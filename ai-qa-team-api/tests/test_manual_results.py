"""Manual result/execution API checks with auth/Mongo doubles. No model/browser/network calls."""
import asyncio
from copy import deepcopy
import unittest
from unittest.mock import patch
import httpx
from fastapi import FastAPI, HTTPException
import test_test_design_review as design_fixture
from app.config import settings
from app.routes import test_result_routes as routes
from app.services.test_results import TestResults

class Cursor:
    def __init__(self, rows): self.rows=deepcopy(rows)
    def sort(self, fields, direction=None):
        for key, order in reversed(fields if isinstance(fields,list) else [(fields,direction)]): self.rows.sort(key=lambda row:row.get(key,''),reverse=order==-1)
        return self
    def skip(self,n): self.rows=self.rows[n:]; return self
    def limit(self,n): self.rows=self.rows[:n]; return self
    async def to_list(self,n): return deepcopy(self.rows[:n])
class Collection(design_fixture.Collection):
    @staticmethod
    def matches(doc,query):
        return all((doc.get(key) in value['$in'] if isinstance(value,dict) and '$in' in value else doc.get(key)==value) for key,value in query.items())
    @staticmethod
    def project(doc,projection):
        return {key:value for key,value in doc.items() if projection is None or key=='_id' or projection.get(key) or any(field.startswith(key+".") for field in projection)}
    def find(self,query,projection=None): return Cursor([self.project(row,projection) for row in self.docs if self.matches(row,query)])
    async def find_one(self,query,projection=None,*,sort=None):
        result=await super().find_one(query,sort=sort)
        return self.project(result,projection) if result else None
    def aggregate(self,pipeline):
        self.last_pipeline=deepcopy(pipeline)
        rows=[row for row in self.docs if self.matches(row,pipeline[0]['$match'])]
        rows.sort(key=lambda row:(row['recorded_at'],row['_id']),reverse=True)
        groups={}
        for row in rows: groups.setdefault((row['testcase_id'],row['mode']),{'latest':row})
        return Cursor(list(groups.values()))

class ManualResultTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        fixture=design_fixture.TestDesignReviewTests();fixture.addCleanup=self.addCleanup;fixture.addAsyncCleanup=self.addAsyncCleanup;await fixture.asyncSetUp()
        self.version=await fixture.approve(await fixture.draft())
        self.db={name:Collection(*collection.docs) for name,collection in fixture.db.items()}
        self.db['test_results']=Collection();self.db['manual_test_executions']=Collection()
        self.db['environments']=Collection({'_id':'env','project_id':'P1','env_id':'E1','name':'Synthetic','credentials':[{'password':'PRIVATE_CANARY'}]})
        self.user={'_id':'tester','email':'fixture@example.test','name':'Fixture Tester'}
        async def member(project,user):
            if project!='P1': raise HTTPException(404,'Access denied')
        for target,name,value in ((routes,'db',self.db),(routes,'require_project_member',member),(settings.features,'manual_test_results',True)):
            patcher=patch.object(target,name,value);patcher.start();self.addCleanup(patcher.stop)
        app=FastAPI();app.include_router(routes.router);app.dependency_overrides[routes.get_current_user]=lambda:self.user
        self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test');self.addAsyncCleanup(self.client.aclose)
        self.base='/projects/P1/test-results';self.payload={'version_id':self.version['version_id'],'idempotency_key':'a'*32,'actual_result':'Draft saved appeared','verdict':'passed','verified_expectation_ids':['step:0','assertion:0'],'environment_id':'E1'}
    async def record(self,**fields): return await self.client.post(self.base+'/cases/TC1',json={**self.payload,**fields})
    async def create_execution(self,**fields):
        return await self.client.post(self.base+'/executions',json={'title':'Release checks','release_cycle':'Release 2 / Cycle A','cases':[{'testcase_id':'TC1','version_id':self.version['version_id']}],'idempotency_key':'e'*32,**fields})
    async def test_results_are_append_only_and_do_not_edit_specification(self):
        before=deepcopy(self.db['test_design_documents'].docs)
        self.assertEqual((await self.record()).status_code,201)
        self.assertEqual((await self.record(idempotency_key='b'*32,verdict='failed',actual_result='Confirmation absent')).status_code,201)
        history=await self.client.get(self.base+'/cases/TC1');self.assertEqual(len(history.json()['records']),2);self.assertEqual(history.headers['cache-control'],'private, no-store')
        self.assertEqual(before,self.db['test_design_documents'].docs)
        self.assertNotIn('PRIVATE_CANARY',history.text)
    async def test_pass_requires_every_expected_result_and_rejects_untrusted_fields(self):
        self.assertEqual((await self.record(verified_expectation_ids=['step:0'])).status_code,422)
        self.assertEqual((await self.record(verified_expectation_ids=['invented'])).status_code,422)
        response=await self.record(mode='automated',secret='INPUT_CANARY');self.assertEqual(response.status_code,422);self.assertNotIn('INPUT_CANARY',response.text)
        self.assertEqual((await self.record(actual_result='   ')).status_code,422)
        self.assertEqual(self.db['test_results'].docs,[])
    async def test_duplicate_submission_and_conflicting_reuse(self):
        responses=await asyncio.gather(self.record(),self.record());self.assertEqual([r.status_code for r in responses],[201,201]);self.assertEqual(responses[0].json()['run_id'],responses[1].json()['run_id']);self.assertEqual(len(self.db['test_results'].docs),1)
        self.assertEqual((await self.record(actual_result='Different')).status_code,409)
    async def test_stale_approvals_block_new_attempt_but_history_survives(self):
        await self.record();self.db['stories'].docs[0]['title']='Changed'
        self.assertEqual((await self.record(idempotency_key='b'*32)).status_code,409)
        history=(await self.client.get(self.base+'/cases/TC1')).json();self.assertIsNone(history['eligible_version']);self.assertEqual(len(history['records']),1)
        self.assertEqual((await self.record()).status_code,201)
    async def test_project_feature_and_environment_isolation(self):
        self.assertEqual((await self.record(environment_id='FOREIGN')).status_code,404)
        for method,path,body in [('GET','?case_ids=TC1',None),('GET','/cases/TC1',None),('POST','/cases/TC1',self.payload),('GET','/executions',None)]:
            response=await self.client.request(method,'/projects/P2/test-results'+path,json=body);self.assertEqual(response.status_code,404)
        settings.features.manual_test_results=False
        self.assertEqual((await self.record()).status_code,403);self.assertEqual((await self.client.get(self.base+'?case_ids=TC1')).status_code,403)
    async def test_summaries_are_mode_and_project_scoped(self):
        await self.record()
        row=deepcopy(self.db['test_results'].docs[0]);row.update(_id='other',run_id='f'*32,mode='automated',adapter='future-trusted-adapter',verdict='blocked');self.db['test_results'].docs.append(row)
        row=deepcopy(row);row.update(_id='foreign',project_id='P2',verdict='failed');self.db['test_results'].docs.append(row)
        response=await self.client.get(self.base+'?case_ids=TC1');self.assertEqual(response.status_code,200);self.assertEqual(response.json()['TC1']['manual']['verdict'],'passed');self.assertEqual(response.json()['TC1']['automated']['verdict'],'blocked')
        self.assertEqual(self.db['test_results'].last_pipeline[0]['$match']['project_id'],'P1')
    async def test_execution_pins_release_and_versions_and_records_after_source_change(self):
        response=await self.create_execution();self.assertEqual(response.status_code,201,response.text);execution=response.json()['execution_id']
        self.db['stories'].docs[0]['title']='Later source change'
        saved=await self.record(execution_id=execution,environment_id=None,verdict='failed',actual_result='Wrong confirmation');self.assertEqual(saved.status_code,201,saved.text)
        result=await self.client.get(self.base+'/executions/'+execution);self.assertEqual(result.status_code,200);self.assertEqual(result.json()['manifest']['release_cycle'],'Release 2 / Cycle A');self.assertEqual(result.json()['lifecycle'],'completed');self.assertEqual(result.json()['results'][0]['verdict'],'failed')
        self.assertEqual((await self.record(execution_id=execution,idempotency_key='b'*32)).status_code,409)
        self.assertEqual(len(self.db['test_results'].docs),1)
    async def test_execution_creation_idempotence_stale_selection_and_access(self):
        a,b=await asyncio.gather(self.create_execution(),self.create_execution());self.assertEqual(a.json(),b.json());self.assertEqual(len(self.db['manual_test_executions'].docs),1)
        self.assertEqual((await self.client.get('/projects/P2/test-results/executions/'+a.json()['execution_id'])).status_code,404)
        self.assertEqual((await self.create_execution(release_cycle='Changed')).status_code,409)
        self.assertEqual((await self.create_execution(cases=[{'testcase_id':'TC1','version_id':'f'*32}],idempotency_key='d'*32)).status_code,409)
        self.assertEqual((await self.create_execution(cases=[{'testcase_id':'TC1','version_id':self.version['version_id']}]*2,idempotency_key='c'*32)).status_code,422)
    async def test_historical_pagination_and_cancelled_verdict(self):
        for i in range(22):
            response=await self.record(idempotency_key=f'{i:032x}',verdict='cancelled',actual_result='Stopped by tester');self.assertEqual(response.status_code,201)
        first=(await self.client.get(self.base+'/cases/TC1')).json();second=(await self.client.get(self.base+'/cases/TC1?skip=20')).json();self.assertTrue(first['has_more']);self.assertEqual(len(first['records']),20);self.assertEqual(len(second['records']),2);self.assertEqual(first['records'][0]['lifecycle'],'cancelled')

    async def test_unauthenticated_requests_reject_before_database_writes(self):
        self.client._transport.app.dependency_overrides.clear()
        self.assertEqual((await self.client.get(self.base+'?case_ids=TC1')).status_code,401)
        self.assertEqual((await self.record()).status_code,401)
        self.assertEqual(self.db['test_results'].docs,[])

    async def test_manual_review_of_legacy_case_without_knowledge_does_not_bypass_linked_case(self):
        from app.services.test_design_review import TestDesignReview
        from app.models.test_design_review import TestDesignDraft
        settings.features.product_knowledge=False;settings.features.story_analysis=False
        review=TestDesignReview(self.db)
        state=await review.state('P1','TC1');self.assertTrue(state['review_required']);self.assertIn('cannot bypass',state['context_error'])
        for collection in ('testcases','scenarios'):
            self.db[collection].docs[0].pop('knowledge_version_id',None)
        self.db['test_design_documents'].docs=[]
        content=deepcopy(self.version['case']);content['public_data']=[];content['rule_references']=[]
        draft=await review.create('P1','TC1','reviewer',TestDesignDraft(case=content,idempotency_key='d'*32))
        version=await review.approve('P1','TC1','reviewer',draft['version_id'])
        self.assertEqual(version['context']['design_basis'],'reviewer-authored-expectations-v1');self.assertIsNone(version['context']['knowledge_version_id'])
        response=await self.record(version_id=version['version_id']);self.assertEqual(response.status_code,201,response.text)

    async def test_optional_extra_checks_leave_every_step_required_for_pass(self):
        from app.services.test_design_review import TestDesignReview
        from app.models.test_design_review import TestDesignDraft
        review=TestDesignReview(self.db)
        content=deepcopy(self.version['case']);content['public_data']=[]
        for field in ('assertions','cleanup','acceptance_criteria_refs','rule_references'): content.pop(field,None)
        draft=await review.create('P1','TC1','reviewer',TestDesignDraft(case=content,parent_version_id=self.version['version_id'],idempotency_key='9'*32))
        approved=await review.approve('P1','TC1','reviewer',draft['version_id'])
        rejected=await self.record(version_id=approved['version_id'],verified_expectation_ids=[])
        self.assertEqual(rejected.status_code,422)
        saved=await self.record(version_id=approved['version_id'],verified_expectation_ids=['step:0'])
        self.assertEqual(saved.status_code,201,saved.text)

    async def test_design_status_tracks_current_pending_draft_and_approval(self):
        from app.services.test_design_review import TestDesignReview
        from app.models.test_design_review import TestDesignDraft
        results=TestResults(self.db)
        self.assertEqual((await results.summaries('P1',['TC1']))['TC1']['design_status'],'approved')
        content=deepcopy(self.version['case']);content['public_data']=[]
        review=TestDesignReview(self.db)
        version=await review.create('P1','TC1','reviewer',TestDesignDraft(case=content,parent_version_id=self.version['version_id'],idempotency_key='7'*32))
        self.assertEqual((await results.summaries('P1',['TC1']))['TC1']['design_status'],'in_review')
        await review.approve('P1','TC1','reviewer',version['version_id'])
        self.assertEqual((await results.summaries('P1',['TC1']))['TC1']['design_status'],'approved')

    async def test_executor_identity_comes_from_authenticated_user(self):
        response=await self.record()
        self.assertEqual(response.status_code,201)
        self.assertEqual(response.json()['executor_id'],'tester')
        self.assertEqual(response.json()['executor_display_name'],'Fixture Tester')
        self.user['name']='Renamed Tester'
        again=await self.record()
        self.assertEqual(again.json()['executor_display_name'],'Fixture Tester')
        rejected=await self.record(idempotency_key='0'*32,executor_display_name='Spoof')
        self.assertEqual(rejected.status_code,422)
