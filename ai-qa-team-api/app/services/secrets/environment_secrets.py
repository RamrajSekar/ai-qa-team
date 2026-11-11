"""Encrypt one environment's secrets inside its atomic Mongo document."""
import base64
import json
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import HTTPException

from app.config import settings


def cipher():
    encoded = settings.environment_secret_master_key or settings.llm_secret_master_key
    if not encoded:
        raise HTTPException(503, "Environment secret storage is not configured.")
    try:
        key = base64.urlsafe_b64decode(encoded)
        if len(key) != 32:
            raise ValueError()
        return AESGCM(key)
    except Exception:
        raise HTTPException(503, "Environment secret storage configuration is invalid.") from None


def associated_data(document):
    return json.dumps(["environment-secrets-v1", document["project_id"], document["env_id"]]).encode()


def read_secrets(document):
    envelope = document.get("secret_payload")
    if not envelope:
        return {
            "passwords": {item["role"].strip().lower(): item.get("password", "")
                          for item in document.get("credentials", [])},
            "auth_token": document.get("auth_token"),
        }
    try:
        raw = cipher().decrypt(base64.b64decode(envelope["nonce"]),
                               base64.b64decode(envelope["ciphertext"]), associated_data(document))
        return json.loads(raw)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(503, "Environment secrets could not be opened.") from None


def encrypt_secrets(document, passwords, auth_token):
    if not any(passwords.values()) and not auth_token:
        return None
    nonce = os.urandom(12)
    raw = json.dumps({"passwords": passwords, "auth_token": auth_token}).encode()
    encrypted = cipher().encrypt(nonce, raw, associated_data(document))
    return {"version": 1, "nonce": base64.b64encode(nonce).decode(),
            "ciphertext": base64.b64encode(encrypted).decode()}


def public_environment(document):
    """Never decrypt on the read/API path, including legacy plaintext records."""
    result = {key: value for key, value in document.items() if key not in ("_id", "secret_payload")}
    result["id"] = str(document.get("_id", document.get("id", "")))
    result["revision"] = document.get("revision", 0)
    result["credentials"] = [
        {**{key: value for key, value in item.items() if key != "password"}, "password": "",
         "password_configured": bool(item.get("password_configured") or item.get("password"))}
        for item in document.get("credentials", [])
    ]
    result["auth_token"] = None
    result["auth_token_configured"] = bool(document.get("auth_token_configured") or document.get("auth_token"))
    return result
