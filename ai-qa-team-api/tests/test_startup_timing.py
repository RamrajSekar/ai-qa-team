import unittest
from unittest.mock import patch

from app.utils.startup_timing import startup_timing


class StartupTimingTests(unittest.TestCase):
    def test_records_stage_and_elapsed_without_connection_details(self):
        with patch("app.utils.startup_timing.perf_counter", side_effect=[1, 1.25]), patch("app.utils.startup_timing.logger") as log:
            with startup_timing("mongo_indexes"):
                pass
        self.assertEqual(log.info.call_args.args[1:], ("mongo_indexes", 250, "completed"))

    def test_failure_is_preserved_and_message_not_logged(self):
        with patch("app.utils.startup_timing.logger") as log:
            with self.assertRaisesRegex(RuntimeError, "private-canary"):
                with startup_timing("redis_probe"):
                    raise RuntimeError("private-canary")
        self.assertNotIn("private-canary", str(log.info.call_args))
        self.assertEqual(log.info.call_args.args[-1], "failed")

    def test_rejects_arbitrary_labels(self):
        with self.assertRaises(ValueError):
            with startup_timing("private-canary"):
                pass
