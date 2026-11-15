"""Local cryptographic/HTTP doubles. No live KMS or database migration."""
import base64
import os
import unittest
import httpx
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from app.services.knowledge_encryption import KnowledgeEnvelope, GcpKnowledgeKms, KnowledgeEncryptionError


class LocalKms:
    def __init__(self):self.key=AESGCM.generate_key(bit_length=256)
    async def wrap(self,key,aad):
        nonce=os.urandom(12)
        return nonce+AESGCM(self.key).encrypt(nonce,key,aad)
    async def unwrap(self,value,aad):return AESGCM(self.key).decrypt(value[:12],value[12:],aad)


class EncryptionTests(unittest.IsolatedAsyncioTestCase):
    async def test_disabled_by_default_and_scope_required(self):
        with self.assertRaises(KnowledgeEncryptionError):
            await KnowledgeEnvelope(LocalKms()).encrypt("A","P","sources","one",{"text":"private"})

    async def test_ciphertext_only_and_cross_tenant_project_record_replay_fails(self):
        cipher=KnowledgeEnvelope(LocalKms(),enabled=True)
        context=("A","P","sources","one")
        encrypted=await cipher.encrypt(*context,{"text":"PRIVATE_CANARY"})
        self.assertNotIn("PRIVATE_CANARY",str(encrypted))
        self.assertEqual(await cipher.decrypt(*context,encrypted),{"text":"PRIVATE_CANARY"})
        for scope in (("B","P","sources","one"),("A","OTHER","sources","one"),("A","P","versions","one"),("A","P","sources","two")):
            with self.assertRaises(KnowledgeEncryptionError):await cipher.decrypt(*scope,encrypted)
        encrypted["ciphertext"]=base64.b64encode(b"tampered").decode()
        with self.assertRaises(KnowledgeEncryptionError):await cipher.decrypt(*context,encrypted)

    async def test_key_revocation_has_no_plaintext_fallback(self):
        cipher=KnowledgeEnvelope(LocalKms(),enabled=True)
        encrypted=await cipher.encrypt("A","P","sources","one",{"text":"private"})
        cipher.kms=LocalKms()
        with self.assertRaises(KnowledgeEncryptionError):await cipher.decrypt("A","P","sources","one",encrypted)

    async def test_managed_kms_endpoint_auth_and_sanitized_failure(self):
        resource="projects/dev/locations/us-central1/keyRings/qa/cryptoKeys/client-a"
        calls=[]
        def handler(request):
            calls.append(request)
            return httpx.Response(403,json={"error":"SECRET_CANARY"})
        async def token():return "TOKEN_CANARY"
        kms=GcpKnowledgeKms(resource,token,transport=httpx.MockTransport(handler))
        with self.assertRaises(KnowledgeEncryptionError) as failure:await kms.wrap(b"test",b"scope")
        self.assertNotIn("CANARY",str(failure.exception))
        self.assertEqual(str(calls[0].url),"https://cloudkms.googleapis.com/v1/"+resource+":encrypt")
        self.assertEqual(calls[0].headers["Authorization"],"Bearer TOKEN_CANARY")
        with self.assertRaises(KnowledgeEncryptionError):GcpKnowledgeKms("https://evil.invalid",token)
