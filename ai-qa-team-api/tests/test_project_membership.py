import os
from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
TEST_ENV = {
    "MONGO_URI": "mongodb://localhost:27017", "MONGO_DB": "membership_tests",
    "REDIS_HOST": "localhost", "REDIS_PORT": "6379", "REDIS_USERNAME": "test",
    "REDIS_PASSWORD": "test", "SESSION_SECRET_KEY": "test", "JWT_SECRET_KEY": "test",
}
with patch.dict(os.environ, TEST_ENV):
    from app.models.project_model import ProjectCreate
    from app.routes import project_routes, repository_routes
    from app.services import project_team_service, subscription_services
    from app.utils import project_authorization


def matches(document, query):
    if "$or" in query:
        return any(matches(document, option) for option in query["$or"])
    for key, expected in query.items():
        actual = document
        for part in key.split("."):
            actual = actual.get(part) if isinstance(actual, dict) else None
        if isinstance(expected, dict):
            if "$in" in expected and actual not in expected["$in"]: return False
            if "$ne" in expected and actual == expected["$ne"]: return False
        elif actual != expected:
            return False
    return True


def assign(document, path, value):
    parts = path.split(".")
    target = document
    for part in parts[:-1]: target = target.setdefault(part, {})
    target[parts[-1]] = value


class Cursor:
    def __init__(self, documents): self.documents = documents
    def __aiter__(self): self.iterator = iter(self.documents); return self
    async def __anext__(self):
        try: return next(self.iterator)
        except StopIteration: raise StopAsyncIteration
    async def to_list(self, length): return list(self.documents)[:length]
    def sort(self, *_): return self


class Result:
    def __init__(self, inserted_id="id", matched=0, modified=0, deleted=0):
        self.inserted_id = inserted_id; self.matched_count = matched
        self.modified_count = modified; self.deleted_count = deleted


class Collection:
    def __init__(self): self.documents = []
    async def insert_one(self, document): self.documents.append(document.copy()); return Result(str(len(self.documents)))
    async def find_one(self, query, projection=None):
        return next((document for document in self.documents if matches(document, query)), None)
    def find(self, query): return Cursor([document for document in self.documents if matches(document, query)])
    async def update_one(self, query, update, upsert=False):
        document = await self.find_one(query)
        if not document and upsert:
            document = {k: v for k, v in query.items() if not k.startswith("$")}; self.documents.append(document)
            for key, value in update.get("$setOnInsert", {}).items(): assign(document, key, value)
            return Result(matched=0, modified=1)
        if not document: return Result()
        for key, value in update.get("$set", {}).items(): assign(document, key, value)
        for key, value in update.get("$inc", {}).items():
            target = document
            parts = key.split(".")
            for part in parts[:-1]: target = target.setdefault(part, {})
            target[parts[-1]] = target.get(parts[-1], 0) + value
        return Result(matched=1, modified=1)
    async def update_many(self, query, update):
        changed = 0
        for document in self.documents:
            if matches(document, query):
                for key, value in update.get("$set", {}).items(): assign(document, key, value)
                changed += 1
        return Result(modified=changed)
    async def delete_one(self, query):
        for index, document in enumerate(self.documents):
            if matches(document, query): self.documents.pop(index); return Result(deleted=1)
        return Result()
    async def delete_many(self, query):
        before = len(self.documents); self.documents = [d for d in self.documents if not matches(d, query)]
        return Result(deleted=before - len(self.documents))
    async def count_documents(self, query): return sum(matches(document, query) for document in self.documents)


class DB(dict):
    def __missing__(self, key): self[key] = Collection(); return self[key]


class MembershipTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        from app.config import settings
        self.db = DB()
        self.owner = {"_id": "U1", "email": "owner@example.com", "name": "Owner"}
        self.tester = {"_id": "U2", "email": "tester@example.com", "name": "Tester"}
        self.other = {"_id": "U3", "email": "other@example.com", "name": "Other"}
        self.db["users"].documents.extend([
            {**self.owner, "subscription": {"plan": "pro", "usage": {"team_members_used": 0}, "limits": {"team_members_limit": 5}}},
            self.tester.copy(), self.other.copy(),
        ])
        self.db["projects"].documents.append({"_id": "P", "project_id": "PRJ1", "name": "Project", "description": None, "created_by": self.owner["email"], "created_at": "2026-01-01", "agent_identities": {}})
        self.patches = [
            patch.object(settings, "features", settings.features.model_copy(update={"customer_accounts": False, "account_subscriptions": False})),
            patch.object(project_team_service, "db", self.db), patch.object(project_authorization, "db", self.db),
            patch.object(project_routes, "db", self.db), patch.object(repository_routes, "db", self.db),
            patch.object(subscription_services, "db", self.db),
            patch.object(project_team_service, "get_next_sequence", new=AsyncMock(side_effect=lambda *_: f"MEM{len(self.db['project_memberships'].documents)+1:03d}")),
            patch.object(project_authorization, "get_next_sequence", new=AsyncMock(return_value="MEM999")),
        ]
        for item in self.patches: item.start()

    def tearDown(self):
        for item in reversed(self.patches): item.stop()

    async def add_creator(self): return await project_team_service.create_creator_membership("PRJ1", self.owner)

    async def test_project_creator_automatically_becomes_admin(self):
        with patch.object(project_routes, "get_next_sequence", new=AsyncMock(return_value="PRJ2")):
            result = await project_routes.create_project(ProjectCreate(name="Created", created_by="ignored"), self.owner, None)
        membership = await self.db["project_memberships"].find_one({"project_id": "PRJ2"})
        self.assertEqual((result.current_user_role, membership["role"], membership["status"]), ("ADMIN", "ADMIN", "ACTIVE"))

    async def test_admin_tester_and_nonmember_access(self):
        await self.add_creator()
        await project_team_service.invite_member("PRJ1", self.tester["email"], "TESTER", self.owner)
        self.assertEqual((await project_authorization.require_project_admin("PRJ1", self.owner))[1]["role"], "ADMIN")
        self.assertEqual((await project_authorization.require_project_member("PRJ1", self.tester))[1]["role"], "TESTER")
        with self.assertRaises(HTTPException): await project_authorization.require_project_member("PRJ1", {"email": "none@example.com"})

    async def test_admin_can_add_tester_and_admin_and_duplicate_is_prevented(self):
        await self.add_creator()
        tester = await project_team_service.invite_member("PRJ1", self.tester["email"], "TESTER", self.owner)
        admin = await project_team_service.invite_member("PRJ1", self.other["email"], "ADMIN", self.owner)
        self.assertEqual((tester["role"], admin["role"]), ("TESTER", "ADMIN"))
        with self.assertRaises(HTTPException) as raised: await project_team_service.invite_member("PRJ1", self.tester["email"], "TESTER", self.owner)
        self.assertEqual(raised.exception.status_code, 409)

    async def test_tester_cannot_invite_change_roles_or_remove(self):
        await self.add_creator(); member = await project_team_service.invite_member("PRJ1", self.tester["email"], "TESTER", self.owner)
        for operation in (
            project_team_service.invite_member("PRJ1", "new@example.com", "TESTER", self.tester),
            project_team_service.change_member_role("PRJ1", member["membership_id"], "ADMIN", self.tester),
            project_team_service.remove_member("PRJ1", member["membership_id"], self.tester),
        ):
            with self.assertRaises(HTTPException) as raised: await operation
            self.assertEqual(raised.exception.status_code, 403)

    async def test_sole_admin_cannot_demote_or_remove_self(self):
        creator = await self.add_creator()
        with self.assertRaises(HTTPException): await project_team_service.change_member_role("PRJ1", creator["membership_id"], "TESTER", self.owner)
        with self.assertRaises(HTTPException): await project_team_service.remove_member("PRJ1", creator["membership_id"], self.owner)

    async def test_admin_can_be_changed_and_removed_when_another_admin_exists(self):
        creator = await self.add_creator()
        await project_team_service.invite_member("PRJ1", self.other["email"], "ADMIN", self.owner)
        changed = await project_team_service.change_member_role("PRJ1", creator["membership_id"], "TESTER", self.owner)
        self.assertEqual(changed["role"], "TESTER")
        await project_team_service.remove_member("PRJ1", creator["membership_id"], self.other)

    async def test_existing_project_creator_is_safely_backfilled(self):
        _, membership = await project_authorization.require_project_member("PRJ1", self.owner)
        self.assertEqual((membership["role"], membership["status"]), ("ADMIN", "ACTIVE"))
        self.assertEqual(await self.db["project_memberships"].count_documents({"project_id": "PRJ1"}), 1)

    async def test_pending_invitation_activates_on_authentication(self):
        await self.add_creator()
        pending = await project_team_service.invite_member("PRJ1", "pending@example.com", "TESTER", self.owner)
        self.assertEqual(pending["status"], "INVITED")
        await project_team_service.activate_pending_memberships({"_id": "U4", "email": "pending@example.com"})
        active = await self.db["project_memberships"].find_one({"email": "pending@example.com"})
        self.assertEqual((active["status"], active["user_id"]), ("ACTIVE", "U4"))

    async def test_team_member_subscription_limit_counts_pending_invitations(self):
        await self.add_creator()
        owner = await self.db["users"].find_one({"email": self.owner["email"]})
        owner["subscription"]["limits"]["team_members_limit"] = 1
        await project_team_service.invite_member("PRJ1", "pending@example.com", "TESTER", self.owner)
        with self.assertRaises(HTTPException) as raised: await project_team_service.invite_member("PRJ1", "second@example.com", "TESTER", self.owner)
        self.assertEqual(raised.exception.status_code, 403)

    async def test_repository_admin_write_and_tester_read_authorization(self):
        await self.add_creator(); await project_team_service.invite_member("PRJ1", self.tester["email"], "TESTER", self.owner)
        self.db["repositories"].documents.append({"repository_id": "REP1", "project_id": "PRJ1"})
        self.assertEqual((await repository_routes.accessible_repository("REP1", self.tester))["repository_id"], "REP1")
        with self.assertRaises(HTTPException) as raised: await repository_routes.accessible_repository("REP1", self.tester, admin=True)
        self.assertEqual(raised.exception.status_code, 403)


if __name__ == "__main__": unittest.main()
