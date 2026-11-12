"""Explicit ownership migration. Never infer customer mergers from shared projects."""
from app.services.approved_visual_run import digest
from uuid import NAMESPACE_URL, uuid5


def plan_accounts(users, projects, memberships, mapping, existing_accounts=()):
    errors, accounts, assignments, changes = [], [], {}, []
    legacy_projects = {}
    known_projects = {project["project_id"] for project in projects}
    identities = {str(user["_id"]): user for user in users}
    emails = {}
    for user in users:
        email = user.get("email", "")
        if email != email.strip().lower() or email in emails:
            errors.append("Duplicate or non-normalized identity: " + str(user["_id"]))
        emails[email] = str(user["_id"])
    used_account_ids = set()
    for spec in mapping.get("accounts", []):
        owners = [item.get("user_id") for item in spec.get("users", []) if item.get("role") == "OWNER"]
        account_id = spec.get("account_id")
        if "account_id" not in spec and len(owners) == 1 and owners[0] in identities:
            # Deterministic for dry-run/apply; naming or membership edits cannot
            # create a different ID. Retain an already assigned owner's identity.
            account_id = identities[owners[0]].get("account_id") or "ACC_" + uuid5(
                NAMESPACE_URL, "ai-qa-squad/customer-account/migration-owner:" + owners[0]).hex
        if not isinstance(account_id, str) or not account_id.startswith("ACC_") or account_id in used_account_ids:
            errors.append("Account IDs must be unique; omit the ID only with one valid reviewed owner."); continue
        used_account_ids.add(account_id)
        if not isinstance(spec.get("name"), str) or not 2 <= len(spec["name"].strip()) <= 160:
            errors.append("Each account requires a valid customer name.")
        if len(owners) != 1:
            errors.append("Exactly one explicit owner is required for " + account_id)
        for item in spec.get("users", []):
            identity = item.get("user_id")
            if identity not in identities or identity in assignments or item.get("role") not in ("OWNER", "ADMIN", "MEMBER"):
                errors.append("Invalid or multiply assigned user: " + str(identity)); continue
            current = identities[identity]
            if current.get("account_id") and current["account_id"] != account_id:
                errors.append("Reparenting is prohibited for user " + identity)
            assignments[identity] = (account_id, item["role"])
        accounts.append({"_id": account_id, "name": spec.get("name", "").strip(), "owner_user_id": owners[0] if len(owners) == 1 else None,
                         "status": "ACTIVE", "setup_status": "COMPLETE"})
        claims = spec.get("legacy_project_ids", [])
        if not isinstance(claims, list):
            errors.append("legacy_project_ids must be an explicit list.")
            claims = []
        for project_id in claims:
            if not isinstance(project_id, str) or project_id not in known_projects:
                errors.append("Unknown legacy project claim: " + str(project_id)); continue
            if project_id in legacy_projects:
                errors.append("Multiply claimed legacy project: " + project_id); continue
            if len(owners) == 1 and owners[0] in identities:
                legacy_projects[project_id] = (account_id, owners[0])
    if set(assignments) != set(identities):
        errors.append("Every existing user must have exactly one reviewed account assignment.")
    existing = {item["_id"]: item for item in existing_accounts}
    for account in accounts:
        old = existing.get(account["_id"])
        if old and (old.get("owner_user_id") != account["owner_user_id"] or old.get("status") != "ACTIVE"):
            errors.append("Existing account conflicts with mapping: " + account["_id"])
    project_accounts = {}
    for project in projects:
        identity = emails.get(project.get("created_by"))
        claim = legacy_projects.get(project["project_id"])
        values = {}
        if identity not in assignments:
            if not claim:
                errors.append("Project creator is unmapped: " + project["project_id"]); continue
            account_id, owner_id = claim
            # Explicit recovery of a deleted creator. Preserve provenance; do not
            # rewrite story/test/run authors or historical billing records.
            values["created_by"] = identities[owner_id]["email"]
            if "legacy_created_by" not in project:
                values["legacy_created_by"] = project.get("created_by")
        else:
            account_id = assignments[identity][0]
            if claim and claim[0] != account_id:
                errors.append("Legacy claim conflicts with mapped creator: " + project["project_id"])
        project_accounts[project["project_id"]] = account_id
        if project.get("account_id") and project["account_id"] != account_id:
            errors.append("Reparenting is prohibited for project " + project["project_id"])
        values["account_id"] = account_id
        changes.append({"collection": "projects", "key": {"project_id": project["project_id"]}, "set": values,
                        "before": {key: project.get(key) for key in values}})
    for identity, (account_id, role) in assignments.items():
        user = identities[identity]
        changes.append({"collection": "users", "key": {"_id": identity}, "set": {"account_id": account_id, "account_role": role, "account_state": "ACTIVE"},
                        "before": {key: user.get(key) for key in ("account_id", "account_role", "account_state")}})
    for membership in memberships:
        account_id = project_accounts.get(membership["project_id"])
        identity = emails.get(membership["email"])
        if not account_id:
            errors.append("Orphan project membership: " + membership["membership_id"]); continue
        values = {"account_id": account_id}
        if identity is None:
            # Deleted users must not acquire access if their email signs up later.
            values["status"] = "LEGACY_REVIEW_REQUIRED"
            if "legacy_status" not in membership:
                values["legacy_status"] = membership["status"]
        elif identity not in assignments or assignments[identity][0] != account_id:
            errors.append("Cross-account membership requires explicit resolution: " + membership["membership_id"])
        changes.append({"collection": "project_memberships", "key": {"membership_id": membership["membership_id"]}, "set": values,
                        "before": {key: membership.get(key) for key in values}})
    changes = [change for change in changes if change["before"] != change["set"]]
    plan = {"accounts": accounts, "changes": changes, "errors": sorted(set(errors))}
    return {**plan, "plan_digest": digest(plan)}


async def apply_accounts(database, plan, expected_digest, *, maintenance_confirmed=False):
    if plan["errors"] or plan["plan_digest"] != expected_digest or not maintenance_confirmed:
        raise ValueError("A conflict-free matching dry-run plan and maintenance confirmation are required.")
    # Caller must take a protected backup and stop writers. CAS catches stale ownership.
    from bson import ObjectId
    from datetime import datetime, timezone
    for account in plan["accounts"]:
        await database["customer_accounts"].update_one({"_id": account["_id"]}, {"$setOnInsert": {**account, "created_at": datetime.now(timezone.utc)}}, upsert=True)
    for change in plan["changes"]:
        key = dict(change["key"])
        if change["collection"] == "users" and ObjectId.is_valid(key["_id"]):
            key["_id"] = ObjectId(key["_id"])
        result = await database[change["collection"]].update_one({**key, **change["before"]}, {"$set": change["set"]})
        if result.matched_count != 1:
            raise ValueError("Migration stopped on a changed record. Reconcile and generate a new dry-run plan.")
