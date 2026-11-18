"""Overview aggregation and reviewer isolation with synthetic canonical readers."""
import unittest
from copy import deepcopy
from unittest.mock import AsyncMock,patch
from fastapi import HTTPException,FastAPI
import httpx
import test_product_knowledge as fixtures
from test_requirement_contexts import MongoCollection
from app.config import settings,FeatureFlags
from app.services.pending_project_reviews import PendingProjectReviews
from app.services.product_knowledge import ProductKnowledge
from app.services.test_design_review import TestDesignReview
from app.services.approved_visual_run import digest

class PageCursor(fixtures.Cursor):
    def skip(self,count):self.docs=self.docs[count:];return self
    def limit(self,count):self.docs=self.docs[:count];return self

class PageCollection(MongoCollection):
    def find(self,query,projection=None):
        return PageCursor(super().find(query,projection).docs)

REAL_SUMMARIES=ProductKnowledge.analysis_summaries

class PendingReviewTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db={name:PageCollection() for name in ['projects','project_memberships','users','stories','scenarios','testcases','knowledge_training_reviews','product_knowledge_versions','requirement_contexts']}
        self.db['projects'].docs=[{'project_id':'P1','account_id':'ACC1'}]
        for email,name,role,account in [('alice@example.test','Alice','ADMIN','ACC1'),('carol@example.test','Carol','TESTER','ACC1'),('bob@example.test','Bob','ADMIN','ACC2')]:
            self.db['project_memberships'].docs.append({'project_id':'P1','status':'ACTIVE','email':email,'role':role})
            self.db['users'].docs.append({'email':email,'name':name,'account_id':account,'account_state':'ACTIVE'})
        self.db['stories'].docs=[{'project_id':'P1','story_id':'S1','title':'Pending story'},{'project_id':'P1','story_id':'S2','title':'Approved story'},{'project_id':'P2','story_id':'FOREIGN','title':'Private'}]
        self.db['scenarios'].docs=[{'project_id':'P1','scenario_id':'SC1','title':'Pending coverage','approved':False,'created_by':'carol@example.test'},{'project_id':'P1','scenario_id':'SC2','title':'Approved coverage','approved':True}]
        self.db['testcases'].docs=[{'project_id':'P1','testcase_id':'TC1','title':'Pending case'},{'project_id':'P1','testcase_id':'TC2','title':'Approved case'}]
        self.db['knowledge_training_reviews'].docs=[{'project_id':'P1','review_id':'R1','draft_version_id':'V1','title':'Pending knowledge','state':'reviewing','extraction_state':'completed'},{'project_id':'P1','review_id':'R2','draft_version_id':'V2','title':'Discarded','state':'rejected','extraction_state':'completed'},{'project_id':'P1','review_id':'R3','draft_version_id':'V3','title':'Approved knowledge','state':'saved','extraction_state':'completed'}]
        self.db['product_knowledge_versions'].docs=[{'_id':'V3','version_id':'V3','project_id':'P1','status':'approved'}]
        flags=patch.object(settings,'features',FeatureFlags(product_knowledge=True,story_analysis=True,story_management=True,scenario_generation=True,test_generation=True));flags.start();self.addCleanup(flags.stop)
        async def summaries(project,ids):return {i:{'story_approval':{'state':'approved' if i=='S2' else 'in_review'},'state':'reviewed' if i=='S2' else 'needs_review'} for i in ids}
        async def case(project,identity):return {'review_required':identity=='TC1','context_ready':True,'context_error':None,'active_version_id':None if identity=='TC1' else 'approved'}
        for target,name,value in [(ProductKnowledge,'analysis_summaries',AsyncMock(side_effect=summaries)),(TestDesignReview,'state',AsyncMock(side_effect=case))]:
            patcher=patch.object(target,name,value);patcher.start();self.addCleanup(patcher.stop)
        self.service=PendingProjectReviews(self.db)

    async def test_all_types_and_real_eligible_reviewer_names_without_writes(self):
        before=deepcopy({name:coll.docs for name,coll in self.db.items()})
        result=await self.service.listing('P1')
        self.assertEqual(result['unavailable_types'],[])
        self.assertEqual({r['type'] for r in result['items']},{'Story','Scenario','Test Case','Knowledge'})
        rows={r['id']:r for r in result['items']}
        self.assertEqual(set(rows),{'S1','SC1','TC1','R1'})
        self.assertEqual(rows['S1']['pending_with'],['Alice'])
        self.assertEqual(rows['SC1']['pending_with'],['Carol'])
        self.assertEqual(rows['TC1']['pending_with'],['Alice','Carol'])
        self.assertEqual(rows['R1']['pending_with'],['Alice'])
        self.assertNotIn('Bob',str(result));self.assertNotIn('FOREIGN',str(result))
        self.assertEqual(before,{name:coll.docs for name,coll in self.db.items()})
        settings.features.test_design_admin_review=True
        self.assertEqual(next(r for r in (await self.service.listing('P1'))['items'] if r['id']=='TC1')['pending_with'],['Alice'])

    async def test_refresh_removes_approved_items_and_type_failure_preserves_other_rows(self):
        self.db['scenarios'].docs[0]['approved']=True
        with patch.object(TestDesignReview,'state',new=AsyncMock(side_effect=RuntimeError('private database detail'))):
            result=await self.service.listing('P1')
        self.assertNotIn('SC1',[r['id'] for r in result['items']])
        self.assertIn('S1',[r['id'] for r in result['items']])
        self.assertEqual(result['unavailable_types'],['Test Cases'])
        self.assertNotIn('private database detail',str(result))

    async def test_pagination_and_flag_gates(self):
        first=await self.service.listing('P1',0,1)
        self.assertTrue(first['has_more'])
        second=await self.service.listing('P1',1,1)
        self.assertNotIn('S1',[r['id'] for r in second['items']])
        settings.features.product_knowledge=False;settings.features.test_generation=False;settings.features.scenario_generation=False
        self.assertEqual((await self.service.listing('P1'))['items'],[])

    async def test_original_manual_story_approval_removes_queue_row(self):
        from app.services.manual_story_review import ManualStoryReview
        from app.models.product_knowledge import ManualStoryApproval
        database={name:PageCollection() for name in [*self.db,'story_analyses','product_knowledge_sources']}
        database['projects'].docs=[{'project_id':'P1','account_id':'ACC1'}]
        database['stories'].docs=[{'project_id':'P1','story_id':'S1','title':'Review me','description':'Users save drafts.','acceptance_criteria':'Draft is saved.','out_of_scope':None}]
        queue=PendingProjectReviews(database)
        with patch.object(ProductKnowledge,'analysis_summaries',REAL_SUMMARIES):
            initial=await queue.listing('P1')
            self.assertEqual([r['id'] for r in initial['items']],['S1'])
            service=ManualStoryReview(database);ready=await service.readiness('P1','S1')
            await service.approve('P1','S1',{'_id':'Alice','name':'Alice'},'ADMIN',ManualStoryApproval(snapshot_digest=ready['snapshot_digest'],confirmed=True))
            result=await queue.listing('P1')
            self.assertEqual(result['items'],[]);self.assertEqual(result['unavailable_types'],[])

    async def test_endpoint_requires_project_membership_and_private_responses(self):
        from app.routes import project_routes as routes
        async def member(project,user):
            if project!='P1':raise HTTPException(404)
            return self.db['projects'].docs[0],{'role':'TESTER'}
        app=FastAPI();app.include_router(routes.router);app.dependency_overrides[routes.get_current_user]=lambda:{'email':'carol@example.test'}
        with patch.object(routes,'db',self.db),patch.object(routes,'require_project_member',member):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
                response=await client.get('/projects/P1/pending-reviews')
                self.assertEqual(response.status_code,200,response.text)
                self.assertEqual(response.headers['cache-control'],'private, no-store')
                self.assertEqual((await client.get('/projects/P2/pending-reviews')).status_code,404)
                self.assertEqual((await client.get('/projects/P1/pending-reviews?limit=100')).status_code,422)
