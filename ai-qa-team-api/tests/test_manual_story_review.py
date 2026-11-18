"""Manual authority tests; isolated database/auth/AI doubles only."""
import asyncio
import unittest
from copy import deepcopy
from fastapi import HTTPException
from app.models.product_knowledge import ManualStoryApproval
from app.services.manual_story_review import ManualStoryReview
from app.services.approved_story_context import ApprovedStoryContext
from app.services.approved_visual_run import digest
from test_requirement_contexts import RequirementTests
import test_product_knowledge as fixtures

class ManualStoryTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp=RequirementTests.asyncSetUp
    approved=fixtures.KnowledgeTests.approved

    async def approve_manual(self,actor=None,note='Reviewed manually'):
        service=ManualStoryReview(self.db)
        ready=await service.readiness('P1','ST1')
        result=await service.approve('P1','ST1',actor or {**self.user,'name':'Alice'},'ADMIN',ManualStoryApproval(snapshot_digest=ready['snapshot_digest'],confirmed=True,note=note))
        return service,result

    async def test_no_analysis_approval_is_immutable_and_generates_story_only(self):
        self.db['story_analyses'].docs.clear()
        knowledge_before=deepcopy(self.db['product_knowledge_versions'].docs)
        service,receipt=await self.approve_manual()
        self.assertEqual(receipt['basis'],'manual_review');self.assertEqual(receipt['approved_by_name'],'Alice')
        self.assertEqual(receipt['approved_by_role'],'ADMIN');self.assertTrue(receipt['approved_at'])
        self.assertEqual(self.db['story_analyses'].docs,[])
        self.assertEqual(self.db['product_knowledge_versions'].docs,knowledge_before)
        self.assertIsNone(await self.service.latest_analysis('P1','ST1'))
        summary=(await self.service.analysis_summaries('P1',['ST1']))['ST1']
        self.assertEqual(summary['story_approval']['basis'],'manual_review');self.assertEqual(summary['state'],'not_analyzed')
        context=await ApprovedStoryContext(self.db).prepare('P1','ST1')
        self.assertEqual(context['design_basis'],'approved_story_only')
        self.assertEqual(context['knowledge']['claims'],[]);self.assertIsNone(context['knowledge']['version_id'])
        self.assertIsNone(context['analysis']['analysis_id']);self.assertFalse(context['independent_knowledge_validation'])
        self.usage.execute.assert_not_called()
        self.db['stories'].docs[0]['description']='Changed story'
        self.assertIsNone((await service.readiness('P1','ST1'))['approval'])
        with self.assertRaises(HTTPException):await ApprovedStoryContext(self.db).resolve('P1','ST1',context['requirements_context_id'])

    async def test_repeated_and_concurrent_approvals_preserve_first_reviewer(self):
        service=ManualStoryReview(self.db);ready=await service.readiness('P1','ST1')
        payload=ManualStoryApproval(snapshot_digest=ready['snapshot_digest'],confirmed=True)
        results=await asyncio.gather(*(service.approve('P1','ST1',{'_id':name,'name':name},'ADMIN',payload) for name in ['Alice','Bob']))
        self.assertEqual(results[0]['approved_by'],results[1]['approved_by'])
        again=await service.approve('P1','ST1',{'_id':'Other','name':'Other'},'ADMIN',payload)
        self.assertEqual(again['approved_by'],results[0]['approved_by'])
        self.assertEqual(sum(row.get('record_type')=='manual_story_approval' for row in self.db['requirement_contexts'].docs),1)

    async def test_old_snapshot_and_unresolved_historical_blockers_cannot_be_skipped(self):
        service=ManualStoryReview(self.db);ready=await service.readiness('P1','ST1')
        self.db['stories'].docs[0]['description']='Edited'
        with self.assertRaises(HTTPException):await service.approve('P1','ST1',self.user,'ADMIN',ManualStoryApproval(snapshot_digest=ready['snapshot_digest'],confirmed=True))
        story=await self.service.story('P1','ST1')
        self.db['story_analyses'].docs.extend([
          {'_id':'old','project_id':'P1','story_id':'ST1','story_digest':digest(story),'status':'needs_review','created_at':'2000','findings':[{'finding_id':'B1','category':'knowledge_conflict','severity':'blocker'}]},
          {'_id':'new','project_id':'P1','story_id':'ST1','story_digest':digest(story),'status':'reviewed','created_at':'3000','findings':[]}])
        ready=await service.readiness('P1','ST1');self.assertTrue(ready['blocked'])
        with self.assertRaises(HTTPException):await service.approve('P1','ST1',self.user,'ADMIN',ManualStoryApproval(snapshot_digest=ready['snapshot_digest'],confirmed=True))

    async def test_admin_project_and_integrity_guards(self):
        service,receipt=await self.approve_manual()
        ready=await service.readiness('P1','ST1');payload=ManualStoryApproval(snapshot_digest=ready['snapshot_digest'],confirmed=True)
        with self.assertRaises(HTTPException):await service.approve('P1','ST1',self.user,'TESTER',payload)
        with self.assertRaises(HTTPException):await service.readiness('P2','ST1')
        row=next(r for r in self.db['requirement_contexts'].docs if r.get('record_type')=='manual_story_approval')
        row['approved_by']='Forged'
        with self.assertRaises(HTTPException):await service.readiness('P1','ST1')

    async def test_http_requires_admin_confirmation_and_rejects_forged_identity(self):
        from app.routes import product_knowledge_routes as routes
        from unittest.mock import patch
        async def member(project,user):
            if project!='P1':raise HTTPException(404)
            return {},{'role':user['role']}
        async def admin(project,user):
            result=await member(project,user)
            if user['role']!='ADMIN':raise HTTPException(403)
            return result
        with patch.object(routes,'require_project_member',member),patch.object(routes,'require_project_admin',admin):
            path=self.base+'/stories/ST1/manual-approval'
            ready=(await self.client.get(path)).json()
            body={'snapshot_digest':ready['snapshot_digest'],'confirmed':True}
            self.user['role']='TESTER';self.assertEqual((await self.client.post(path,json=body)).status_code,403)
            self.user['role']='ADMIN'
            self.assertEqual((await self.client.post(path,json={**body,'confirmed':False})).status_code,422)
            self.assertEqual((await self.client.post(path,json={**body,'approved_by':'FORGED'})).status_code,422)
            self.assertEqual((await self.client.post(path,json=body)).status_code,200)
            self.assertEqual((await self.client.get(path)).json()['approval']['basis'],'manual_review')
            self.assertEqual((await self.client.get(path.replace('P1','P2'))).status_code,404)
