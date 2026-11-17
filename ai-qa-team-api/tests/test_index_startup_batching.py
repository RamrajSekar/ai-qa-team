"""Startup still verifies indexes and propagates failures; no real DB connection."""
import asyncio
import unittest
from collections import defaultdict
from unittest.mock import patch
import test_product_knowledge as fixtures
from app.db import init_indexes as module


class IndexStartupTests(unittest.IsolatedAsyncioTestCase):
    async def run_indexes(self, fail=False):
        state={"active":0,"peak":0,"finished":0,"calls":{}}
        class Collection:
            def __init__(self,name):self.name=name
            async def create_indexes(self,models):
                state['active']+=1;state['peak']=max(state['peak'],state['active'])
                try:
                    await asyncio.sleep(0)
                    state['calls'][self.name]=[m.document for m in models]
                    if fail and self.name=='projects':raise RuntimeError('index failure')
                finally:state['active']-=1;state['finished']+=1
        class Database(dict):
            def __missing__(self,key):self[key]=Collection(key);return self[key]
        database=Database()
        with patch.object(module,'db',database):
            if fail:
                with self.assertRaisesRegex(RuntimeError,'index failure'):await module.init_indexes()
            else:await module.init_indexes()
        return state

    async def test_batches_same_collection_bounded_concurrency_and_unique_constraints(self):
        with patch.object(fixtures.settings.features,'customer_accounts',True):state=await self.run_indexes()
        self.assertGreater(state['peak'],1);self.assertLessEqual(state['peak'],4)
        self.assertEqual(state['finished'],len(state['calls']))
        self.assertTrue(any(m.get('unique') and dict(m['key'])=={'project_id':1,'email':1} for m in state['calls']['project_memberships']))
        self.assertTrue(any(m.get('unique') and dict(m['key'])=={'email':1} for m in state['calls']['users']))
        for collection,key in [('projects','project_id'),('stories','story_id'),('scenarios','scenario_id'),('testcases','testcase_id'),('executions','execution_id'),('encrypted_secrets','credential_ref')]:
            self.assertTrue(any(m.get('unique') and dict(m['key'])=={key:1} for m in state['calls'][collection]))
        self.assertGreater(len(state['calls']['ai_usage_records']),1)
        for collection,key in [('stories',{'project_id':1}),('scenarios',{'project_id':1,'scenario_id':1}),('testcases',{'project_id':1,'testcase_id':1}),('environments',{'project_id':1})]:
            self.assertTrue(any(dict(m['key'])==key for m in state['calls'][collection]))

    async def test_failure_is_not_swallowed_and_other_started_checks_are_awaited(self):
        state=await self.run_indexes(fail=True)
        self.assertEqual(state['active'],0)
        self.assertEqual(state['finished'],len(state['calls']))

    async def test_optional_account_uniqueness_remains_gated(self):
        with patch.object(fixtures.settings.features,'customer_accounts',False):state=await self.run_indexes()
        self.assertNotIn('users',state['calls'])
