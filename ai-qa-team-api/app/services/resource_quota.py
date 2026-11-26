"""Transactional scenario/case capacity. No model work occurs in a transaction."""
import asyncio
from contextlib import asynccontextmanager
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from uuid import uuid4

from bson import ObjectId
from fastapi import HTTPException
from pymongo.errors import PyMongoError, DuplicateKeyError
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern
from pymongo import ReadPreference

from app.services.account_billing import billing_account
from app.services.testcase_allowances import testcase_allowances


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()



class ResourceQuota:
    def __init__(self, database):
        self.db = database
        self.rows = database["resource_quota_reservations"]

    async def transaction(self, work):
        try:
            async with asyncio.timeout(30):
                async with await self.db.client.start_session() as session:
                    return await session.with_transaction(work, read_concern=ReadConcern("snapshot"),
                        write_concern=WriteConcern("majority", wtimeout=10000), read_preference=ReadPreference.PRIMARY)
        except HTTPException:
            raise
        except DuplicateKeyError:
            raise HTTPException(409, "This resource request already exists. Check saved records before retrying.") from None
        except (PyMongoError, AttributeError, TimeoutError):
            raise HTTPException(503, "Resource capacity could not be confirmed. A transaction-capable Mongo deployment is required; check saved records before retrying.") from None

    async def target(self, user):
        stored = await self.db["users"].find_one({"email": user["email"]})
        if not stored:
            raise HTTPException(401, "User not found.")
        account = await billing_account(self.db, stored)
        if account:
            return "customer_accounts", account["_id"], stored
        return "users", stored["_id"], stored

    async def create_account_resource(self, user, kind, document, *, creator_membership=None):
        """Atomic immediate creation for v2 projects/stories, including project membership."""
        if kind not in ("projects", "stories") or document.get("created_by") != user.get("email"):
            raise HTTPException(422, "Invalid account resource.")
        collection, identity, stored = await self.target(user)
        if collection != "customer_accounts":
            raise HTTPException(409, "Account entitlement adoption is required.")
        document = deepcopy(document)
        document.setdefault("_id", ObjectId())

        async def work(session):
            owner = await self.db[collection].find_one({"_id": identity, "billing_version": 1, "status": "ACTIVE"}, session=session)
            sub = (owner or {}).get("subscription", {})
            if sub.get("entitlement_version") != 2 or sub.get("status") != "active":
                raise HTTPException(403, "No active account resource allowance.")
            from app.services.billing.access import require_consumption
            require_consumption(owner)
            if kind == "projects":
                if document.get("account_id") != identity or not creator_membership or creator_membership.get("project_id") != document.get("project_id") or creator_membership.get("email") != stored["email"].lower():
                    raise HTTPException(422, "Project membership scope mismatch.")
            else:
                project = await self.db["projects"].find_one({"project_id": document.get("project_id"), "account_id": identity}, session=session)
                if not project:
                    raise HTTPException(403, "Project is outside this account.")
            metric = kind + "_used"
            limit = sub.get("limits", {}).get(kind + "_limit")
            used = sub.get("usage", {}).get(metric)
            pending = owner.get("resource_quota_pending", {}).get(metric, 0)
            if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in (limit, used, pending)):
                raise HTTPException(503, "Account resource reconciliation is required.")
            if used + pending >= limit:
                raise HTTPException(403, f"{kind.title()} allowance reached. Existing records remain available.")
            await self.db[collection].update_one({"_id": identity}, {"$inc": {f"subscription.usage.{metric}": 1}}, session=session)
            await self.db[kind].insert_one(document, session=session)
            if creator_membership:
                await self.db["project_memberships"].insert_one(deepcopy(creator_membership), session=session)
            return document
        return await self.transaction(work)

    @staticmethod
    def limits(subscription, kind, tier):
        limits = subscription.get("limits", {})
        total = limits.get(kind + "_limit")
        if kind == "testcases":
            effective = testcase_allowances(subscription)
            result = {"testcases_used": effective["testcases_limit"], f"testcases_{tier}_used": effective[f"testcases_{tier}_limit"]}
        else:
            if "scenarios_limit" not in limits:
                raise HTTPException(503, "Scenario allowance is not configured.")
            result = {"scenarios_used": total}
        if any(value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 0) for value in result.values()):
            raise HTTPException(503, "Resource allowance is not configured.")
        return result

    async def reserve(self, user, project, kind, count, tier="basic", *, request_id=None, source=None):
        if kind not in ("scenarios", "testcases") or tier not in ("basic", "medium", "advanced") or isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 20:
            raise HTTPException(422, "Invalid resource reservation.")
        collection, owner_id, stored = await self.target(user)
        request_id = request_id or uuid4().hex
        identity = fingerprint([collection, str(owner_id), request_id])
        request_digest = fingerprint([stored["email"], project, kind, count, tier, source])

        async def work(session):
            existing = await self.rows.find_one({"_id": identity}, session=session)
            if existing:
                raise HTTPException(409, "This generation request was already admitted. Check saved records; do not repeat an uncertain AI request.")
            owner = await self.db[collection].find_one({"_id": owner_id}, session=session)
            if (not owner or owner.get("subscription", {}).get("status") != "active"
                    or (collection == "customer_accounts" and (owner.get("status") != "ACTIVE" or owner.get("billing_version") != 1))):
                raise HTTPException(403, "No active resource allowance.")
            limits = self.limits(owner["subscription"], kind, tier)
            if collection == "customer_accounts":
                from app.services.billing.access import require_consumption
                require_consumption(owner)
            pending = owner.get("resource_quota_pending", {})
            allowed = count
            for metric, limit in limits.items():
                if collection == "customer_accounts":
                    used = owner["subscription"].get("usage", {}).get(metric, 0)
                else:
                    query = {"created_by": stored["email"]}
                    if metric != kind + "_used":
                        query["$or"] = [{"complexity": tier}, {"complexity": None, "level": {"$in": [tier, None] if tier == "basic" else [tier]}}]
                    used = await self.db[kind].count_documents(query, session=session)
                waiting = pending.get(metric, 0)
                if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in (used, waiting)):
                    raise HTTPException(503, "Resource usage reconciliation is required.")
                if limit is not None:
                    allowed = min(allowed, max(limit - used - waiting, 0))
            if allowed <= 0:
                raise HTTPException(403, f"{kind.title()} limit reached. Other requests may have reserved the remaining capacity.")
            record = {"_id": identity, "schema_version": "resource-quota-v1", "request_id": request_id, "request_digest": request_digest,
                "owner_collection": collection, "owner_id": owner_id, "actor_email": stored["email"],
                "project_id": project, "kind": kind, "tier": tier, "metrics": list(limits),
                "capacity": allowed, "remaining": allowed, "saved": {}, "state": "RESERVED",
                "created_at": datetime.now(timezone.utc).isoformat()}
            await self.db[collection].update_one({"_id": owner_id}, {"$inc": {f"resource_quota_pending.{metric}": allowed for metric in limits}}, session=session)
            await self.rows.insert_one(record, session=session)
            return record
        return await self.transaction(work)

    async def persist(self, reservation, document, index):
        document = deepcopy(document)
        if document.get("project_id") != reservation["project_id"] or document.get("created_by") != reservation["actor_email"]:
            raise HTTPException(422, "Reservation resource scope mismatch.")
        if reservation["kind"] == "testcases" and document.get("complexity") != reservation["tier"]:
            raise HTTPException(422, "Reservation complexity mismatch.")
        document["_id"] = ObjectId(fingerprint([reservation["_id"], index])[:24])
        signature = fingerprint(document)

        async def work(session):
            row = await self.rows.find_one({"_id": reservation["_id"]}, session=session)
            if not row:
                raise HTTPException(409, "Resource reservation is unavailable.")
            saved = row["saved"].get(str(index))
            if saved:
                if saved["digest"] != signature: raise HTTPException(409, "This reserved item has different content.")
                return await self.db[row["kind"]].find_one({"_id": saved["id"]}, session=session)
            if row["state"] != "RESERVED" or row["remaining"] <= 0 or not 0 <= index < row["capacity"]:
                raise HTTPException(409, "Resource reservation is closed or exhausted.")
            owner_query = {"_id": row["owner_id"], "subscription.status": "active"}
            if row["owner_collection"] == "customer_accounts": owner_query.update(status="ACTIVE", billing_version=1)
            for metric in row["metrics"]:owner_query[f"resource_quota_pending.{metric}"] = {"$gte": 1}
            changes = {f"resource_quota_pending.{metric}": -1 for metric in row["metrics"]}
            changes.update({f"subscription.usage.{metric}": 1 for metric in row["metrics"]})
            result = await self.db[row["owner_collection"]].update_one(owner_query, {"$inc": changes}, session=session)
            if result.matched_count != 1:raise HTTPException(409, "Resource capacity changed. Review this request.")
            await self.db[row["kind"]].insert_one(document, session=session)
            await self.rows.update_one({"_id": row["_id"]}, {"$inc": {"remaining": -1}, "$set": {f"saved.{index}": {"id": document["_id"], "digest": signature}}}, session=session)
            return document
        return await self.transaction(work)

    async def settle(self, reservation, *, expected_digest=None):
        async def work(session):
            row = await self.rows.find_one({"_id": reservation["_id"]}, session=session)
            if not row or row["state"] == "SETTLED":return row
            if expected_digest is not None and fingerprint(row) != expected_digest:
                raise HTTPException(409, "Reservation changed. Review a new reconciliation plan.")
            count = row["remaining"]
            if count:
                query = {"_id": row["owner_id"], **{f"resource_quota_pending.{metric}": {"$gte": count} for metric in row["metrics"]}}
                result = await self.db[row["owner_collection"]].update_one(query,
                    {"$inc": {f"resource_quota_pending.{metric}": -count for metric in row["metrics"]}}, session=session)
                if result.matched_count != 1:raise HTTPException(409, "Reservation reconciliation is required.")
            await self.rows.update_one({"_id": row["_id"]}, {"$set": {"remaining": 0, "state": "SETTLED", "settled_at": datetime.now(timezone.utc).isoformat()}}, session=session)
            return row
        return await self.transaction(work)

    @asynccontextmanager
    async def admission(self, user, project, kind, count, tier="basic", **kwargs):
        reservation = await self.reserve(user, project, kind, count, tier, **kwargs)
        try:
            yield reservation
        finally:
            # No AI replay. DB-only transaction retries reconcile committed writes.
            # A process kill/outage retains pending capacity for explicit recovery.
            await self.settle(reservation)
