"""M3 service/ASGI regression with synthetic auth, database and metered AI doubles."""
import unittest

from fastapi import HTTPException
import test_product_knowledge as fixtures
from app.models.product_knowledge import ReviewStoryAnalysis


class StoryAnalysisModes(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await fixtures.KnowledgeTests.asyncSetUp(self)

    approved = fixtures.KnowledgeTests.approved
    analysis = fixtures.KnowledgeTests.analysis

    async def test_validation_errors_are_specific_to_analysis_mode(self):
        finding={'finding_id':'F1','category':'ambiguity','severity':'warning','description':'Detail','question':'Clarify?','knowledge_claim_id':'K_missing'}
        with self.assertRaises(HTTPException) as story_error:await self.explicit('story_only',[finding])
        self.assertEqual(story_error.exception.detail,'Story Clarity received an unsupported AI reference. No analysis was saved.')
        await self.approved()
        with self.assertRaises(HTTPException) as comparison_error:await self.explicit('knowledge_aware',[finding])
        self.assertEqual(comparison_error.exception.detail,'AI returned an unsupported knowledge reference. No analysis was saved.')
        self.assertEqual(self.db['story_analyses'].docs,[])

    async def test_contact_record_type_story_accepts_whitespace_only_quote_changes(self):
        story=self.db['stories'].docs[0]
        story.update(title='Create a record types in Contact Object',description='As a user while creating a contact display record types Employee, Guest, Agent',acceptance_criteria='This is applicable for any user profile\nFor Record Type as Agent - Display Add Agency Button\nFor Record Type as Guest & Employee - Do not display Add Agency Button')
        quote='This is applicable for any user profile For Record Type as Agent - Display Add Agency Button'
        finding={'finding_id':'F1','category':'missing_detail','severity':'warning','description':'Button behavior needs detail','question':'What happens after Add Agency?','criterion_quote':quote}
        result=await self.explicit('story_only',[finding])
        self.assertEqual(result['findings'][0]['criterion_quote'],'This is applicable for any user profile\nFor Record Type as Agent - Display Add Agency Button')
        self.assertIsNone(result['findings'][0]['story_quote'])
        self.assertIsNone(result['knowledge_version_id'])
        self.assertEqual(self.usage.execute.await_count,1)
        self.assertEqual(self.usage.execute.call_args.args[3].max_retries,0)

    async def test_knowledge_comparison_accepts_source_layout_changes_but_rejects_unknown_claims(self):
        await self.mixed()
        self.db['stories'].docs[0]['acceptance_criteria']='Agent can add Agency.\nGuest cannot add Agency.'
        finding={'finding_id':'F1','category':'knowledge_conflict','severity':'blocker','description':'Check rule conflict','question':'Is this intentional?','criterion_quote':'Agent can add Agency. Guest cannot add Agency.','knowledge_claim_id':'K1'}
        result=await self.explicit('knowledge_aware',[finding])
        self.assertEqual(result['findings'][0]['criterion_quote'],self.db['stories'].docs[0]['acceptance_criteria'])
        self.assertEqual(result['findings'][0]['knowledge_claim_id'],'K1')
        self.assertEqual(result['included_knowledge_claim_ids'],['K1'])
        before=len(self.db['story_analyses'].docs)
        for identity in ('K2','K_missing',None):
            finding['knowledge_claim_id']=identity
            with self.assertRaises(HTTPException):await self.explicit('knowledge_aware',[finding])
        self.assertEqual(len(self.db['story_analyses'].docs),before)

    async def test_description_quote_is_reclassified_with_source_not_claimed_as_criteria(self):
        self.db['stories'].docs[0].update(description='Show Employee, Guest, Agent record types.',acceptance_criteria=None)
        finding={'finding_id':'F1','category':'ambiguity','severity':'warning','description':'Scope needs detail','question':'What is the default type?','criterion_quote':'Employee, Guest, Agent'}
        result=await self.explicit('story_only',[finding])
        self.assertIsNone(result['findings'][0]['criterion_quote'])
        self.assertEqual(result['findings'][0]['story_field'],'description')
        self.assertEqual(result['findings'][0]['story_quote'],'Employee, Guest, Agent')
        stored=await self.service.latest_analysis('P1','ST1')
        self.assertEqual(stored['findings'],result['findings'])

    async def test_quote_matching_does_not_change_values_punctuation_or_invent_sources(self):
        self.db['stories'].docs[0].update(description='Guest & Employee cannot add Agency.',acceptance_criteria='Agent can add Agency.')
        for quote in ('Guest and Employee cannot add Agency.','Agent cannot add Agency.','agent can add Agency.','Agent can add Agency!'):
            finding={'finding_id':'F1','category':'ambiguity','severity':'warning','description':'Detail','question':'Clarify?','criterion_quote':quote}
            with self.assertRaises(HTTPException):await self.explicit('story_only',[finding])
        self.assertEqual(self.db['story_analyses'].docs,[])
        finding.update(criterion_quote=None,story_quote='Agent can add Agency.',story_field='description')
        with self.assertRaises(HTTPException):await self.explicit('story_only',[finding])
        self.assertEqual(self.db['story_analyses'].docs,[])

    async def test_story_only_without_criteria_review_cannot_enable_generation(self):
        self.db["stories"].docs[0]["acceptance_criteria"] = None
        result = await self.analysis()
        self.assertEqual(result["analysis_mode"], "story_only")
        self.assertIsNone(result["knowledge_version_id"])
        self.assertFalse((await self.service.latest_analysis("P1", "ST1"))["stale"])
        await self.service.review_analysis("P1", "reviewer", "ST1", result["analysis_id"], ReviewStoryAnalysis(resolutions=[]))
        self.assertEqual((await self.service.analysis_summaries("P1", ["ST1"]))["ST1"]["state"], "reviewed")
        with self.assertRaises(HTTPException) as failure:
            await self.service.generation_context("P1", "ST1")
        self.assertEqual(failure.exception.status_code, 409)
        self.assertEqual(self.usage.execute.call_args.args[3].max_retries, 0)

    async def test_story_only_with_criteria_is_not_trusted_generation(self):
        result = await self.analysis()
        await self.service.review_analysis("P1", "reviewer", "ST1", result["analysis_id"], ReviewStoryAnalysis(resolutions=[]))
        with self.assertRaises(HTTPException):
            await self.service.generation_context("P1", "ST1")
        await self.approved()
        self.assertTrue((await self.service.latest_analysis("P1", "ST1"))["stale"])
        self.assertEqual((await self.service.analysis_summaries("P1", ["ST1"]))["ST1"]["state"], "stale")
        with self.assertRaises(HTTPException):
            await self.service.review_analysis("P1", "reviewer", "ST1", result["analysis_id"], ReviewStoryAnalysis(resolutions=[]))

    async def test_knowledge_aware_without_criteria_and_legacy_compatibility(self):
        await self.approved()
        self.db["stories"].docs[0]["acceptance_criteria"] = ""
        result = await self.analysis()
        self.assertEqual(result["analysis_mode"], "knowledge_aware")
        self.db["story_analyses"].docs[0].pop("analysis_mode")
        self.assertFalse((await self.service.latest_analysis("P1", "ST1"))["stale"])
        self.db["stories"].docs[0]["description"] = "New requirement"
        self.assertTrue((await self.service.latest_analysis("P1", "ST1"))["stale"])

    async def test_story_only_rejects_invented_knowledge_and_criteria(self):
        finding = {"finding_id": "F1", "category": "knowledge_conflict", "severity": "blocker",
                   "description": "Unsupported", "question": "Clarify?"}
        with self.assertRaises(HTTPException) as failure:
            await self.analysis([finding])
        self.assertEqual(failure.exception.status_code, 502)
        finding.update(category="ambiguity", knowledge_claim_id="K_missing")
        with self.assertRaises(HTTPException):
            await self.analysis([finding])
        finding.update(knowledge_claim_id=None, criterion_quote="Invented criterion")
        with self.assertRaises(HTTPException):
            await self.analysis([finding])
        self.assertEqual(self.db["story_analyses"].docs, [])

    async def test_blank_story_rejected_before_metered_call_and_member_review_guard(self):
        self.db["stories"].docs[0].update(description=" ", acceptance_criteria=None)
        response = await self.client.post(self.base + "/stories/ST1/analyze")
        self.assertEqual(response.status_code, 409)
        self.usage.execute.assert_not_called()
        self.db["stories"].docs[0]["description"] = "Users save a draft for later editing."
        result = await self.analysis()
        self.user["role"] = "MEMBER"
        response = await self.client.post(self.base + f'/stories/ST1/analysis/{result["analysis_id"]}/review', json={"resolutions": []})
        self.assertEqual(response.status_code, 403)

    async def explicit(self,mode,findings=None):
        import json
        from types import SimpleNamespace
        self.usage.execute.return_value=SimpleNamespace(text=json.dumps({"summary":"Review supplied inputs","findings":findings or []}))
        return await self.service.analyze("P1",self.user,"ST1",analysis_mode=mode)

    async def mixed(self):
        from app.models.product_knowledge import KnowledgeSourceInput, KnowledgeDraft
        current=await self.approved()
        source=await self.service.add_source("P1","reviewer",KnowledgeSourceInput(title="Story proposal",kind="document",text="Show Signup."),origin={"kind":"story","story_id":"ST1"})
        second={**self.claim,"claim_id":"K2","source_id":source["source_id"],"statement":"Show Signup.","quote":"Show Signup.","epistemic_status":"inferred"}
        draft=await self.service.create_version("P1","reviewer",KnowledgeDraft(title="Mixed rules",parent_version_id=current["version_id"],claims=[self.claim,second]))
        return await self.service.approve("P1","reviewer",draft["version_id"])

    async def test_explicit_story_clarity_with_same_story_knowledge_remains_independent(self):
        import json
        await self.mixed()
        self.db['stories'].docs[0]['acceptance_criteria']=None
        result=await self.explicit('story_only')
        prompt=json.loads(self.usage.execute.call_args.args[3].prompt)
        self.assertIsNone(prompt['knowledge']);self.assertIsNone(result['knowledge_version_id'])
        self.assertEqual(result['analysis_scope_version'],1)
        await self.service.review_analysis('P1','reviewer','ST1',result['analysis_id'],ReviewStoryAnalysis(resolutions=[]))
        # An explicit story-only review never claimed dependence on knowledge.
        self.db['product_knowledge_versions'].docs.clear()
        self.assertFalse((await self.service.latest_analysis('P1','ST1'))['stale'])
        with self.assertRaises(HTTPException):await self.service.generation_context('P1','ST1')
        self.db['stories'].docs[0]['description']='Changed story'
        self.assertTrue((await self.service.latest_analysis('P1','ST1'))['stale'])
        self.assertEqual((await self.service.analysis_summaries('P1',['ST1']))['ST1']['state'],'stale')

    async def test_comparison_filters_same_story_rules_and_history_before_model(self):
        import json
        approved=await self.mixed()
        result=await self.explicit('knowledge_aware')
        prompt=json.loads(self.usage.execute.call_args.args[3].prompt)
        self.assertEqual([c['claim_id'] for c in prompt['knowledge']['claims']],['K1'])
        self.assertNotIn('Show Signup.',json.dumps(prompt['knowledge']))
        self.assertEqual(result['knowledge_version_id'],approved['version_id'])
        self.assertEqual(result['included_knowledge_claim_ids'],['K1'])
        self.assertEqual(result['excluded_knowledge_claims'][0]['claim_id'],'K2')
        self.assertEqual(len((await self.service.active('P1'))['claims']),2)
        await self.service.review_analysis('P1','reviewer','ST1',result['analysis_id'],ReviewStoryAnalysis(resolutions=[]))
        with self.assertRaises(HTTPException):await self.service.generation_context('P1','ST1')

    async def test_no_eligible_rules_never_silently_falls_back_or_spends(self):
        await self.approved()
        self.db['product_knowledge_sources'].docs[0]['origin']={'kind':'story','story_id':'ST1'}
        with self.assertRaises(HTTPException) as failure:await self.explicit('knowledge_aware')
        self.assertEqual(failure.exception.status_code,409)
        self.assertIn('K1',failure.exception.detail);self.assertIn('Story clarity',failure.exception.detail)
        self.usage.execute.assert_not_called()
        # Legacy callers retain their original rejection; no hidden fallback.
        with self.assertRaises(HTTPException):await self.analysis()
        self.usage.execute.assert_not_called()
        result=await self.explicit('story_only')
        self.assertEqual(result['analysis_mode'],'story_only')

    async def test_excluded_and_foreign_claim_citations_are_rejected(self):
        await self.mixed()
        finding={"finding_id":"F1","category":"knowledge_conflict","severity":"blocker","description":"Conflict","question":"Which?","knowledge_claim_id":"K2"}
        with self.assertRaises(HTTPException) as failure:await self.explicit('knowledge_aware',[finding])
        self.assertEqual(failure.exception.status_code,502)
        finding['knowledge_claim_id']=None
        with self.assertRaises(HTTPException):await self.explicit('knowledge_aware',[finding])
        self.assertEqual(self.db['story_analyses'].docs,[])
        self.usage.execute.reset_mock()
        self.db['product_knowledge_sources'].docs[0]['project_id']='OTHER'
        with self.assertRaises(HTTPException):await self.explicit('knowledge_aware')
        self.usage.execute.assert_not_called()

    async def test_explicit_api_modes_validate_and_authorize_before_metering(self):
        response=await self.client.post(self.base+'/stories/ST1/analyze?analysis_mode=invalid')
        self.assertEqual(response.status_code,422);self.usage.execute.assert_not_called()
        response=await self.client.post('/projects/P2/knowledge/stories/ST1/analyze?analysis_mode=story_only')
        self.assertEqual(response.status_code,404);self.usage.execute.assert_not_called()
        response=await self.client.post(self.base+'/stories/ST1/analyze?analysis_mode=knowledge_aware')
        self.assertEqual(response.status_code,409);self.usage.execute.assert_not_called()
        await self.explicit('story_only')
        response=await self.client.post(self.base+'/stories/ST1/analyze?analysis_mode=story_only')
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['analysis_mode'],'story_only')
