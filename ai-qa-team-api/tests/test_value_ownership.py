import os
from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
TEST_ENV = {"MONGO_URI": "mongodb://localhost:27017", "MONGO_DB": "ownership_tests", "REDIS_HOST": "localhost", "REDIS_PORT": "6379", "REDIS_USERNAME": "test", "REDIS_PASSWORD": "test-only", "SESSION_SECRET_KEY": "session-test-only", "JWT_SECRET_KEY": "jwt-test-only", "OPENAI_API_KEY": ""}
with patch.dict(os.environ, TEST_ENV):
    from app.services.playwright_discovery_service import discover_playwright_tests
    from app.services.repository_discovery_service import discover_robot_tests
    from app.services.selenium_java_discovery_service import discover_selenium_java_tests
    from app.services.test_registry_service import build_test_contract
    from app.services.value_ownership_service import build_value_ownership

FIXTURES = Path(__file__).parent / "fixtures"
REPOSITORY = {"repository_id": "REP001", "project_id": "PRJ001"}


def record(record_id, kind, sources=None, status="RESOLVED"):
    return {"provenance_id": record_id, "expression": record_id, "evidence_kind": kind,
            "source_file": "fixture", "line_number": 1, "resolution_status": status,
            "source_ids": sources or [], "callable_reference": None, "parameter_name": None}


class ValueOwnershipTests(unittest.TestCase):
    def contracts(self):
        scanned = {
            "robot": discover_robot_tests(FIXTURES / "robot_structure")[0],
            "playwright": next(item for item in discover_playwright_tests(FIXTURES / "playwright_structure") if item["test_name"] == "basic structure"),
            "selenium_java": next(item for item in discover_selenium_java_tests(FIXTURES / "selenium_java") if item["test_name"] == "legacyFlow"),
        }
        now = datetime.now(timezone.utc)
        return {name: build_test_contract(REPOSITORY, "a" * 40, item, now) for name, item in scanned.items()}

    def test_cross_framework_ownership_is_canonical_and_explainable(self):
        required = {"ownership_id", "provenance_id", "ownership", "status", "evidence_ids", "reason_code", "source_file"}
        for framework, contract in self.contracts().items():
            with self.subTest(framework=framework):
                self.assertTrue(contract["value_ownership"])
                self.assertTrue(all(required.issubset(item) for item in contract["value_ownership"]))
                categories = {item["ownership"] for item in contract["value_ownership"]}
                self.assertTrue({"STATIC_INTERNAL", "GENERATED_RUNTIME", "ENVIRONMENT"}.issubset(categories))
                self.assertTrue(all(item["evidence_ids"] for item in contract["value_ownership"] if item["ownership"] != "UNKNOWN"))

    def test_parameter_flow_preserves_literal_ownership(self):
        for framework, contract in self.contracts().items():
            with self.subTest(framework=framework):
                parameter_ids = {item["provenance_id"] for item in contract["value_provenance"] if item["evidence_kind"] == "PARAMETER"}
                self.assertTrue(any(item["ownership"] == "STATIC_INTERNAL" and parameter_ids.intersection(item["evidence_ids"])
                                    for item in contract["value_ownership"]))

    def test_same_and_conflicting_branch_origins(self):
        same = [record("A", "ARGUMENT", ["V"]), record("V", "VARIABLE_REFERENCE", ["D"], "AMBIGUOUS"),
                record("D", "ASSIGNMENT", ["L1", "L2"], "AMBIGUOUS"), record("L1", "LITERAL"), record("L2", "LITERAL")]
        result = build_value_ownership("same", same)[0]
        self.assertEqual((result["ownership"], result["status"]), ("STATIC_INTERNAL", "AMBIGUOUS"))

        conflict = [record("A", "ARGUMENT", ["V"]), record("V", "VARIABLE_REFERENCE", ["D"], "AMBIGUOUS"),
                    record("D", "ASSIGNMENT", ["L", "E"], "AMBIGUOUS"), record("L", "LITERAL"),
                    record("E", "ENV_ACCESS_EXPRESSION")]
        result = build_value_ownership("conflict", conflict)[0]
        self.assertEqual((result["ownership"], result["status"], result["reason_code"]),
                         ("UNKNOWN", "AMBIGUOUS", "CONFLICTING_OWNERSHIP"))

    def test_unknown_dynamic_limit_and_member_behavior(self):
        cases = [
            ([record("A", "ARGUMENT", ["U"]), record("U", "VARIABLE_REFERENCE", [], "UNRESOLVED")], "UNKNOWN", "UNRESOLVED"),
            ([record("A", "ARGUMENT", ["D"]), record("D", "UNKNOWN_EXPRESSION", [], "DYNAMIC")], "UNKNOWN", "DYNAMIC"),
            ([record("A", "ARGUMENT", ["T"]), record("T", "TRAVERSAL_LIMIT", [], "PARTIAL")], "UNKNOWN", "PARTIAL"),
            ([record("A", "ARGUMENT", ["M"]), record("M", "MEMBER_REFERENCE", ["C"]), record("C", "CALL_RESULT")], "GENERATED_RUNTIME", "PARTIAL"),
        ]
        for index, (graph, ownership, status) in enumerate(cases):
            result = build_value_ownership(str(index), graph)[0]
            self.assertEqual((result["ownership"], result["status"]), (ownership, status))

    def test_environment_names_do_not_create_credentials(self):
        graph = [record("A", "ARGUMENT", ["E"]), record("E", "ENV_ACCESS_EXPRESSION")]
        result = build_value_ownership("password", graph)[0]
        self.assertEqual(result["ownership"], "ENVIRONMENT")
        self.assertNotEqual(result["ownership"], "CREDENTIAL")

    def test_unproven_external_boundary_remains_unknown(self):
        graph = [record("A", "ARGUMENT", ["P"]), record("P", "PARAMETER", [], "UNRESOLVED")]
        result = build_value_ownership("external", graph)[0]
        self.assertEqual(result["ownership"], "UNKNOWN")

    def test_only_argument_nodes_are_classification_targets(self):
        graph = [record("L", "LITERAL"), record("A", "ARGUMENT", ["L"])]
        result = build_value_ownership("targets", graph)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["provenance_id"], "A")

    def test_stable_ids_and_no_semantic_side_effects(self):
        graph = [record("A", "ARGUMENT", ["L"]), record("L", "LITERAL")]
        self.assertEqual(build_value_ownership("stable", graph), build_value_ownership("stable", graph))
        for contract in self.contracts().values():
            self.assertEqual(contract["inputs"], [])
            self.assertEqual(contract["runtime_dependencies"], [])
            self.assertEqual(contract["capabilities"], [])
            self.assertEqual(contract["assertions"], [])
            self.assertIsNone(contract["confidence"])


if __name__ == "__main__":
    unittest.main()
