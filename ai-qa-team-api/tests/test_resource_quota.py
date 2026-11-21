"""Pure contract checks; real transaction coverage lives in opt-in local verifier."""
import os
import unittest
from unittest.mock import patch, AsyncMock
from fastapi import HTTPException
with patch.dict(os.environ, {"MONGO_URI":"mongodb://127.0.0.1:27129","MONGO_DB":"qa_quota_contracts","REDIS_HOST":"127.0.0.1","REDIS_PORT":"6399","REDIS_USERNAME":"","REDIS_PASSWORD":"","JWT_SECRET_KEY":"fixture-only","SESSION_SECRET_KEY":"fixture-only"}):
    from app.services.resource_quota import ResourceQuota


class ResourceQuotaContracts(unittest.IsolatedAsyncioTestCase):
    async def test_transactionless_backend_fails_closed_before_work(self):
        quota=ResourceQuota({"resource_quota_reservations":object()});work=AsyncMock()
        with self.assertRaises(HTTPException) as error:await quota.transaction(work)
        self.assertEqual(error.exception.status_code,503);work.assert_not_called()

    async def test_invalid_admissions_never_resolve_a_billing_target(self):
        quota=ResourceQuota({"resource_quota_reservations":object()})
        with patch.object(quota,'target',new=AsyncMock()) as target:
            for kind,count,tier in [('other',1,'basic'),('scenarios',0,'basic'),('testcases',21,'basic'),('testcases',True,'basic'),('scenarios',1,'custom')]:
                with self.assertRaises(HTTPException) as error:await quota.reserve({},'P1',kind,count,tier)
                self.assertEqual(error.exception.status_code,422)
            target.assert_not_called()

    def test_unlimited_and_legacy_aggregate_defaults_are_preserved(self):
        self.assertEqual(ResourceQuota.limits({'limits':{'testcases_limit':0,'testcases_basic_limit':10,'testcases_medium_limit':0,'testcases_advanced_limit':0}},'testcases','basic'),{'testcases_used':10,'testcases_basic_used':10})
        self.assertEqual(ResourceQuota.limits({'limits':{'scenarios_limit':None}},'scenarios','basic'),{'scenarios_used':None})
        self.assertEqual(ResourceQuota.limits({'limits':{'testcases_limit':None,'testcases_basic_limit':None}},'testcases','basic'),{'testcases_used':None,'testcases_basic_used':None})

    def test_invalid_or_missing_allowance_fails_closed(self):
        for limits,kind in [({},'scenarios'),({},'testcases'),({'scenarios_limit':True},'scenarios'),({'testcases_limit':0,'testcases_basic_limit':'10'},'testcases')]:
            with self.assertRaises(HTTPException) as error:ResourceQuota.limits({'limits':limits},kind,'basic')
            self.assertEqual(error.exception.status_code,503)
