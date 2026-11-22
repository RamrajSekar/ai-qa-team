"""Real account-scope policy with Mongo/auth/provider doubles; no external services."""
import asyncio
import json
import unittest
from copy import deepcopy
from types import SimpleNamespace
import test_product_knowledge as fixtures
from fastapi import HTTPException
from app.services.knowledge_ask import KnowledgeAsk
from app.models.knowledge_ask import KnowledgeQuestion
from app.config import settings


class AskTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await fixtures.KnowledgeTests.asyncSetUp(self)
        settings.features.knowledge_ask = True
        self.user.update(email="a@example.test",account_id="ACC_A")
        self.db["users"] = fixtures.Collection({"_id":"reviewer","email":"a@example.test","account_id":"ACC_A","account_state":"ACTIVE"})
        self.db["customer_accounts"] = fixtures.Collection({"_id":"ACC_A","status":"ACTIVE"})
        self.db["customer_accounts"].docs.append({"_id":"ACC_B","status":"ACTIVE"})
        self.db["projects"] = fixtures.Collection({"project_id":"P1","account_id":"ACC_A"})
        self.db["projects"].docs.append({"project_id":"P2","account_id":"ACC_B"})
        self.db["project_memberships"] = fixtures.Collection({"project_id":"P1","account_id":"ACC_A","email":"a@example.test","status":"ACTIVE"})
        self.db["knowledge_ask_requests"] = fixtures.Collection()
        self.ask = KnowledgeAsk(self.db,self.service)
        self.payload = KnowledgeQuestion(request_id="a"*32,question="What happens when saving?")

    approved = fixtures.KnowledgeTests.approved

    def answer(self,**changes):
        self.usage.execute.return_value=SimpleNamespace(text=json.dumps({"status":"supported","answer":"A confirmation is shown.",
            "citations":[{"claim_id":"K1"}],**changes}))

    async def test_scoped_cited_answer_metered_once_without_stored_text(self):
        version=await self.approved();self.answer()
        result=await self.ask.ask("P1",self.user,self.payload)
        self.assertEqual(result["knowledge_version_id"],version["version_id"])
        self.assertEqual(result["citations"][0]["source_id"],self.claim["source_id"])
        request=self.usage.execute.call_args.args[3]
        self.assertEqual(self.usage.execute.call_args.args[0].value,"KNOWLEDGE_ASK")
        self.assertEqual(request.max_retries,0)
        self.assertEqual(request.prompt_key,"knowledge_ask_v1")
        self.assertNotIn("question",self.db["knowledge_ask_requests"].docs[0])
        self.assertNotIn("answer",self.db["knowledge_ask_requests"].docs[0])
        with self.assertRaises(HTTPException) as duplicate:
            await self.ask.ask("P1",self.user,self.payload)
        self.assertEqual(duplicate.exception.status_code,409)
        self.assertEqual(self.usage.execute.await_count,1)

    async def test_account_claims_and_membership_cannot_cross_tenants(self):
        await self.approved();self.answer();self.user["account_id"]="ACC_B"
        await self.ask.scope("P1",self.user)
        self.assertEqual(self.user["account_id"],"ACC_A")
        with self.assertRaises(HTTPException) as denied:
            await self.ask.ask("P2",self.user,self.payload)
        self.assertEqual(denied.exception.status_code,404)
        self.db["project_memberships"].docs[0]["account_id"]="ACC_B"
        with self.assertRaises(HTTPException):await self.ask.ask("P1",self.user,self.payload)
        self.usage.execute.assert_not_called()

    async def test_real_project_guard_rejects_foreign_account_even_for_platform_owner(self):
        from unittest.mock import patch
        from app.utils import project_authorization
        self.user["platform_role"]="OWNER"
        with patch.object(project_authorization,"db",self.db):
            await project_authorization.require_project_member("P1",self.user)
            with self.assertRaises(HTTPException) as blocked:
                await project_authorization.require_project_member("P2",self.user)
        self.assertEqual(blocked.exception.status_code,404)

    async def test_pending_foreign_and_historical_rules_not_sent(self):
        await self.approved();self.answer()
        self.db["product_knowledge_versions"].docs.append({"_id":"b"*32,"project_id":"P2","version_id":"b"*32,"status":"approved","approved_at":"2099","claims":[{"statement":"FOREIGN_CANARY"}]})
        await self.service.create_version("P1","reviewer",fixtures.KnowledgeDraft(title="Pending",claims=[{**self.claim,"claim_id":"K2","statement":"PENDING_CANARY"}]))
        await self.ask.ask("P1",self.user,self.payload)
        prompt=self.usage.execute.call_args.args[3].prompt
        self.assertNotIn("FOREIGN_CANARY",prompt);self.assertNotIn("PENDING_CANARY",prompt)

    async def test_no_knowledge_and_disabled_flag_make_no_ai_call(self):
        self.assertEqual((await self.ask.ask("P1",self.user,self.payload))["status"],"not_covered")
        settings.features.knowledge_ask=False
        response=await self.client.post(self.base+"/ask",json=self.payload.model_dump())
        self.assertEqual(response.status_code,403)
        self.usage.execute.assert_not_called()

    async def test_invalid_citation_or_false_conflict_rejected_without_answer(self):
        await self.approved()
        for changes in ({"citations":[{"claim_id":"OTHER","quote":"Show"}]},{"citations":[]},{"status":"conflicting"}):
            self.db["knowledge_ask_requests"].docs.clear();self.answer(**changes)
            with self.assertRaises(HTTPException) as rejected:await self.ask.ask("P1",self.user,self.payload)
            self.assertEqual(rejected.exception.status_code,502)
        self.assertEqual(self.db["knowledge_ask_requests"].docs[0]["state"],"uncertain")

    async def test_concurrent_duplicate_requests_have_one_provider_call(self):
        await self.approved();self.answer()
        results=await asyncio.gather(self.ask.ask("P1",self.user,self.payload),self.ask.ask("P1",self.user,self.payload),return_exceptions=True)
        self.assertEqual(sum(isinstance(item,HTTPException) for item in results),1)
        self.assertEqual(self.usage.execute.await_count,1)

    async def test_unknown_output_is_canonical_and_knowledge_never_changes(self):
        await self.approved();before=deepcopy(self.db["product_knowledge_versions"].docs)
        self.answer(status="not_covered",answer="UNSUPPORTED_CANARY",citations=[])
        result=await self.ask.ask("P1",self.user,self.payload)
        self.assertNotIn("UNSUPPORTED_CANARY",result["answer"])
        self.assertEqual(before,self.db["product_knowledge_versions"].docs)

    async def test_changed_knowledge_and_uncertain_provider_do_not_replay(self):
        await self.approved()
        async def changed(*args):
            self.db["product_knowledge_versions"].docs.clear()
            return SimpleNamespace(text=json.dumps({"status":"supported","answer":"Saved.","citations":[{"claim_id":"K1"}]}))
        self.usage.execute.side_effect=changed
        with self.assertRaises(HTTPException) as stale:await self.ask.ask("P1",self.user,self.payload)
        self.assertEqual(stale.exception.status_code,409)
        self.assertEqual(self.db["knowledge_ask_requests"].docs[0]["state"],"uncertain")

    async def test_prompt_and_feature_contract_reject_client_scope_and_no_plaintext_fallback(self):
        await self.approved();self.answer()
        response=await self.client.post(self.base+"/ask",json={**self.payload.model_dump(),"account_id":"ACC_B","extra_field":"SECRET_CANARY"})
        self.assertEqual(response.status_code,422)
        self.assertNotIn("SECRET_CANARY",response.text)
        self.usage.execute.assert_not_called()
        from unittest.mock import patch
        with patch.object(settings,"knowledge_encryption_required",True):
            with self.assertRaises(HTTPException) as blocked:fixtures.ProductKnowledge(self.db,self.usage)
        self.assertEqual(blocked.exception.status_code,503)

    async def test_quotes_come_from_approved_statement_not_generated_or_source_excerpt(self):
        first = await self.approved()
        statement = "Landing page buttons:\nHome, Pricing, Login, Signup."
        draft = await self.service.create_version("P1", "reviewer", fixtures.KnowledgeDraft(
            title="Reviewed landing rule", parent_version_id=first["version_id"],
            claims=[{**self.claim, "statement": statement}]))
        await self.service.approve("P1", "reviewer", draft["version_id"])
        self.answer()
        result = await self.ask.ask("P1", self.user, self.payload)
        self.assertEqual(result["citations"][0]["quote"], statement)
        self.assertEqual(result["citations"][0]["source_quote"], "Show Draft saved.")
        request = self.usage.execute.call_args.args[3]
        context = json.loads(request.prompt)["approved_knowledge"]["claims"][0]
        self.assertEqual(set(context), {"claim_id", "statement", "epistemic_status"})
        reference = next(item for item in request.response_schema["$defs"].values()
                         if "claim_id" in item.get("properties", {}))
        self.assertEqual(reference["properties"]["claim_id"]["enum"], ["K1"])
        self.assertNotIn("quote", reference["properties"])
        self.assertEqual(self.usage.execute.await_count, 1)

    async def test_unknown_claim_id_is_rejected_without_generated_quote(self):
        await self.approved()
        self.answer(citations=[{"claim_id": "UNKNOWN"}])
        with self.assertRaises(HTTPException) as error:
            await self.ask.ask("P1", self.user, self.payload)
        self.assertEqual(error.exception.status_code, 502)
        self.assertEqual(self.usage.execute.await_count, 1)
        self.assertEqual(self.db["knowledge_ask_requests"].docs[0]["state"], "uncertain")

    async def test_model_cannot_supply_invented_quote_or_source_link(self):
        await self.approved()
        self.answer(citations=[{"claim_id": "K1", "quote": "Invented wording", "source_id": "FOREIGN"}])
        with self.assertRaises(HTTPException) as error:
            await self.ask.ask("P1", self.user, self.payload)
        self.assertEqual(error.exception.status_code, 502)
        self.assertNotIn("Invented wording", str(error.exception.detail))
        self.assertEqual(self.usage.execute.await_count, 1)

    async def test_legacy_approved_knowledge_needs_no_migration(self):
        approved = await self.approved()
        legacy = {**deepcopy(approved), "_id": approved["version_id"]}
        for key in ("knowledge_contract_version", "changes", "removed_claim_ids"):
            legacy.pop(key)
        self.db["product_knowledge_versions"].docs[:] = [legacy]
        before = deepcopy(legacy)
        self.answer()
        result = await self.ask.ask("P1", self.user, self.payload)
        self.assertEqual(result["citations"][0]["quote"], self.claim["statement"])
        self.assertEqual(self.db["product_knowledge_versions"].docs, [before])

    async def test_http_response_keeps_existing_citation_contract(self):
        await self.approved()
        self.answer()
        response = await self.client.post(self.base + "/ask", json=self.payload.model_dump())
        self.assertEqual(response.status_code, 200, response.text)
        citation = response.json()["citations"][0]
        self.assertEqual(set(citation), {"claim_id", "quote", "source_id", "source_quote", "information_type", "segment_index"})
        self.assertEqual(citation["quote"], self.claim["statement"])
        self.assertEqual(citation["source_id"], self.claim["source_id"])
