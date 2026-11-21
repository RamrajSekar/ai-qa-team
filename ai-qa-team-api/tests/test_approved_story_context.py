from resource_quota_double import ResourceQuotaDouble
"""Approved story authority reuse; no real DB/model/execution."""
import unittest
from fastapi import HTTPException
from app.services.approved_story_context import ApprovedStoryContext
from app.models.product_knowledge import ReviewStoryAnalysis, KnowledgeDraft
from test_requirement_contexts import RequirementTests
import test_product_knowledge as fixtures

class ApprovedStoryTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp=RequirementTests.asyncSetUp
    approved=fixtures.KnowledgeTests.approved

    async def test_story_only_reuses_review_without_creating_approval_and_pins_successors(self):
        service=ApprovedStoryContext(self.db)
        before=len(self.db['requirement_contexts'].docs)
        context=await service.prepare('P1','ST1')
        self.assertEqual(context['design_basis'],'approved_story_only')
        self.assertEqual(context['knowledge']['claims'],[])
        self.assertFalse(context['independent_knowledge_validation'])
        self.assertEqual(len(self.db['requirement_contexts'].docs),before+1)
        self.assertEqual((await service.prepare('P1','ST1'))['requirements_context_id'],context['requirements_context_id'])
        self.assertEqual((await self.service.generation_context('P1','ST1',context['requirements_context_id']))['story_approval']['approved_by'],'reviewer')
        self.db['stories'].docs[0]['description']='Changed'
        with self.assertRaises(HTTPException):await service.resolve('P1','ST1',context['requirements_context_id'])
        with self.assertRaises(HTTPException):await service.prepare('P1','ST1')
        self.usage.execute.assert_not_called()

    async def test_current_knowledge_review_reuses_independent_rules_and_rejects_changed_head(self):
        analysis=await self.service.analyze('P1',self.user,'ST1',analysis_mode='knowledge_aware')
        await self.service.review_analysis('P1','Alice','ST1',analysis['analysis_id'],ReviewStoryAnalysis(resolutions=[]))
        self.usage.execute.reset_mock()
        service=ApprovedStoryContext(self.db);context=await service.prepare('P1','ST1')
        self.assertEqual(context['design_basis'],'approved_story_with_knowledge')
        self.assertEqual(context['knowledge']['claims'][0]['claim_id'],'K1')
        draft=await self.service.create_version('P1','reviewer',KnowledgeDraft(title='New',claims=[{**self.claim,'claim_id':'K2'}]))
        await self.service.approve('P1','reviewer',draft['version_id'])
        with self.assertRaises(HTTPException):await service.resolve('P1','ST1',context['requirements_context_id'])
        self.usage.execute.assert_not_called()

    async def test_unreviewed_foreign_and_tampered_contexts_fail_closed(self):
        raw=self.db['story_analyses'].docs[-1];raw['status']='draft'
        service=ApprovedStoryContext(self.db)
        with self.assertRaises(HTTPException):await service.prepare('P1','ST1')
        raw['status']='reviewed';context=await service.prepare('P1','ST1')
        with self.assertRaises(HTTPException):await service.resolve('P2','ST1',context['requirements_context_id'])
        row=next(r for r in self.db['requirement_contexts'].docs if r.get('record_type')=='approved_story_generation')
        row['context']['requirements_story']['title']='Forged'
        with self.assertRaises(HTTPException):await service.resolve('P1','ST1',context['requirements_context_id'])

    async def test_testcases_inherit_exact_context_and_flow_prerequisites(self):
        import json
        from types import SimpleNamespace
        from app.services.knowledge_test_design import KnowledgeTestDesign
        design=KnowledgeTestDesign(self.db,self.usage)
        intent={'title':'Save draft','description':'Save behavior','purpose':'Verify save','role':None,'coverage_type':'happy_path','preconditions':['Draft is open'],'expected_outcome':'Show Draft saved.','acceptance_criteria_refs':['Show Draft saved.'],'rule_references':[]}
        self.usage.execute.return_value=SimpleNamespace(text=json.dumps({'scenarios':[intent]}))
        scenarios,context=await design.scenarios('P1',self.user,{'story_id':'ST1'},1,'basic',approved_story=True)
        scenario={**scenarios[0], 'scenario_id':'SC1','story_id':'ST1','approved':True,'knowledge_version_id':context['knowledge']['version_id'],'story_analysis_id':context['analysis']['analysis_id'], 'requirements_context_id':context['requirements_context_id'],'requirements_context_digest':context['requirements_context_digest']}
        case={'title':'Save draft details','purpose':'Check save','role':None,'preconditions':['Draft is open'],'public_data':[],'procedure':[{'instruction':'Save draft','expected':'Show Draft saved.'}],'assertions':['Show Draft saved.'],'cleanup':[],'acceptance_criteria_refs':['Show Draft saved.'],'rule_references':[]}
        self.usage.execute.return_value=SimpleNamespace(text=json.dumps({'testcases':[case]}))
        cases,inherited=await design.testcases('P1',self.user,scenario,1)
        self.assertEqual(inherited['requirements_context_id'],context['requirements_context_id'])
        self.assertEqual(cases[0]['preconditions'],['Draft is open'])
        self.assertEqual(inherited['story_approval'],context['story_approval'])

    async def test_catalog_edit_retains_omitted_preconditions_and_saves_explicit_changes(self):
        from unittest.mock import AsyncMock,patch
        from app.routes import testcase_routes as routes
        self.db['testcases'].docs.append({'_id':'case','project_id':'P1','testcase_id':'TC1','scenario_id':'SC1','title':'Case','description':'Description','steps':[],'status':'draft','code':'','created_by':'reviewer@example.test','created_at':'2026-11-17','preconditions':['Existing condition']})
        with patch.object(routes,'db',self.db),patch.object(routes,'require_project_member',new=AsyncMock()):
            user={'email':'reviewer@example.test'}
            result=await routes.edit_catalog_testcase('TC1',routes.CatalogTestCaseEdit(title='Edit',description='Description',steps=[]),'P1',user)
            self.assertEqual(result.preconditions,['Existing condition'])
            result=await routes.edit_catalog_testcase('TC1',routes.CatalogTestCaseEdit(title='Edit',description='Description',steps=[],preconditions=[' Updated condition ']),'P1',user)
            self.assertEqual(result.preconditions,['Updated condition'])
            result=await routes.edit_catalog_testcase('TC1',routes.CatalogTestCaseEdit(title='Edit',description='Description',steps=[],preconditions=[]),'P1',user)
            self.assertEqual(result.preconditions,[])

    async def test_http_generation_reuses_approval_for_member_without_extra_approval_endpoint(self):
        from fastapi import FastAPI
        import httpx,json
        from types import SimpleNamespace
        from unittest.mock import AsyncMock,patch
        from app.routes import scenario_routes
        from app.utils import subscription_dependency
        from app.services.knowledge_test_design import KnowledgeTestDesign
        from test_requirement_contexts import MongoCollection
        self.user.update(email='reviewer@example.test',role='TESTER')
        self.db['stories'].docs[0]['created_by']=self.user['email']
        self.db['projects']=MongoCollection({'project_id':'P1'})
        sub={'plan':'free','status':'active','billing_scope':'ACCOUNT','ai_allowance_version':1,'usage':{'ai_gen_used':0,'scenarios_used':0},'limits':{'ai_gen_limit':25,'scenarios_limit':10}}
        intent={'title':'Save draft','description':'Save behavior','purpose':'Verify save','role':None,'coverage_type':'happy_path','preconditions':[],'expected_outcome':'Show Draft saved.','acceptance_criteria_refs':['Show Draft saved.'],'rule_references':[]}
        self.usage.execute.return_value=SimpleNamespace(text=json.dumps({'scenarios':[intent]}))
        factory=lambda database:KnowledgeTestDesign(database,self.usage)
        app=FastAPI();app.include_router(scenario_routes.router)
        app.dependency_overrides[scenario_routes.get_current_user]=lambda:self.user
        app.dependency_overrides[subscription_dependency.get_current_user]=lambda:self.user
        patches=[]
        for module,name,value in [(scenario_routes,'ResourceQuota',ResourceQuotaDouble),(subscription_dependency,'get_subscription',AsyncMock(return_value=sub)),(scenario_routes,'db',self.db),(scenario_routes,'get_subscription',AsyncMock(return_value=sub)),(scenario_routes,'require_project_member',AsyncMock()),(scenario_routes,'get_next_sequence',AsyncMock(return_value='SC_NEW')),(scenario_routes,'increment_usage',AsyncMock()),(scenario_routes,'KnowledgeTestDesign',factory)]:
            patcher=patch.object(module,name,value);patcher.start();patches.append(patcher)
        try:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
                response=await client.post('/scenarios/generate-from-story?story_id=ST1&count=1&approved_story=true')
                self.assertEqual(response.status_code,200,response.text)
                scenario=response.json()['scenarios'][0]
                self.assertEqual(scenario['design_basis'],'approved_story_only')
                self.assertFalse(scenario['approved'])
                self.assertTrue(scenario['requirements_context_id'])
                self.assertEqual(sum(r.get('record_type')=='approved_story_generation' for r in self.db['requirement_contexts'].docs),1)
                self.assertFalse(any(r.get('record_type') in ('approval','story_change_approval') for r in self.db['requirement_contexts'].docs))
        finally:
            for patcher in reversed(patches):patcher.stop()
