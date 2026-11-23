"""Shared Free policy, including old stored limits; no DB/model calls."""
import unittest
import os
from types import SimpleNamespace
from unittest.mock import patch, AsyncMock, Mock
from copy import deepcopy
from fastapi import HTTPException
with patch.dict(os.environ, {"MONGO_URI":"mongodb://localhost:27017","MONGO_DB":"free_policy_fixture","REDIS_HOST":"localhost","REDIS_PORT":"6399","REDIS_USERNAME":"","REDIS_PASSWORD":"","SESSION_SECRET_KEY":"fixture","JWT_SECRET_KEY":"fixture"}):
    from app.services.testcase_allowances import testcase_allowances, effective_subscription
    from app.models.subscription import Subscription


class FreeTestCaseAllowanceTests(unittest.TestCase):
    @staticmethod
    def old_free():
        return {"plan":"free", "status":"active", "usage":{"testcases_used":7,"testcases_basic_used":7,"managed_ai_credits_used":11,"byok_ai_requests_used":3},
            "limits":{"testcases_limit":0,"testcases_basic_limit":10,"testcases_medium_limit":0,"testcases_advanced_limit":0}}

    def test_old_free_limits_resolve_to_one_shared_ten_without_mutation(self):
        original=self.old_free();before=deepcopy(original)
        result=effective_subscription(original)
        self.assertEqual(result["limits"],dict(testcases_limit=10,testcases_basic_limit=10,testcases_medium_limit=10,testcases_advanced_limit=10))
        self.assertEqual(result["testcase_complexity_policy"],"SHARED_TOTAL")
        self.assertEqual(result["usage"],before["usage"]);self.assertEqual(original,before)

    def test_new_free_defaults_do_not_create_thirty_slots(self):
        subscription=Subscription();subscription.apply_plan_defaults()
        caps=testcase_allowances(subscription.model_dump())
        self.assertEqual(caps["testcases_limit"],10)
        self.assertEqual(set(caps.values()),{10})
        subscription.limits.testcases_limit=0
        self.assertEqual(testcase_allowances(subscription.model_dump())["testcases_limit"],10)

    def test_existing_explicit_total_remains_authoritative(self):
        subscription=self.old_free();subscription["limits"]["testcases_limit"]=4
        self.assertEqual(set(testcase_allowances(subscription).values()),{4})
        subscription["limits"]["testcases_basic_limit"]=0;subscription["limits"]["testcases_limit"]=0
        self.assertEqual(set(testcase_allowances(subscription).values()),{0})

    def test_paid_tier_caps_are_unchanged(self):
        subscription=self.old_free();subscription["plan"]="pro";before=deepcopy(subscription)
        caps=testcase_allowances(subscription)
        self.assertEqual(caps["testcases_limit"],10);self.assertEqual(caps["testcases_medium_limit"],0)
        self.assertEqual(effective_subscription(subscription),before)

    def test_invalid_configurations_fail_closed(self):
        for limits in ({},{"testcases_limit":True},{"testcases_basic_limit":-1},{"testcases_medium_limit":"10"}):
            with self.assertRaises(HTTPException) as error:testcase_allowances({"plan":"free","limits":limits})
            self.assertEqual(error.exception.status_code,503)

    def test_explicit_unlimited_caps_remain_unlimited(self):
        caps=testcase_allowances({"plan":"free","limits":{"testcases_limit":None,"testcases_basic_limit":None}})
        self.assertTrue(all(value is None for value in caps.values()))


class FreeGenerationRouteTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        import httpx
        from fastapi import FastAPI
        from app.routes import testcase_routes as routes
        from app.config import settings, FeatureFlags
        from resource_quota_double import ResourceQuotaDouble
        self.subscription=FreeTestCaseAllowanceTests.old_free()
        self.subscription['billing_scope']='ACCOUNT'
        self.subscription['usage']['testcases_used']=9
        cases=SimpleNamespace(count_documents=AsyncMock(return_value=0),insert_one=AsyncMock())
        scenario={'project_id':'P1','scenario_id':'SC1','approved':True,'created_by':'member@example.test','title':'Save','steps':[]}
        self.generator=Mock(return_value='fixture code')
        self.patches=[patch.object(routes,'db',{'scenarios':SimpleNamespace(find_one=AsyncMock(return_value=scenario)),'testcases':cases}),
            patch.object(routes,'get_subscription',AsyncMock(side_effect=lambda *args:self.subscription)),
            patch.object(routes,'require_project_member',AsyncMock()),patch.object(routes,'get_next_sequence',AsyncMock(return_value='TC1')),
            patch.object(routes,'generate_playwright_test',self.generator),patch.object(routes,'ResourceQuota',ResourceQuotaDouble),
            patch.object(settings,'features',FeatureFlags(test_generation=True))]
        for item in self.patches:item.start()
        app=FastAPI();app.include_router(routes.router)
        app.dependency_overrides[routes.get_current_user]=lambda:{'_id':'member','email':'member@example.test'}
        self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://fixture')

    async def asyncTearDown(self):
        await self.client.aclose()
        for item in reversed(self.patches):item.stop()

    async def test_old_free_record_allows_each_complexity_only_up_to_shared_remaining(self):
        for tier in ('basic','medium','advanced'):
            response=await self.client.post(f'/testcases/generate?scenario_id=SC1&project_id=P1&count=2&complexity={tier}')
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual(len(response.json()),1)
            self.assertEqual(response.json()[0]['complexity'],tier)

    async def test_exhausted_total_blocks_all_complexities_before_generation(self):
        self.subscription['usage']['testcases_used']=10
        for tier in ('basic','medium','advanced'):
            response=await self.client.post(f'/testcases/generate?scenario_id=SC1&project_id=P1&count=1&complexity={tier}')
            self.assertEqual(response.status_code,403,response.text)
        self.generator.assert_not_called()
