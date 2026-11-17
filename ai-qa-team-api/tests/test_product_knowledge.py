"""Synthetic ASGI/auth/database/provider checks; no real AI or Mongo calls."""
import os
import json
import unittest
from unittest.mock import patch, AsyncMock
from types import SimpleNamespace

import httpx
from fastapi import FastAPI, HTTPException

with patch.dict(os.environ, {"MONGO_URI": "mongodb://localhost:27017", "MONGO_DB": "knowledge_tests",
                            "REDIS_HOST": "localhost", "REDIS_PORT": "6399", "REDIS_USERNAME": "",
                            "REDIS_PASSWORD": "", "SESSION_SECRET_KEY": "test", "JWT_SECRET_KEY": "test"}):
    from app.config import settings, FeatureFlags
    from app.routes import product_knowledge_routes as routes
    from app.services.product_knowledge import ProductKnowledge
    from app.services.knowledge_test_design import KnowledgeTestDesign
    from app.models.product_knowledge import KnowledgeSourceInput, KnowledgeDraft
    from app.services.ai.ai_usage_policy import AIOperation, get_ai_usage_policy
    from test_visual_specifications import Collection as BaseCollection, Cursor


class Collection(BaseCollection):
    @staticmethod
    def matches(doc, query):
        return all(doc.get(key) in value["$in"] if isinstance(value,dict) and "$in" in value else BaseCollection.matches(doc,{key:value}) for key,value in query.items())
    def aggregate(self,pipeline):
        rows=[row for row in self.docs if self.matches(row,pipeline[0]["$match"])]
        rows.sort(key=lambda row:(row["created_at"],row["_id"]),reverse=True)
        groups={}
        for row in rows: groups.setdefault(row["story_id"],{"_id":row["story_id"],"latest":row})
        return Cursor(list(groups.values()))


class KnowledgeTests(unittest.IsolatedAsyncioTestCase):
    async def test_bulk_head_reads_match_canonical_chain_with_constant_round_trips(self):
        head=await self.approved()
        for index in range(12):
            draft=await self.service.create_version('P1','reviewer',KnowledgeDraft(title='Revision',parent_version_id=head['version_id'],claims=[{**self.claim,'statement':f'Reviewed expectation {index}'}]))
            head=await self.service.approve('P1','reviewer',draft['version_id'])
        versions=self.db['product_knowledge_versions']
        versions.docs.append({'_id':'unreachable-legacy-receipt','record_type':'knowledge_approval','scope_project_id':'P1'})
        with patch.object(versions,'find_one',wraps=versions.find_one) as one,patch.object(versions,'find',wraps=versions.find) as many:
            actual=await self.service.active('P1')
            self.assertLessEqual(one.call_count,3)
            self.assertLessEqual(many.call_count,2)
            projection=many.call_args.args[1]
            self.assertNotIn('claims',projection)
        self.assertEqual(actual,await self.service._active_sequential('P1'))
        # A broken historical link must not be ignored simply because the head is valid.
        historical=next(d for d in versions.docs if d.get('version_id') and d['version_id']!=head['version_id'])
        historical['content_digest']='tampered'
        with self.assertRaises(HTTPException) as error:await self.service.active('P1')
        self.assertEqual(error.exception.status_code,409)

    async def test_bulk_head_large_unreachable_history_keeps_legacy_fallback(self):
        from unittest.mock import AsyncMock
        head=await self.approved()
        for index in range(2049):
            self.db['product_knowledge_versions'].docs.append({'_id':f'unreachable-{index}','record_type':'knowledge_approval','scope_project_id':'P1','approved_version_id':'not-reachable'})
        with patch.object(self.service,'_active_sequential',new=AsyncMock(return_value=head)) as fallback:
            self.assertEqual(await self.service.active('P1'),head)
            fallback.assert_awaited_once_with('P1')

    async def test_compact_overview_keeps_current_and_fetchable_evidence_and_history(self):
        old=await self.approved()
        draft=await self.service.create_version('P1','reviewer',KnowledgeDraft(title='Successor',parent_version_id=old['version_id'],claims=[{**self.claim,'statement':'Updated save behavior'}]))
        new=await self.service.approve('P1','reviewer',draft['version_id'])
        response=await self.client.get(self.base+'?current_only=true')
        self.assertEqual(response.status_code,200,response.text)
        compact=response.json()
        self.assertEqual([v['version_id'] for v in compact['versions']],[new['version_id']])
        self.assertEqual(compact['sources'][0]['text'],'')
        self.assertFalse(compact['sources'][0]['details_loaded'])
        evidence=await self.client.get(self.base+'/sources/'+self.claim['source_id'])
        self.assertEqual(evidence.json()['text'],'Show Draft saved.')
        self.assertEqual((await self.client.get(self.base+'/versions/'+old['version_id'])).status_code,200)

    async def test_review_name_is_recorded_immutably(self):
        analysis=await self.analysis([])
        self.user['name']='Alice Reviewer'
        path=self.base+'/stories/ST1/analysis/'+analysis['analysis_id']+'/review'
        self.assertEqual((await self.client.post(path,json={'resolutions':[]})).status_code,200)
        self.user['name']='Different Name'
        await self.client.post(path,json={'resolutions':[]})
        latest=await self.client.get(self.base+'/stories/ST1/analysis')
        self.assertEqual(latest.json()['reviewed_by_name'],'Alice Reviewer')

    async def test_approval_name_is_server_owned_and_immutable_on_retry(self):
        first = await self.approved()
        draft = await self.service.create_version("P1", "reviewer", KnowledgeDraft(title="Correction",
            parent_version_id=first["version_id"], claims=[{**self.claim,"statement":"Updated rule"}]))
        self.user["name"] = "Alice Reviewer"
        path=self.base+"/versions/"+draft["version_id"]+"/approve"
        response=await self.client.post(path)
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()["approved_by_name"],"Alice Reviewer")
        self.user["name"] = "Changed Profile"
        self.assertEqual((await self.client.post(path)).json()["approved_by_name"],"Alice Reviewer")

    async def asyncSetUp(self):
        self.db = {key: Collection() for key in ("product_knowledge_sources", "product_knowledge_versions", "story_analyses", "prompt_definitions")}
        self.db["stories"] = Collection({"project_id": "P1", "story_id": "ST1", "title": "Save draft",
                                        "description": "Synthetic", "acceptance_criteria": "Show Draft saved.", "out_of_scope": ""})
        self.usage = SimpleNamespace(execute=AsyncMock())
        self.service = ProductKnowledge(self.db, self.usage)
        self.user = {"_id": "reviewer", "role": "ADMIN"}
        async def member(project, user):
            if project != "P1": raise HTTPException(404)
        async def admin(project, user):
            await member(project, user)
            if user["role"] != "ADMIN": raise HTTPException(403)
        for target, key, value in ((routes, "db", self.db), (routes, "service", lambda: self.service),
                                  (routes, "require_project_member", member), (routes, "require_project_admin", admin),
                                  (settings, "features", FeatureFlags(product_knowledge=True, story_analysis=True, scenario_generation=True, test_generation=True))):
            patcher = patch.object(target, key, value); patcher.start(); self.addCleanup(patcher.stop)
        app = FastAPI(); app.include_router(routes.router)
        app.dependency_overrides[routes.get_current_user] = lambda: self.user
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")
        self.addAsyncCleanup(self.client.aclose)
        self.base = "/projects/P1/knowledge"

    async def approved(self):
        source = await self.service.add_source("P1", "reviewer", KnowledgeSourceInput(title="Guide", kind="document", text="Show Draft saved."))
        self.claim = {"claim_id": "K1", "category": "business_rule", "statement": "Show Draft saved.",
                      "epistemic_status": "expected", "source_id": source["source_id"], "segment_index": None, "quote": "Show Draft saved."}
        draft = await self.service.create_version("P1", "reviewer", KnowledgeDraft(title="Rules", claims=[self.claim]))
        return await self.service.approve("P1", "reviewer", draft["version_id"])

    async def analysis(self, findings=None):
        self.usage.execute.return_value = SimpleNamespace(text=json.dumps({"summary": "Review save behavior", "findings": findings or []}))
        return await self.service.analyze("P1", self.user, "ST1")

    async def test_project_and_feature_guards_and_safe_validation(self):
        self.assertEqual((await self.client.get("/projects/P2/knowledge")).status_code, 404)
        settings.features.product_knowledge = False
        self.assertEqual((await self.client.post(self.base + "/sources", json={})).status_code, 403)
        settings.features.product_knowledge = True
        response = await self.client.post(self.base + "/sources", json={"title": "x", "kind": "document", "text": "", "secret": "CANARY"})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("CANARY", response.text)

    async def test_citations_approval_successors_and_cross_project_source(self):
        approved = await self.approved()
        self.user["role"] = "MEMBER"
        self.assertEqual((await self.client.post(self.base + f'/versions/{approved["version_id"]}/approve')).status_code, 403)
        wrong = {**self.claim, "quote": "invented"}
        response = await self.client.post(self.base + "/versions", json={"title": "wrong", "claims": [wrong]})
        self.assertEqual(response.status_code, 422)
        self.assertEqual((await self.client.post("/projects/P2/knowledge/versions", json={"title": "wrong", "claims": [self.claim]})).status_code, 404)
        self.claim["statement"] = "Updated expectation"
        successor = await self.service.create_version("P1", "reviewer", KnowledgeDraft(title="Updated", claims=[self.claim], parent_version_id=approved["version_id"]))
        await self.service.approve("P1", "reviewer", successor["version_id"])
        original = await self.service.record("product_knowledge_versions", "P1", approved["version_id"])
        self.assertEqual(original["claims"][0]["statement"], "Show Draft saved.")
        self.assertEqual((await self.service.active("P1"))["version_id"], successor["version_id"])

    async def test_blockers_require_review_and_changes_invalidate_context(self):
        await self.approved()
        finding = {"finding_id": "F1", "category": "ambiguity", "severity": "blocker", "description": "When?", "question": "When should it appear?", "criterion_quote": "Draft saved", "knowledge_claim_id": "K1"}
        analysis = await self.analysis([finding])
        self.assertEqual((await self.client.post(self.base + f'/stories/ST1/analysis/{analysis["analysis_id"]}/review', json={"resolutions": []})).status_code, 422)
        with self.assertRaises(HTTPException): await self.service.generation_context("P1", "ST1")
        response = await self.client.post(self.base + f'/stories/ST1/analysis/{analysis["analysis_id"]}/review', json={"resolutions": [{"finding_id": "F1", "decision": "clarified", "rationale": "After Save is clicked."}]})
        self.assertEqual(response.status_code, 200, response.text)
        await self.service.generation_context("P1", "ST1")
        self.db["stories"].docs[0]["acceptance_criteria"] = "Changed expected behavior"
        with self.assertRaises(HTTPException): await self.service.generation_context("P1", "ST1")
        self.assertTrue((await self.service.latest_analysis("P1", "ST1"))["stale"])

    async def test_metered_extraction_validates_exact_transcript_segment(self):
        source = await self.service.add_source("P1", "reviewer", KnowledgeSourceInput(title="Demo", kind="recording_transcript", segments=[{"start_seconds": 10, "end_seconds": 15, "text": "Show Draft saved."}]))
        claim = {"claim_id": "K1", "category": "workflow", "statement": "Saved", "epistemic_status": "observed", "source_id": source["source_id"], "segment_index": 0, "quote": "Draft saved"}
        self.usage.execute.return_value = SimpleNamespace(text=json.dumps({"claims": [claim], "clarification_questions": ["Is this expected?"]}))
        result = await self.service.extract("P1", self.user, source["source_id"])
        self.assertEqual(result.claims[0].epistemic_status, "observed")
        self.assertEqual(self.usage.execute.call_args.args[0], AIOperation.KNOWLEDGE_EXTRACTION)
        self.assertEqual(self.usage.execute.call_args.args[3].prompt_version, "CODE_DEFAULT_V1")
        self.db["prompt_definitions"].docs.append({
            "prompt_key": "KNOWLEDGE_EXTRACTION_V1", "active_version": 2,
            "versions": [{"version": 2, "status": "ACTIVE", "system_prompt": "Preserve product terminology."}]})
        await self.service.extract("P1", self.user, source["source_id"])
        request = self.usage.execute.call_args.args[3]
        self.assertEqual(request.prompt_version, "2")
        self.assertIn("Preserve product terminology.", request.system_prompt)
        self.assertIn("untrusted data", request.system_prompt)
        claim["segment_index"] = 1
        self.usage.execute.return_value.text = json.dumps({"claims": [claim], "clarification_questions": []})
        with self.assertRaises(HTTPException): await self.service.extract("P1", self.user, source["source_id"])

    async def test_scenario_design_returns_distinct_intent_not_procedure(self):
        approved = await self.approved(); analysis = await self.analysis()
        from app.models.product_knowledge import ReviewStoryAnalysis
        await self.service.review_analysis("P1", "reviewer", "ST1", analysis["analysis_id"], ReviewStoryAnalysis(resolutions=[]))
        intent = {"title": "Save", "description": "Save a draft", "purpose": "Confirm save", "role": None, "coverage_type": "happy_path", "preconditions": [], "expected_outcome": "Show Draft saved.", "acceptance_criteria_refs": ["Show Draft saved."], "rule_references": ["K1"]}
        self.usage.execute.return_value = SimpleNamespace(text=json.dumps({"scenarios": [intent]}))
        plans, context = await KnowledgeTestDesign(self.db, self.usage).scenarios("P1", self.user, await self.service.story("P1", "ST1"), 3, "basic")
        self.assertEqual(len(plans), 1)  # fewer supported intents are valid, never fabricate three
        self.assertNotIn("steps", plans[0]); self.assertEqual(context["knowledge"]["version_id"], approved["version_id"])
        self.usage.execute.return_value.text = json.dumps({"scenarios": [intent, intent]})
        with self.assertRaises(HTTPException): await KnowledgeTestDesign(self.db, self.usage).scenarios("P1", self.user, await self.service.story("P1", "ST1"), 3, "basic")

    async def test_detailed_case_design_has_assertions_and_rejects_stale_scenario(self):
        approved = await self.approved(); analysis = await self.analysis()
        from app.models.product_knowledge import ReviewStoryAnalysis
        await self.service.review_analysis("P1", "reviewer", "ST1", analysis["analysis_id"], ReviewStoryAnalysis(resolutions=[]))
        scenario = {"_id": object(), "project_id": "P1", "story_id": "ST1", "scenario_id": "SC1", "title": "Save",
                    "knowledge_version_id": approved["version_id"], "story_analysis_id": analysis["analysis_id"]}
        case = {"title": "Save a draft", "purpose": "Verify persistence notification", "preconditions": [], "public_data": [],
                "procedure": [{"instruction": "Click Save", "expected": "Draft saved"}], "assertions": ["Draft saved"],
                "cleanup": [], "acceptance_criteria_refs": ["Show Draft saved."], "rule_references": ["K1"]}
        self.usage.execute.return_value = SimpleNamespace(text=json.dumps({"testcases": [case]}))
        cases, _ = await KnowledgeTestDesign(self.db, self.usage).testcases("P1", self.user, scenario, 2)
        self.assertEqual(cases[0]["procedure"][0]["expected"], "Draft saved")
        self.assertEqual(cases[0]["assertions"], ["Draft saved"])
        self.assertNotIn("_id", json.loads(self.usage.execute.call_args.args[3].prompt)["scenario"])
        scenario["knowledge_version_id"] = "f" * 32
        with self.assertRaises(HTTPException): await KnowledgeTestDesign(self.db, self.usage).testcases("P1", self.user, scenario, 1)

    async def test_specification_pins_knowledge_and_rule_change_requires_review(self):
        approved = await self.approved(); analysis = await self.analysis()
        from app.models.product_knowledge import ReviewStoryAnalysis
        from app.models.visual_specification import SpecificationDraft, SpecificationPreviewSelection
        from app.services.visual_specifications import VisualSpecifications
        await self.service.review_analysis("P1", "reviewer", "ST1", analysis["analysis_id"], ReviewStoryAnalysis(resolutions=[]))
        settings.features.reusable_workflows = True
        self.db.update({"visual_workflow_versions": Collection(), "visual_test_spec_versions": Collection(),
            "testcases": Collection({"project_id": "P1", "testcase_id": "TC1", "scenario_id": "SC1"}),
            "scenarios": Collection({"project_id": "P1", "scenario_id": "SC1", "story_id": "ST1", "approved": True}),
            "environments": Collection({"project_id": "P1", "env_id": "ENV1", "revision": 1, "base_url": "https://test.salesforce.com", "credentials": []})})
        service = VisualSpecifications(self.db, b"test")
        draft = await service.create_specification("P1", "TC1", "reviewer", SpecificationDraft(steps=[{"action": "assert_text", "expected": "Draft saved"}]))
        await service.approve_specification("P1", "TC1", "reviewer", draft["version_id"])
        preview = await service.preview("P1", "TC1", draft["version_id"], SpecificationPreviewSelection(environment_id="ENV1"))
        self.assertEqual(preview.knowledge_version_id, approved["version_id"])
        self.assertEqual(preview.story_analysis_id, analysis["analysis_id"])
        self.claim["statement"] = "Save notification changed"
        next_draft = await self.service.create_version("P1", "reviewer", KnowledgeDraft(title="Changed", claims=[self.claim], parent_version_id=approved["version_id"]))
        await self.service.approve("P1", "reviewer", next_draft["version_id"])
        state = await service.latest_specification("P1", "TC1")
        self.assertTrue(state["review_required"])
        self.assertEqual(state["version"]["knowledge_version_id"], approved["version_id"])
        self.assertEqual(state["version"]["status"], "approved")

    def test_all_supported_ai_tasks_have_bounded_policies(self):
        for operation in AIOperation:
            policy = get_ai_usage_policy(operation)
            self.assertGreater(policy.credit_cost, 0)
            self.assertGreater(policy.max_input_chars, 0)
            self.assertGreater(policy.max_output_tokens, 0)

    async def test_analysis_summaries_states_and_project_scope(self):
        self.assertEqual((await self.client.get(self.base+'/analysis-summaries?story_ids=ST1')).json()['ST1']['state'],'not_analyzed')
        await self.approved();analysis=await self.analysis()
        self.assertEqual((await self.client.get(self.base+'/analysis-summaries?story_ids=ST1')).json()['ST1']['state'],'needs_review')
        await self.service.review_analysis('P1','reviewer','ST1',analysis['analysis_id'],__import__('app.models.product_knowledge',fromlist=['ReviewStoryAnalysis']).ReviewStoryAnalysis(resolutions=[]))
        self.assertEqual((await self.client.get(self.base+'/analysis-summaries?story_ids=ST1')).json()['ST1']['state'],'reviewed')
        self.db['stories'].docs[0]['title']='Changed'
        self.assertEqual((await self.client.get(self.base+'/analysis-summaries?story_ids=ST1')).json()['ST1']['state'],'stale')
        self.assertEqual((await self.client.get('/projects/P2/knowledge/analysis-summaries?story_ids=ST1')).status_code,404)
        self.assertEqual((await self.client.get(self.base+'/analysis-summaries?story_ids=../../private')).status_code,422)

    async def test_story_proposals_are_inferred_reviewed_and_cannot_validate_their_own_story(self):
        async def extract(*args,**kwargs):
            source=json.loads(args[3].prompt)
            return SimpleNamespace(text=json.dumps({'claims':[{'claim_id':'K0','category':'business_rule','statement':'Show Draft saved.','epistemic_status':'expected','source_id':source['source_id'],'segment_index':None,'quote':'Show Draft saved.'}],'clarification_questions':['When is it saved?']}))
        self.usage.execute.side_effect=extract
        response=await self.client.post(self.base+'/stories/ST1/suggest-knowledge')
        self.assertEqual(response.status_code,200,response.text);result=response.json()
        self.assertTrue(result['requires_review']);self.assertEqual(result['claims'][0]['epistemic_status'],'inferred')
        self.assertIsNone(await self.service.active('P1'))
        self.assertEqual(result['source']['origin']['story_id'],'ST1')
        result['claims'][0]['epistemic_status']='expected'
        draft=await self.service.create_version('P1','reviewer',KnowledgeDraft(title='Reviewed story proposal',claims=result['claims']))
        await self.service.approve('P1','reviewer',draft['version_id'])
        with self.assertRaises(HTTPException) as failure:await self.service.analyze('P1',self.user,'ST1')
        self.assertEqual(failure.exception.status_code,409)
        self.assertEqual(self.usage.execute.await_count,1)
        self.assertEqual((await self.client.post('/projects/P2/knowledge/stories/ST1/suggest-knowledge')).status_code,404)

    async def test_incremental_addition_preserves_rules_answers_and_history(self):
        first = await self.approved()
        second_claim = {**self.claim, "claim_id": "K2", "statement": "Another reviewed rule"}
        draft = await self.service.create_version("P1", "reviewer", KnowledgeDraft(
            title="Incremental", claims=[second_claim], clarification_answers={"When?": "After saving"}))
        self.assertEqual([claim["claim_id"] for claim in draft["claims"]], ["K1", "K2"])
        self.assertEqual([item["action"] for item in draft["changes"]], ["add"])
        second = await self.service.approve("P1", "reviewer", draft["version_id"])
        # Rejected/omitted proposals do not remove approved content or answers.
        next_draft = await self.service.create_version("P1", "reviewer", KnowledgeDraft(title="No accepted change"))
        self.assertEqual(next_draft["claims"], second["claims"])
        self.assertEqual(next_draft["clarification_answers"], {"When?": "After saving"})
        self.assertEqual(next_draft["changes"], [])
        history = await self.service.overview("P1")
        self.assertEqual(sum(item["status"] == "approved" for item in history["versions"]), 2)
        self.assertEqual((await self.service.record("product_knowledge_versions", "P1", first["version_id"]))["claims"], first["claims"])
        self.assertFalse(self.usage.execute.called)

    async def test_targeted_correction_and_explicit_removal_only(self):
        await self.approved()
        draft = await self.service.create_version("P1", "reviewer", KnowledgeDraft(title="Add", claims=[{**self.claim,"claim_id":"K2"}]))
        await self.service.approve("P1", "reviewer", draft["version_id"])
        correction = {**self.claim, "statement": "Corrected expectation"}
        draft = await self.service.create_version("P1", "reviewer", KnowledgeDraft(title="Correct", claims=[correction], parent_version_id=(await self.service.active("P1"))["version_id"]))
        self.assertEqual([claim["claim_id"] for claim in draft["claims"]], ["K1", "K2"])
        self.assertEqual(draft["changes"][0]["action"], "replace")
        self.assertEqual(draft["changes"][0]["before"]["statement"], "Show Draft saved.")
        await self.service.approve("P1", "reviewer", draft["version_id"])
        removal = await self.service.create_version("P1", "reviewer", KnowledgeDraft(title="Remove", removed_claim_ids=["K2"], removal_reasons={"K2":"Feature retired"}, parent_version_id=(await self.service.active("P1"))["version_id"]))
        self.assertEqual(len((await self.service.active("P1"))["claims"]), 2)
        self.assertEqual(removal["changes"][0]["action"], "remove")
        self.assertEqual([claim["claim_id"] for claim in removal["claims"]], ["K1"])
        await self.service.approve("P1", "reviewer", removal["version_id"])
        self.assertEqual(len((await self.service.active("P1"))["claims"]), 1)
        for ids, claims in [(["unknown"], []), (["K1", "K1"], []), (["K1"], [correction])]:
            with self.assertRaises(HTTPException) as failure:
                await self.service.create_version("P1", "reviewer", KnowledgeDraft(title="Invalid", claims=claims, removed_claim_ids=ids))
            self.assertEqual(failure.exception.status_code, 422)

    async def test_two_competing_approvals_have_one_atomic_winner(self):
        import asyncio
        first = await self.approved()
        drafts = [await self.service.create_version("P1", "reviewer", KnowledgeDraft(title="Change", claims=[{**self.claim, "claim_id": f"K{i}"}])) for i in (2,3)]
        original_active = self.service.active
        ready = asyncio.Event(); readers = 0
        async def simultaneous_read(project):
            nonlocal readers
            result = await original_active(project)
            readers += 1
            if readers == 2: ready.set()
            await ready.wait()
            return result
        with patch.object(self.service, "active", side_effect=simultaneous_read):
            results = await asyncio.gather(*(self.service.approve("P1", "reviewer", draft["version_id"]) for draft in drafts), return_exceptions=True)
        winners = [result for result in results if isinstance(result, dict)]
        losers = [result for result in results if isinstance(result, HTTPException)]
        self.assertEqual(len(winners), 1); self.assertEqual([error.status_code for error in losers], [409])
        self.assertEqual((await self.service.active("P1"))["version_id"], winners[0]["version_id"])
        with self.assertRaises(HTTPException):
            await self.service.create_version("P1", "reviewer", KnowledgeDraft(title="Stale", claims=[self.claim], parent_version_id=first["version_id"]))
        await self.service.approve("P1", "reviewer", first["version_id"])
        self.assertEqual((await self.service.active("P1"))["version_id"], winners[0]["version_id"])

    async def test_uncertain_approval_recovers_without_ai_or_second_publish(self):
        draft = await self.service.create_version("P1", "reviewer", KnowledgeDraft(title="First", claims=[(await self.approved())["claims"][0]]))
        collection = self.db["product_knowledge_versions"]
        insert = collection.insert_one
        async def accepted_then_disconnected(document):
            await insert(document)
            raise TimeoutError("synthetic lost acknowledgement")
        with patch.object(collection, "insert_one", side_effect=accepted_then_disconnected):
            with self.assertRaises(TimeoutError):
                await self.service.approve("P1", "reviewer", draft["version_id"])
        self.assertEqual((await self.service.active("P1"))["version_id"], draft["version_id"])
        recovered = await self.service.approve("P1", "another reviewer", draft["version_id"])
        self.assertEqual(recovered["approved_by"], "reviewer")
        self.assertEqual(recovered["status"], "approved")
        self.assertFalse(self.usage.execute.called)

    async def test_legacy_approved_snapshot_is_retained_but_unsafe_draft_requires_resave(self):
        from copy import deepcopy
        approved = await self.approved()
        self.db["product_knowledge_versions"].docs.clear()
        legacy = {**deepcopy(approved), "_id": approved["version_id"]}
        legacy.pop("knowledge_contract_version"); legacy.pop("changes"); legacy.pop("removed_claim_ids")
        self.db["product_knowledge_versions"].docs.append(legacy)
        draft = await self.service.create_version("P1", "reviewer", KnowledgeDraft(title="Increment", claims=[{**self.claim, "claim_id":"K2"}]))
        await self.service.approve("P1", "reviewer", draft["version_id"])
        self.assertEqual(len((await self.service.active("P1"))["claims"]), 2)
        self.assertEqual(self.db["product_knowledge_versions"].docs[0], legacy)
        unsafe = {**legacy, "_id": "a"*32, "version_id": "a"*32, "status":"draft"}
        self.db["product_knowledge_versions"].docs.append(unsafe)
        with self.assertRaises(HTTPException) as failure:
            await self.service.approve("P1", "reviewer", unsafe["version_id"])
        self.assertEqual(failure.exception.status_code, 409)

    async def test_combined_bound_and_tampered_draft_fail_without_changing_active(self):
        first = await self.approved()
        proposals = [{**self.claim, "claim_id":f"K{i}"} for i in range(2,102)]
        with self.assertRaises(HTTPException) as failure:
            await self.service.create_version("P1", "reviewer", KnowledgeDraft(title="Overflow", claims=proposals))
        self.assertEqual(failure.exception.status_code, 413)
        draft = await self.service.create_version("P1", "reviewer", KnowledgeDraft(title="Draft", claims=[]))
        raw = next(row for row in self.db["product_knowledge_versions"].docs if row.get("version_id") == draft["version_id"])
        raw["claims"] = []
        with self.assertRaises(HTTPException) as failure:
            await self.service.approve("P1", "reviewer", draft["version_id"])
        self.assertEqual(failure.exception.status_code, 409)
        self.assertEqual((await self.service.active("P1"))["version_id"], first["version_id"])

    async def test_corrections_require_explicit_base_and_removing_every_rule_is_explicit(self):
        approved = await self.approved()
        with self.assertRaises(HTTPException) as missing_reason:
            await self.service.create_version("P1", "reviewer", KnowledgeDraft(
                title="Unexplained removal", removed_claim_ids=["K1"], parent_version_id=approved["version_id"]))
        self.assertEqual(missing_reason.exception.status_code, 422)
        for payload in (KnowledgeDraft(title="Correction", claims=[{**self.claim, "statement":"Changed"}]),
                        KnowledgeDraft(title="Removal", removed_claim_ids=["K1"], removal_reasons={"K1":"Feature retired"})):
            with self.assertRaises(HTTPException) as failure:
                await self.service.create_version("P1", "reviewer", payload)
            self.assertEqual(failure.exception.status_code, 409)
        draft = await self.service.create_version("P1", "reviewer", KnowledgeDraft(
            title="Explicit removal", removed_claim_ids=["K1"], removal_reasons={"K1":"Feature retired"}, parent_version_id=approved["version_id"]))
        self.assertEqual(len((await self.service.active("P1"))["claims"]), 1)
        result = await self.service.approve("P1", "reviewer", draft["version_id"])
        self.assertEqual(result["claims"], [])
        self.assertEqual((await self.service.record("product_knowledge_versions", "P1", approved["version_id"]))["claims"], approved["claims"])

    async def test_historical_version_api_is_scoped_and_not_limited_to_overview(self):
        first = await self.approved()
        self.user["role"] = "MEMBER"
        response = await self.client.get(self.base + "/versions/" + first["version_id"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "approved")
        self.assertNotIn("_id", response.json())
        foreign = await self.client.get("/projects/P2/knowledge/versions/" + first["version_id"])
        self.assertEqual(foreign.status_code, 404)
        self.assertEqual((await self.client.get(self.base + "/versions/" + "f"*32)).status_code, 404)
        self.assertFalse(self.usage.execute.called)

    async def test_compat_old_client_payload_cannot_drop_rules_or_forge_approval(self):
        approved = await self.approved()
        # Legacy client shape: no contract marker, removal list or approval metadata.
        old_payload = {"title": "Old client", "claims": [{**self.claim, "claim_id":"K2"}]}
        saved = await self.client.post(self.base + "/versions", json=old_payload)
        self.assertEqual(saved.status_code, 201)
        self.assertEqual({item["claim_id"] for item in saved.json()["claims"]}, {"K1", "K2"})
        for field, value in [("status", "approved"), ("knowledge_contract_version", 1),
                             ("approved_by", "FORGED"), ("changes", []), ("content_digest", "f"*64)]:
            forged = await self.client.post(self.base + "/versions", json={**old_payload, field:value})
            self.assertEqual(forged.status_code, 422)
        url = self.base + "/versions/" + saved.json()["version_id"]
        self.assertEqual((await self.client.patch(url, json={"status":"approved"})).status_code, 405)
        self.assertEqual((await self.client.put(url, json={"status":"approved"})).status_code, 405)
        self.assertEqual((await self.service.active("P1"))["version_id"], approved["version_id"])

    async def test_compat_simultaneous_http_first_approvals_have_one_winner(self):
        import asyncio
        await self.approved()
        self.db["product_knowledge_versions"].docs.clear()
        drafts = [await self.service.create_version("P1", "reviewer", KnowledgeDraft(title="Initial", claims=[{**self.claim,"claim_id":key}])) for key in ("K1","K2")]
        original = self.service.active; gate = asyncio.Event(); readers = 0
        async def together(project):
            nonlocal readers
            result = await original(project); readers += 1
            if readers == 2: gate.set()
            await gate.wait(); return result
        with patch.object(self.service, "active", side_effect=together):
            responses = await asyncio.gather(*(self.client.post(self.base+"/versions/"+draft["version_id"]+"/approve") for draft in drafts))
        self.assertEqual(sorted(item.status_code for item in responses), [200,409])
        winner = next(item.json() for item in responses if item.status_code == 200)
        self.assertEqual((await self.service.active("P1"))["version_id"],winner["version_id"])

    async def test_compat_repeated_http_approval_preserves_actor_time_and_receipt(self):
        import asyncio
        approved = await self.approved()
        url = self.base+"/versions/"+approved["version_id"]+"/approve"
        before = len(self.db["product_knowledge_versions"].docs)
        responses = await asyncio.gather(self.client.post(url),self.client.post(url),self.client.post(url))
        self.assertTrue(all(item.status_code == 200 for item in responses))
        self.assertTrue(all(item.json()["approved_by"] == approved["approved_by"] and
                            item.json()["approved_at"] == approved["approved_at"] for item in responses))
        self.assertEqual(len(self.db["product_knowledge_versions"].docs), before)

    async def test_compat_legacy_approved_retry_and_legacy_draft_reject(self):
        from copy import deepcopy
        approved = await self.approved()
        collection = self.db["product_knowledge_versions"]
        collection.docs.clear()
        legacy = {**deepcopy(approved),"_id":approved["version_id"]}
        legacy.pop("knowledge_contract_version");legacy.pop("changes");legacy.pop("removed_claim_ids")
        collection.docs.append(legacy)
        response=await self.client.post(self.base+"/versions/"+legacy["version_id"]+"/approve")
        self.assertEqual(response.status_code,200);self.assertEqual(response.json(),self.service.public(legacy))
        unsafe={**legacy,"_id":"b"*32,"version_id":"b"*32,"status":"draft"}
        collection.docs.append(unsafe)
        self.assertEqual((await self.client.post(self.base+"/versions/"+unsafe["version_id"]+"/approve")).status_code,409)
        self.assertEqual(collection.docs[0],legacy)

    async def test_compat_characterization_old_backend_direct_write_can_disconnect_receipts(self):
        # Hazard characterization, NOT a desired-behavior/rollout acceptance test.
        # An old backend can write directly; the new API cannot control that binary.
        from copy import deepcopy
        approved = await self.approved()
        legacy = {**deepcopy(approved),"_id":"e"*32,"version_id":"e"*32,
                  "status":"approved","approved_at":"2099-01-01T00:00:00Z","claims":[]}
        for key in ("knowledge_contract_version","changes","removed_claim_ids"):
            legacy.pop(key,None)
        self.db["product_knowledge_versions"].docs.append(legacy)
        self.assertEqual((await self.service.active("P1"))["version_id"],legacy["version_id"])
        # Earlier approval remains immutable/readable, but is no longer active.
        historical=await self.service.record("product_knowledge_versions","P1",approved["version_id"])
        self.assertEqual(historical["status"],"approved")
        self.assertEqual(historical["claims"],approved["claims"])

    async def test_compat_simultaneous_same_draft_approval_is_idempotent(self):
        import asyncio
        await self.approved()
        draft=await self.service.create_version("P1","reviewer",KnowledgeDraft(title="Same draft"))
        original=self.service.active;gate=asyncio.Event();readers=0
        async def together(project):
            nonlocal readers
            result=await original(project);readers+=1
            if readers==3:gate.set()
            await gate.wait();return result
        with patch.object(self.service,"active",side_effect=together):
            results=await asyncio.gather(*(self.client.post(self.base+"/versions/"+draft["version_id"]+"/approve",json={"approved_by":"FORGED"}) for _ in range(3)))
        self.assertEqual([item.status_code for item in results],[200,200,200])
        self.assertEqual(len({item.json()["approved_at"] for item in results}),1)
        self.assertTrue(all(item.json()["approved_by"]=="reviewer" for item in results))
        receipts=[row for row in self.db["product_knowledge_versions"].docs if row.get("approved_version_id")==draft["version_id"]]
        self.assertEqual(len(receipts),1)

    async def test_compat_old_http_parent_cannot_overwrite_current_knowledge(self):
        first=await self.approved()
        draft=await self.service.create_version("P1","reviewer",KnowledgeDraft(title="Next",claims=[{**self.claim,"claim_id":"K2"}]))
        await self.service.approve("P1","reviewer",draft["version_id"])
        response=await self.client.post(self.base+"/versions",json={"title":"Stale browser","claims":[self.claim],"parent_version_id":first["version_id"]})
        self.assertEqual(response.status_code,409)
        self.assertEqual((await self.service.active("P1"))["version_id"],draft["version_id"])
