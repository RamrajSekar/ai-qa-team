import base64
import os
from datetime import datetime, timezone
from uuid import uuid4

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import settings
from app.db.connection import db
from app.services.secrets.base import SecretStore


class SecretStoreConfigurationError(RuntimeError):
    pass


class EncryptedMongoSecretStore(SecretStore):
    collection_name = "encrypted_secrets"

    def __init__(self, master_key: str | None = None):
        encoded = master_key or settings.llm_secret_master_key
        if not encoded:
            raise SecretStoreConfigurationError("LLM secret storage is not configured")
        try:
            key = base64.urlsafe_b64decode(encoded)
        except Exception as exc:
            raise SecretStoreConfigurationError("LLM secret master key is invalid") from exc
        if len(key) != 32:
            raise SecretStoreConfigurationError("LLM secret master key must decode to 32 bytes")
        self._cipher = AESGCM(key)

    async def put(self, project_id: str, value: str) -> str:
        credential_ref = f"llmsec_{uuid4().hex}"
        nonce = os.urandom(12)
        ciphertext = self._cipher.encrypt(nonce, value.encode(), self._aad(project_id, credential_ref))
        now = datetime.now(timezone.utc)
        await db[self.collection_name].insert_one({"credential_ref": credential_ref, "project_id": project_id,
            "nonce": base64.b64encode(nonce).decode(), "ciphertext": base64.b64encode(ciphertext).decode(),
            "created_at": now, "updated_at": now})
        return credential_ref

    async def get(self, project_id: str, credential_ref: str) -> str:
        document = await db[self.collection_name].find_one({"credential_ref": credential_ref, "project_id": project_id})
        if not document:
            raise KeyError("Credential not found")
        value = self._cipher.decrypt(base64.b64decode(document["nonce"]), base64.b64decode(document["ciphertext"]), self._aad(project_id, credential_ref))
        return value.decode()

    async def replace(self, project_id: str, credential_ref: str, value: str) -> str:
        new_ref = await self.put(project_id, value)
        await self.delete(project_id, credential_ref)
        return new_ref

    async def delete(self, project_id: str, credential_ref: str) -> None:
        await db[self.collection_name].delete_one({"credential_ref": credential_ref, "project_id": project_id})

    @staticmethod
    def _aad(project_id: str, credential_ref: str) -> bytes:
        return f"ai-qa-team:{project_id}:{credential_ref}".encode()
