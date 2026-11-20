import unittest
from unittest.mock import MagicMock, AsyncMock
from app.services.account_billing import scenario_complexity_usage


class ScenarioUsageTests(unittest.IsolatedAsyncioTestCase):
    async def test_account_scoped_read_only_breakdown(self):
        collection = MagicMock()
        collection.aggregate.return_value.to_list = AsyncMock(return_value=[
            {"_id": "basic", "count": 3}, {"_id": "advanced", "count": 2},
            {"_id": "unspecified", "count": 1}])
        database = {"projects": collection}
        result = await scenario_complexity_usage(database, "ACC_one")
        self.assertEqual(result, {"scenarios_basic_used": 3, "scenarios_medium_used": 0,
                                  "scenarios_advanced_used": 2, "scenarios_unspecified_used": 1})
        pipeline = collection.aggregate.call_args.args[0]
        self.assertEqual(pipeline[0], {"$match": {"account_id": "ACC_one"}})
        lookup = pipeline[1]["$lookup"]
        self.assertEqual(lookup["pipeline"][0], {"$match": {"$expr": {"$eq": ["$project_id", "$$project"]}}})
        self.assertEqual(lookup["pipeline"][1]["$group"]["_id"]["$cond"][2], "unspecified")
        collection.update_one.assert_not_called()
        collection.aggregate.return_value.to_list.assert_awaited_once_with(4)

    async def test_empty_account_returns_zero_counts(self):
        collection = MagicMock()
        collection.aggregate.return_value.to_list = AsyncMock(return_value=[])
        result = await scenario_complexity_usage({"projects": collection}, "ACC_empty")
        self.assertEqual(list(result.values()), [0, 0, 0, 0])
