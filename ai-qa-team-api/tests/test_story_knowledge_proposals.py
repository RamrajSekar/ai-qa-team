"""Approved story copies, canonical review/approval and no-AI regressions."""
import asyncio
import unittest
from copy import deepcopy
from fastapi import HTTPException
import test_product_knowledge as fixtures
import test_requirement_contexts as context_fixtures
from app.models.knowledge_training import StoryKnowledgeProposal,TrainingReview,TrainingSave
from app.models.product_knowledge import ManualStoryApproval,KnowledgeDraft,KnowledgeSourceInput
from app.services.story_knowledge_proposals import StoryKnowledgeProposals
from app.services.knowledge_training import KnowledgeTraining
from app.services.manual_story_review import ManualStoryReview

class StoryProposalTests(unittest.IsolatedAsyncioTestCase):
    approved=fixtures.KnowledgeTests.approved
    async def asyncSetUp(self):
        await context_fixtures.RequirementTests.asyncSetUp(self)
        self.db['knowledge_training_reviews']=context_fixtures.MongoCollection()
        self.proposals=StoryKnowledgeProposals(self.db)
        self.training=KnowledgeTraining(self.db,self.service)

    async def start(self,update=False):
        return await self.proposals.start('P1','ST1','member',StoryKnowledgeProposal(change_type='update' if update else 'add',claim_id='K1' if update else None,base_version_id=self.version['version_id'] if update else None))

    async def save(self,row):
        reviewed=await self.training.review('P1',row['review_id'],TrainingReview(expected_revision=row['revision'],proposals=[{'claim':p['claim'],'decision':'confirmed'} for p in row['proposals']]))
        return await self.training.save('P1','reviewer',row['review_id'],TrainingSave(expected_revision=reviewed['revision']))

    async def test_add_copies_without_ai_and_reopens_same_review_even_concurrently(self):
        before=deepcopy(await self.service.active('P1'))
        first,second=await asyncio.gather(self.start(),self.start())
        self.assertEqual(first['review_id'],second['review_id'])
        self.assertEqual(first['extraction_state'],'completed');self.assertEqual(first['clarification_questions'],[])
        self.assertTrue(all(p['decision']=='pending' for p in first['proposals']))
        self.assertEqual(first['proposals'][0]['claim']['statement'],'Show Draft saved.')
        self.assertEqual(len(self.db['knowledge_training_reviews'].docs),1)
        self.assertEqual(sum(s.get('origin',{}).get('approved_story_copy',False) for s in self.db['product_knowledge_sources'].docs),1)
        self.assertEqual(await self.service.active('P1'),before)
        saved=await self.save(first)
        self.assertEqual(await self.service.active('P1'),before)
        approved=await self.service.approve('P1','admin',saved['saved_version']['version_id'])
        self.assertTrue(any(c['claim_id']=='K1' for c in approved['claims']))
        eligible,excluded=await self.service.analysis_knowledge('P1','ST1',approved)
        self.assertEqual([c['claim_id'] for c in eligible['claims']],['K1']);self.assertTrue(excluded)
        again=await self.start();self.assertEqual(again['saved_version']['status'],'approved')
        self.usage.execute.assert_not_called()

    async def test_update_targets_one_rule_and_retains_unaffected_knowledge(self):
        extra={**self.claim,'claim_id':'K2','statement':'Keep unrelated behavior.'}
        draft=await self.service.create_version('P1','reviewer',KnowledgeDraft(title='More knowledge',claims=[extra]))
        self.version=await self.service.approve('P1','reviewer',draft['version_id'])
        row=await self.start(update=True)
        self.assertEqual(row['mode'],'correction');self.assertEqual([p['claim']['claim_id'] for p in row['proposals']],['K1'])
        self.assertEqual(row['removed_claim_ids'],[])
        saved=await self.save(row)
        self.assertEqual(saved['saved_version']['status'],'draft')
        result=await self.service.approve('P1','admin',saved['saved_version']['version_id'])
        self.assertEqual(next(c for c in result['claims'] if c['claim_id']=='K2')['statement'],'Keep unrelated behavior.')
        self.assertTrue(next(c for c in result['claims'] if c['claim_id']=='K1')['source_id']!=self.claim['source_id'])
        self.usage.execute.assert_not_called()

    async def test_manual_approval_without_analysis_supports_add(self):
        self.db['story_analyses'].docs.clear()
        service=ManualStoryReview(self.db);ready=await service.readiness('P1','ST1')
        await service.approve('P1','ST1',{'_id':'admin','name':'Alice'},'ADMIN',ManualStoryApproval(snapshot_digest=ready['snapshot_digest'],confirmed=True))
        row=await self.start();self.assertTrue(row['proposals'])
        self.assertEqual(self.db['story_analyses'].docs,[])
        self.usage.execute.assert_not_called()

    async def test_changed_source_blocks_save_and_direct_approval(self):
        row=await self.start();saved=await self.save(row)
        self.db['stories'].docs[0]['description']='Different requirements'
        with self.assertRaises(HTTPException):await self.service.approve('P1','admin',saved['saved_version']['version_id'])
        self.assertEqual((await self.service.active('P1'))['version_id'],self.version['version_id'])
        with self.assertRaises(HTTPException):await self.start()

    async def test_new_version_review_preserves_old_source_history_on_unrelated_changes(self):
        row=await self.start();saved=await self.save(row)
        first=await self.service.approve('P1','admin',saved['saved_version']['version_id'])
        self.db['stories'].docs[0]['description']='Later story change'
        # Previously approved sources remain valid history, not a new proposal.
        self.assertEqual((await self.service.approve('P1','admin',first['version_id']))['version_id'],first['version_id'])
        guide=await self.service.add_source('P1','reviewer',KnowledgeSourceInput(title='Independent guide',kind='document',text='Independent rule.'))
        claim={**self.claim,'claim_id':'K3','statement':'Independent rule.','source_id':guide['source_id'],'quote':'Independent rule.'}
        successor=await self.service.create_version('P1','reviewer',KnowledgeDraft(title='Independent addition',parent_version_id=first['version_id'],claims=[claim]))
        self.assertEqual((await self.service.approve('P1','admin',successor['version_id']))['status'],'approved')

    async def test_changed_story_before_save_and_unapproved_story_cannot_publish(self):
        row=await self.start()
        self.db['stories'].docs[0]['description']='Changed before review'
        with self.assertRaises(HTTPException):await self.save(row)
        self.assertEqual((await self.service.active('P1'))['version_id'],self.version['version_id'])
        self.db['story_analyses'].docs.clear()
        with self.assertRaises(HTTPException):await self.start()
        self.usage.execute.assert_not_called()

    async def test_long_addition_keeps_literal_excerpts_without_silent_truncation(self):
        from app.services.approved_visual_run import digest
        text=('Approved requirement text with exact punctuation. '*60).strip()
        self.db['stories'].docs[0]['acceptance_criteria']=text
        raw=self.db['story_analyses'].docs[-1]
        raw['story_digest']=digest(await self.service.story('P1','ST1'))
        row=await self.start()
        self.assertGreater(len(row['proposals']),1)
        self.assertEqual(' '.join(p['claim']['statement'] for p in row['proposals']),text)
        source=await self.service.record('product_knowledge_sources','P1',row['source_id'])
        self.assertTrue(all(p['claim']['quote'] in source['text'] for p in row['proposals']))
        with self.assertRaises(HTTPException):await self.start(update=True)
        self.usage.execute.assert_not_called()

    async def test_http_permissions_validation_and_no_remove_action(self):
        path=self.base+'/stories/ST1/knowledge-proposals'
        self.user['role']='MEMBER'
        response=await self.client.post(path,json={'change_type':'add'});self.assertEqual(response.status_code,200,response.text)
        self.assertEqual((await self.client.post(path,json={'change_type':'remove','claim_id':'K1'})).status_code,422)
        self.assertEqual((await self.client.post(path,json={'change_type':'add','approved_by':'FORGED'})).status_code,422)
        self.assertEqual((await self.client.post(path.replace('P1','P2'),json={'change_type':'add'})).status_code,404)
        self.assertEqual((await self.client.post(path,json={'change_type':'update','claim_id':'K_missing','base_version_id':self.version['version_id']})).status_code,409)
        saved=await self.save(response.json())
        approve=self.base+'/versions/'+saved['saved_version']['version_id']+'/approve'
        self.assertEqual((await self.client.post(approve,json={})).status_code,403)
        self.user['role']='ADMIN';self.assertEqual((await self.client.post(approve,json={})).status_code,200)
        self.usage.execute.assert_not_called()
