"""Disabled preparation for envelope encryption; not a database migration/wrapper.

Callers must authorize the tenant/project before requesting a cipher. No local
master-key fallback. Deployment identity and tenant key mappings are server-owned.
"""
import base64
import json
import os
import re
import httpx
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class KnowledgeEncryptionError(RuntimeError):
    pass


class GcpKnowledgeKms:
    def __init__(self, key_resource, token_provider, *, transport=None):
        if not re.fullmatch(r"projects/[A-Za-z0-9_-]+/locations/[A-Za-z0-9_-]+/keyRings/[A-Za-z0-9_-]+/cryptoKeys/[A-Za-z0-9_-]+", key_resource):
            raise KnowledgeEncryptionError("Invalid managed key configuration")
        self.resource, self.token_provider, self.transport = key_resource, token_provider, transport

    async def operation(self, operation, value, aad):
        if operation not in {"encrypt", "decrypt"}:
            raise KnowledgeEncryptionError("Unsupported managed key operation")
        try:
            token = await self.token_provider()
            if not token:
                raise KnowledgeEncryptionError("Managed identity unavailable")
            field = "plaintext" if operation == "encrypt" else "ciphertext"
            async with httpx.AsyncClient(transport=self.transport, trust_env=False, timeout=10, follow_redirects=False) as client:
                response = await client.post("https://cloudkms.googleapis.com/v1/"+self.resource+":"+operation,
                    headers={"Authorization":"Bearer "+token}, json={field:base64.b64encode(value).decode(),
                        "additionalAuthenticatedData":base64.b64encode(aad).decode()})
                response.raise_for_status()
                output = response.json()["ciphertext" if operation == "encrypt" else "plaintext"]
                return base64.b64decode(output, validate=True)
        except Exception:
            # Never surface HTTP bodies, tokens, key material or plaintext.
            raise KnowledgeEncryptionError("Managed key operation unavailable") from None

    async def wrap(self, key, aad):
        return await self.operation("encrypt", key, aad)

    async def unwrap(self, wrapped, aad):
        return await self.operation("decrypt", wrapped, aad)


class KnowledgeEnvelope:
    def __init__(self, kms, *, enabled=False):
        self.kms, self.enabled = kms, enabled

    def context(self, account, project, collection, identity):
        if not self.enabled or not all((account, project, collection, identity)):
            raise KnowledgeEncryptionError("Knowledge encryption is disabled or unconfigured")
        return json.dumps(["knowledge-envelope-v1",account,project,collection,identity], separators=(",",":")).encode()

    async def encrypt(self, account, project, collection, identity, payload):
        aad = self.context(account,project,collection,identity)
        key, nonce = AESGCM.generate_key(bit_length=256), os.urandom(12)
        wrapped = await self.kms.wrap(key, aad)
        ciphertext = AESGCM(key).encrypt(nonce,json.dumps(payload,ensure_ascii=False).encode(),aad)
        return {"envelope_version":1,"wrapped_key":base64.b64encode(wrapped).decode(),
            "nonce":base64.b64encode(nonce).decode(),"ciphertext":base64.b64encode(ciphertext).decode()}

    async def decrypt(self, account, project, collection, identity, envelope):
        aad = self.context(account,project,collection,identity)
        try:
            if envelope["envelope_version"] != 1:
                raise ValueError()
            key = await self.kms.unwrap(base64.b64decode(envelope["wrapped_key"],validate=True),aad)
            raw = AESGCM(key).decrypt(base64.b64decode(envelope["nonce"],validate=True),
                base64.b64decode(envelope["ciphertext"],validate=True),aad)
            return json.loads(raw)
        except Exception:
            raise KnowledgeEncryptionError("Knowledge could not be decrypted") from None
