import re
from copy import deepcopy
from datetime import datetime, timezone

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from app.config import settings
from app.db.connection import db
from app.services.platform_role_service import normalize_email
from app.services.prompt_defaults import PROMPT_DEFAULTS
from app.services.prompt_templates import validate_template


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default(prompt_key: str) -> dict:
    value = PROMPT_DEFAULTS.get(prompt_key)
    if not value:
        raise HTTPException(404, "Prompt not found")
    return deepcopy(value)


def _safe_definition(document: dict | None, prompt_key: str) -> dict:
    fallback = _default(prompt_key)
    if not document:
        return {key: fallback[key] for key in ("prompt_key", "name", "description", "output_contract")} | {
            "active_version": None, "created_at": None, "updated_at": None,
        }
    return {key: document.get(key) for key in ("prompt_key", "name", "description", "output_contract", "active_version", "created_at", "updated_at")}


def _validate_prompt_content(content: str) -> None:
    secret_values = [settings.openai_api_key, settings.llm_secret_master_key]
    if any(value and value in content for value in secret_values):
        raise HTTPException(422, "Prompt content must not contain credentials")
    if re.search(r"(?:sk-[A-Za-z0-9_-]{16,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|Bearer\s+[A-Za-z0-9._-]{16,})", content, re.IGNORECASE):
        raise HTTPException(422, "Prompt content must not contain credentials")


async def list_prompts() -> list[dict]:
    results = []
    for prompt_key in PROMPT_DEFAULTS:
        document = await db["prompt_definitions"].find_one({"prompt_key": prompt_key})
        definition = _safe_definition(document, prompt_key)
        active = await get_active(prompt_key)
        definition.update({"resolved_version": active["resolved_version"], "source": active["source"]})
        results.append(definition)
    return results


async def get_prompt_definition(prompt_key: str) -> dict:
    prompt_key = prompt_key.upper()
    document = await db["prompt_definitions"].find_one({"prompt_key": prompt_key})
    definition = _safe_definition(document, prompt_key)
    definition["template_variables"] = _default(prompt_key).get("template_variables", [])
    definition["active"] = await get_active(prompt_key)
    return definition


async def get_active(prompt_key: str, database=None) -> dict:
    prompt_key = prompt_key.upper()
    fallback = _default(prompt_key)
    store = db if database is None else database
    document = await store["prompt_definitions"].find_one({"prompt_key": prompt_key})
    if document and document.get("active_version") is not None:
        version = next((item for item in document.get("versions", []) if item["version"] == document["active_version"] and item["status"] == "ACTIVE"), None)
        if version:
            return {"prompt_key": prompt_key, "resolved_version": version["version"], "source": "DATABASE", "system_prompt": version["system_prompt"]}
    return {key: fallback[key] for key in ("prompt_key", "resolved_version", "source", "system_prompt")}


async def list_versions(prompt_key: str) -> list[dict]:
    prompt_key = prompt_key.upper(); _default(prompt_key)
    document = await db["prompt_definitions"].find_one({"prompt_key": prompt_key})
    return sorted(deepcopy((document or {}).get("versions", [])), key=lambda item: item["version"], reverse=True)


def _base_content(document: dict | None, prompt_key: str, base_version: int | str | None) -> str:
    fallback = _default(prompt_key)
    if base_version == fallback["resolved_version"] or not document:
        return fallback["system_prompt"]
    selected = base_version if isinstance(base_version, int) else document.get("active_version")
    if selected is None:
        return fallback["system_prompt"]
    version = next((item for item in document.get("versions", []) if item["version"] == selected), None)
    if not version:
        raise HTTPException(404, "Prompt version not found")
    return version["system_prompt"]


async def create_draft(prompt_key: str, actor: str, base_version: int | str | None = None) -> dict:
    prompt_key = prompt_key.upper(); fallback = _default(prompt_key)
    document = await db["prompt_definitions"].find_one({"prompt_key": prompt_key})
    versions = deepcopy((document or {}).get("versions", []))
    version = max((item["version"] for item in versions), default=0) + 1
    draft = {"version": version, "system_prompt": _base_content(document, prompt_key, base_version), "status": "DRAFT",
        "created_by": normalize_email(actor), "created_at": _now(), "activated_at": None}
    versions.append(draft)
    if not document:
        now = _now()
        new_document = {key: fallback[key] for key in ("prompt_key", "name", "description", "output_contract")}
        new_document.update({"active_version": None, "versions": versions, "revision": 1, "created_at": now, "updated_at": now})
        try:
            await db["prompt_definitions"].insert_one(new_document)
        except DuplicateKeyError:
            raise HTTPException(409, "Prompt changed concurrently; retry") from None
    else:
        await _atomic_update(document, {"versions": versions, "updated_at": _now()})
    return draft


async def update_draft(prompt_key: str, version_number: int, system_prompt: str) -> dict:
    prompt_key = prompt_key.upper(); fallback = _default(prompt_key); _validate_prompt_content(system_prompt)
    validate_template(system_prompt, fallback.get("template_variables", []))
    document = await db["prompt_definitions"].find_one({"prompt_key": prompt_key})
    if not document: raise HTTPException(404, "Prompt version not found")
    versions = deepcopy(document.get("versions", []))
    target = next((item for item in versions if item["version"] == version_number), None)
    if not target: raise HTTPException(404, "Prompt version not found")
    if target["status"] != "DRAFT": raise HTTPException(409, "Only DRAFT prompt versions can be edited")
    target["system_prompt"] = system_prompt
    await _atomic_update(document, {"versions": versions, "updated_at": _now()})
    return target


async def activate_version(prompt_key: str, version_number: int) -> dict:
    prompt_key = prompt_key.upper(); _default(prompt_key)
    document = await db["prompt_definitions"].find_one({"prompt_key": prompt_key})
    if not document: raise HTTPException(404, "Prompt version not found")
    versions = deepcopy(document.get("versions", []))
    target = next((item for item in versions if item["version"] == version_number), None)
    if not target: raise HTTPException(404, "Prompt version not found")
    _validate_prompt_content(target["system_prompt"])
    validate_template(target["system_prompt"], _default(prompt_key).get("template_variables", []))
    activated_at = _now()
    for item in versions:
        if item["status"] == "ACTIVE": item["status"] = "INACTIVE"
    target["status"] = "ACTIVE"; target["activated_at"] = activated_at
    await _atomic_update(document, {"versions": versions, "active_version": version_number, "updated_at": activated_at})
    return target


async def _atomic_update(document: dict, changes: dict) -> None:
    result = await db["prompt_definitions"].update_one(
        {"prompt_key": document["prompt_key"], "revision": document.get("revision", 1)},
        {"$set": changes, "$inc": {"revision": 1}},
    )
    if result.modified_count != 1:
        raise HTTPException(409, "Prompt changed concurrently; retry")
