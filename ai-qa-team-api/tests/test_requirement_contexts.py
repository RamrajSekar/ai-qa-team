"""Release approvals with synthetic database/auth/AI; no live provider or execution."""
import asyncio
import json
import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4
from fastapi import HTTPException
import test_product_knowledge as fixtures
from app.models.requirement_context import RequirementDraft
from app.models.product_knowledge import ReviewStoryAnalysis
from app.services.requirement_contexts import RequirementContexts
from app.services.knowledge_test_design import KnowledgeTestDesign
from app.services.test_design_review import TestDesignReview


class MongoCollection(fixtures.Collection):
    async def count_documents(self,query):
        return sum(self.matches(row,{k:v for k,v in query.items() if k!='$or'}) for row in self.docs)

    async def insert_one(self,doc):
        doc={**doc,'_id':doc.get('_id') or uuid4().hex}
        await super().insert_one(doc)
        return SimpleNamespace(inserted_id=doc['_id'])

    async def find_one_and_update(self,query,update,**kwargs):
        # Mongo creates missing parents for dotted $set paths.
        row=next((row for row in self.docs if self.matches(row,query)),None)
        if row is not None:
            for key in update.get('$set',{}):
                current=row
                for part in key.split('.')[:-1]:current=current.setdefault(part,{})
        return await super().find_one_and_update(query,update,**kwargs)


class RequirementTests(unittest.IsolatedAsyncioTestCase):
    approved=fixtures.KnowledgeTests.approved
    async def asyncSetUp(self):
        await fixtures.KnowledgeTests.asyncSetUp(self)
        for collection in ('requirement_contexts','scenarios','testcases','test_design_documents','executions'):
            self.db[collection]=MongoCollection()
        fixtures.settings.features.story_management=True
        self.contexts=RequirementContexts(self.db)
        self.usage.execute.return_value=SimpleNamespace(text=json.dumps({'summary':'Clarify scope','findings':[]}))
        self.version=await self.approved()
        self.analysis=await self.service.analyze('P1',self.user,'ST1',analysis_mode='story_only')
        await self.service.review_analysis('P1','reviewer','ST1',self.analysis['analysis_id'],ReviewStoryAnalysis(resolutions=[]))
        self.usage.execute.reset_mock()

    def payload(self,**fields):
        return RequirementDraft(request_id=uuid4().hex,analysis_id=self.analysis['analysis_id'],
            basis=fields.pop('basis','approved_change'),target_release=fields.pop('target_release','Release 2'),
            decisions=fields.pop('decisions',[{'decision':'intentional_change','action':'remove','rule_id':'K1',
                'rationale':'Intentional enhancement removes save confirmation.','expected_result':'Save confirmation is absent.'}]),**fields)

    async def context(self,**fields):
        row=await self.contexts.create('P1','ST1','author',self.payload(**fields))
        return await self.contexts.approve('P1','ST1',row['context_id'],{**self.user,'name':'Reviewer'})

    async def test_approved_change_is_separate_pinned_and_does_not_change_knowledge(self):
        before=deepcopy(self.db['product_knowledge_versions'].docs)
        context=await self.context()
        self.assertEqual(context['status'],'approved');self.assertEqual(context['approver']['approved_by_name'],'Reviewer')
        resolved=await self.service.generation_context('P1','ST1',context['context_id'])
        self.assertEqual(resolved['design_basis'],'approved_change')
        self.assertFalse(resolved['independent_knowledge_validation'])
        self.assertNotIn('Show Draft saved.',resolved['requirements_story']['acceptance_criteria'])
        self.assertEqual(self.db['stories'].docs[0]['acceptance_criteria'],'Show Draft saved.')
        self.assertEqual(resolved['knowledge']['claims'][0]['statement'],'Save confirmation is absent.')
        self.assertEqual(resolved['knowledge']['claims'][0]['requirement_basis'],'human_approved_change')
        self.assertEqual(self.db['product_knowledge_versions'].docs,before)
        self.assertEqual(self.db['executions'].docs,[]);self.usage.execute.assert_not_called()
        with self.assertRaises(HTTPException):await self.service.generation_context('P1','ST1')

    async def test_non_intentional_decisions_remain_saved_but_cannot_approve(self):
        for decision in ('needs_clarification','correct_story'):
            row=await self.contexts.create('P1','ST1','author',self.payload(decisions=[{'decision':decision,'rationale':'Ask owner to clarify.'}]))
            with self.assertRaises(HTTPException):await self.contexts.approve('P1','ST1',row['context_id'],self.user)
            self.assertEqual((await self.contexts.view(await self.contexts.row('P1','ST1',row['context_id'])))['status'],'draft')

    async def test_activation_flags_designs_only_and_repeat_is_idempotent(self):
        self.db['scenarios'].docs=[{'project_id':'P1','scenario_id':'SC1','knowledge_version_id':self.version['version_id'],'approved':True,'title':'Existing'}]
        self.db['testcases'].docs=[{'project_id':'P1','testcase_id':'TC1','knowledge_version_id':self.version['version_id'],'title':'Existing case'}]
        self.db['executions'].docs=[{'project_id':'P1','verdict':'Passed','version_id':'historical'}]
        before=deepcopy(self.db['executions'].docs);context=await self.context()
        self.assertEqual(context['impact']['scenarios'][0]['id'],'SC1')
        result=await self.contexts.activate('P1','ST1',context['context_id'],'reviewer')
        self.assertEqual(result['status'],'active')
        self.assertTrue(self.db['scenarios'].docs[0]['requirements_review_required'])
        self.assertTrue(self.db['scenarios'].docs[0]['approved'])
        await self.contexts.activate('P1','ST1',context['context_id'],'other')
        self.assertEqual(self.db['executions'].docs,before)

    async def test_simultaneous_activation_has_one_winner_and_approval_retry_keeps_actor(self):
        first=await self.context();second=await self.context()
        results=await asyncio.gather(*[self.contexts.activate('P1','ST1',c['context_id'],'reviewer') for c in (first,second)],return_exceptions=True)
        self.assertEqual(sum(isinstance(value,HTTPException) for value in results),1)
        retry=await self.contexts.approve('P1','ST1',first['context_id'],{'_id':'different','name':'Other'})
        self.assertEqual(retry['approver']['approved_by_name'],'Reviewer')

    async def test_successor_preserves_prior_release_changes_and_history(self):
        first=await self.context();await self.contexts.activate('P1','ST1',first['context_id'],'reviewer')
        second=await self.context(decisions=[{'decision':'intentional_change','action':'add','rationale':'Add navigation.','expected_result':'Home remains visible.'}])
        resolved=await self.contexts.resolve('P1','ST1',second['context_id'])
        statements={claim['statement'] for claim in resolved['knowledge']['claims']}
        self.assertEqual(statements,{'Save confirmation is absent.','Home remains visible.'})
        await self.contexts.activate('P1','ST1',second['context_id'],'reviewer')
        with self.assertRaises(HTTPException):await self.contexts.resolve('P1','ST1',first['context_id'])
        self.assertEqual((await self.contexts.view(await self.contexts.row('P1','ST1',first['context_id'])))['status'],'superseded')

    async def test_pending_activation_reconciles_after_metadata_write_failure(self):
        self.db['scenarios'].docs=[{'project_id':'P1','scenario_id':'SC1','knowledge_version_id':self.version['version_id']}]
        context=await self.context()
        with patch.object(self.db['scenarios'],'update_one',side_effect=RuntimeError('synthetic interrupted write')):
            with self.assertRaises(HTTPException) as error:await self.contexts.activate('P1','ST1',context['context_id'],'reviewer')
        self.assertEqual(error.exception.status_code,503)
        with self.assertRaises(HTTPException):await self.contexts.resolve('P1','ST1',context['context_id'])
        result=await self.contexts.activate('P1','ST1',context['context_id'],'reviewer')
        self.assertEqual(result['status'],'active')

    async def test_story_only_provisional_never_claims_knowledge_and_requires_review(self):
        row=await self.contexts.create('P1','ST1','author',self.payload(basis='story_only_provisional',decisions=[]))
        with self.assertRaises(HTTPException):await self.contexts.resolve('P1','ST1',row['context_id'])
        await self.contexts.approve('P1','ST1',row['context_id'],self.user)
        result=await self.contexts.resolve('P1','ST1',row['context_id'])
        self.assertIsNone(result['knowledge']['version_id']);self.assertEqual(result['knowledge']['claims'],[])
        self.assertEqual(result['design_basis'],'story_only_provisional')
        with self.assertRaises(HTTPException):await self.contexts.activate('P1','ST1',row['context_id'],'reviewer')

    async def test_stale_story_and_missing_source_stop_before_model(self):
        context=await self.context();self.db['stories'].docs[0]['description']='Changed requirement'
        with self.assertRaises(HTTPException):await self.contexts.resolve('P1','ST1',context['context_id'])
        self.usage.execute.assert_not_called()

    async def test_http_project_role_and_payload_guards(self):
        payload=self.payload();path=self.base+'/stories/ST1/requirements'
        self.user['role']='MEMBER'
        result=await self.client.post(path,json=payload.model_dump());self.assertEqual(result.status_code,200,result.text)
        identity=result.json()['context_id']
        self.assertEqual((await self.client.post(path+'/'+identity+'/approve')).status_code,403)
        self.assertEqual((await self.client.get('/projects/P2/knowledge/stories/ST1/requirements')).status_code,404)
        self.assertEqual((await self.client.post(path,json={**payload.model_dump(),'approved_by':'FORGED'})).status_code,422)
        self.user['role']='ADMIN'
        self.assertEqual((await self.client.post(path+'/'+identity+'/approve')).status_code,200)
        self.assertEqual((await self.client.get(path+'/'+identity)).status_code,200)

    async def test_scenario_and_case_design_pin_context_and_reject_changed_selection(self):
        context=await self.context();identity=context['context_id']
        resolved=await self.contexts.resolve('P1','ST1',identity)
        intent={'title':'Removed confirmation','description':'Verify removal','purpose':'Confirm absence','role':None,'coverage_type':'negative',
            'preconditions':[],'expected_outcome':'Save confirmation is absent.','acceptance_criteria_refs':['Save confirmation is absent.'],'rule_references':['K1']}
        self.usage.execute.return_value=SimpleNamespace(text=json.dumps({'scenarios':[intent]}))
        plans,pinned=await KnowledgeTestDesign(self.db,self.usage).scenarios('P1',self.user,await self.service.story('P1','ST1'),1,'basic',identity)
        self.assertEqual(plans[0]['rule_references'],['K1']);self.assertEqual(pinned['requirements_context_id'],identity)
        scenario={'project_id':'P1','story_id':'ST1','scenario_id':'SC1','approved':True,**intent,
            'knowledge_version_id':self.version['version_id'],'story_analysis_id':self.analysis['analysis_id'],
            'requirements_context_id':identity,'requirements_context_digest':resolved['requirements_context_digest']}
        case={'title':'Verify absence','purpose':'Check removal','role':None,'preconditions':[],'public_data':[],
            'procedure':[{'instruction':'Save a draft','expected':'Save confirmation is absent.'}],'assertions':['Save confirmation is absent.'],
            'cleanup':[],'acceptance_criteria_refs':['Save confirmation is absent.'],'rule_references':['K1']}
        self.usage.execute.return_value=SimpleNamespace(text=json.dumps({'testcases':[case]}))
        cases,_=await KnowledgeTestDesign(self.db,self.usage).testcases('P1',self.user,scenario,1)
        self.assertEqual(cases[0]['assertions'],['Save confirmation is absent.'])
        self.db['scenarios'].docs=[scenario];self.db['testcases'].docs=[{'project_id':'P1','testcase_id':'TC1','scenario_id':'SC1',**{key:scenario[key] for key in ('knowledge_version_id','story_analysis_id','requirements_context_id','requirements_context_digest')}}]
        snapshot,_,_=await TestDesignReview(self.db).context('P1','TC1')
        self.assertEqual(snapshot['requirements_context_id'],identity);self.assertFalse(snapshot['source_context_changed'])
        scenario['requirements_context_digest']='forged'
        with self.assertRaises(HTTPException):await KnowledgeTestDesign(self.db,self.usage).testcases('P1',self.user,scenario,1)

    async def test_http_generation_propagates_context_into_approval_and_cases(self):
        from unittest.mock import AsyncMock
        from fastapi import FastAPI
        import httpx
        from app.routes import scenario_routes,testcase_routes
        from app.utils import subscription_dependency
        self.user['email']='reviewer@example.test'
        self.db['stories'].docs[0]['created_by']=self.user['email']
        self.db['projects']=MongoCollection({'project_id':'P1','created_by':self.user['email']})
        context=await self.context();identity=context['context_id']
        sub={'plan':'free','status':'active','billing_scope':'ACCOUNT','ai_allowance_version':1,
             'usage':{'ai_gen_used':3,'scenarios_used':0,'testcases_used':0,'testcases_basic_used':0},
             'limits':{'ai_gen_limit':3,'scenarios_limit':10,'testcases_limit':10,'testcases_basic_limit':10}}
        intent={'title':'Release removal','description':'Absence check','purpose':'Check removal','role':None,'coverage_type':'negative',
                'preconditions':[],'expected_outcome':'Save confirmation is absent.','acceptance_criteria_refs':['Save confirmation is absent.'],'rule_references':['K1']}
        case={'title':'Release case','purpose':'Check absence','role':None,'preconditions':[],'public_data':[],
              'procedure':[{'instruction':'Save','expected':'Save confirmation is absent.'}],'assertions':['Save confirmation is absent.'],
              'cleanup':[],'acceptance_criteria_refs':['Save confirmation is absent.'],'rule_references':['K1']}
        self.usage.execute.side_effect=[SimpleNamespace(text=json.dumps({'scenarios':[intent]})),SimpleNamespace(text=json.dumps({'testcases':[case]}))]
        app=FastAPI();app.include_router(scenario_routes.router);app.include_router(testcase_routes.router)
        app.dependency_overrides[scenario_routes.get_current_user]=lambda:self.user
        app.dependency_overrides[testcase_routes.get_current_user]=lambda:self.user
        app.dependency_overrides[subscription_dependency.get_current_user]=lambda:self.user
        patches=[]
        for target,name,value in [(subscription_dependency,'get_subscription',AsyncMock(return_value=sub))]:
            patcher=patch.object(target,name,value);patcher.start();patches.append(patcher)
        factory=lambda database:KnowledgeTestDesign(database,self.usage)
        factory.references=KnowledgeTestDesign.references
        for module in (scenario_routes,testcase_routes):
            for name,value in {'db':self.db,'get_subscription':AsyncMock(return_value=sub),
                               'require_project_member':AsyncMock(return_value=({}, {'role':'ADMIN'})),
                               'get_next_sequence':AsyncMock(return_value='SC_R' if module is scenario_routes else 'TC_R'),
                               'increment_usage':AsyncMock(),'KnowledgeTestDesign':factory}.items():
                patcher=patch.object(module,name,value);patcher.start();patches.append(patcher)
        try:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
                response=await client.post('/scenarios/generate-from-story?story_id=ST1&count=1&requirements_context_id='+identity)
                self.assertEqual(response.status_code,200,response.text)
                self.assertEqual(response.json()['scenarios'][0]['requirements_context_id'],identity)
                self.assertFalse(response.json()['scenarios'][0]['approved'])
                response=await client.put('/scenarios/SC_R/approve');self.assertEqual(response.status_code,200,response.text)
                response=await client.post('/testcases/generate?scenario_id=SC_R&project_id=P1&count=1')
                self.assertEqual(response.status_code,200,response.text)
                self.assertEqual(response.json()[0]['requirements_context_id'],identity)
                self.assertEqual(response.json()[0]['design_basis'],'approved_change')
                self.assertEqual(response.json()[0]['status'],'draft')
        finally:
            for patcher in reversed(patches):patcher.stop()

    async def test_provisional_without_acceptance_criteria_is_traceable_to_story(self):
        self.db['stories'].docs[0]['acceptance_criteria']=None
        for record in self.db['story_analyses'].docs:record['created_at']='2000-01-01T00:00:00+00:00'
        self.usage.execute.return_value=SimpleNamespace(text=json.dumps({'summary':'Review story','findings':[]}))
        self.analysis=await self.service.analyze('P1',self.user,'ST1',analysis_mode='story_only')
        current=await self.service.latest_analysis('P1','ST1')
        self.assertEqual(current['analysis_id'],self.analysis['analysis_id'],str(self.db['story_analyses'].docs))
        self.assertFalse(current['stale'],str(current))
        await self.service.review_analysis('P1','reviewer','ST1',self.analysis['analysis_id'],ReviewStoryAnalysis(resolutions=[]))
        context=await self.context(basis='story_only_provisional',decisions=[])
        resolved=await self.contexts.resolve('P1','ST1',context['context_id'])
        self.assertEqual(resolved['criteria_basis'],'provisional_story_requirements')
        self.assertEqual(resolved['requirements_story']['acceptance_criteria'],'Synthetic')
        self.assertIsNone(self.db['stories'].docs[0]['acceptance_criteria'])
