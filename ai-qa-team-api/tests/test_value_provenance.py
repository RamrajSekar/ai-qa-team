import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
TEST_ENV = {"MONGO_URI": "mongodb://localhost:27017", "MONGO_DB": "provenance_tests", "REDIS_HOST": "localhost", "REDIS_PORT": "6379", "REDIS_USERNAME": "test", "REDIS_PASSWORD": "test-only", "SESSION_SECRET_KEY": "session-test-only", "JWT_SECRET_KEY": "jwt-test-only", "OPENAI_API_KEY": ""}
with patch.dict(os.environ, TEST_ENV):
    from app.services.playwright_discovery_service import discover_playwright_tests
    from app.services.repository_discovery_service import discover_robot_tests
    from app.services.selenium_java_discovery_service import discover_selenium_java_tests
    from app.services.value_provenance_service import MAX_PROVENANCE_NODES, build_value_provenance

FIXTURES = Path(__file__).parent / "fixtures"


class ValueProvenanceTests(unittest.TestCase):
    def contracts(self):
        return {
            "robot": discover_robot_tests(FIXTURES / "robot_structure")[0],
            "playwright": next(item for item in discover_playwright_tests(FIXTURES / "playwright_structure") if item["test_name"] == "basic structure"),
            "selenium_java": next(item for item in discover_selenium_java_tests(FIXTURES / "selenium_java") if item["test_name"] == "legacyFlow"),
        }

    def test_all_frameworks_emit_same_canonical_provenance_shape(self):
        required = {"provenance_id", "expression", "evidence_kind", "source_file", "resolution_status", "source_ids"}
        for framework, contract in self.contracts().items():
            with self.subTest(framework=framework):
                self.assertTrue(contract["value_provenance"])
                self.assertTrue(all(required.issubset(item) for item in contract["value_provenance"]))
                self.assertTrue(any(item["evidence_kind"] == "ARGUMENT" for item in contract["value_provenance"]))
                self.assertTrue(any(item["evidence_kind"] == "PARAMETER" for item in contract["value_provenance"]))

    def test_structural_origin_kinds_are_cross_framework(self):
        kinds = {name: {item["evidence_kind"] for item in contract["value_provenance"]} for name, contract in self.contracts().items()}
        self.assertTrue({"LITERAL", "CALL_RESULT", "ENV_ACCESS_EXPRESSION"}.issubset(kinds["robot"]))
        for framework in ("playwright", "selenium_java"):
            self.assertTrue({"LITERAL", "VARIABLE_REFERENCE", "CALL_RESULT", "MEMBER_REFERENCE", "ENV_ACCESS_EXPRESSION"}.issubset(kinds[framework]))

    def test_latest_assignment_and_branch_ambiguity_are_preserved(self):
        for framework, variable in (("playwright", "latest"), ("selenium_java", "code")):
            records = self.contracts()[framework]["value_provenance"]
            matches = [item for item in records if item["expression"] == variable]
            self.assertTrue(any(item["resolution_status"] == "RESOLVED" for item in matches))
            self.assertTrue(any(item["resolution_status"] == "AMBIGUOUS" for item in matches))

    def test_recursion_is_cycle_safe_and_node_limit_is_partial(self):
        calls = [{"name": "repeat", "arguments": ["value"], "source_file": "test", "line_number": index, "callable_reference": "repeat", "keyword_reference": None} for index in range(MAX_PROVENANCE_NODES)]
        definitions = [{"callable_reference": "repeat", "name": "repeat", "source_file": "test", "line_number": 1, "declared_parameters": ["value"], "nested_calls": calls[:1]}]
        result = build_value_provenance("bounded", calls, definitions)
        self.assertLessEqual(len(result), MAX_PROVENANCE_NODES)
        self.assertTrue(any(item["evidence_kind"] == "TRAVERSAL_LIMIT" and item["resolution_status"] == "PARTIAL" for item in result))

        binding_cycle = build_value_provenance(
            "binding-cycle",
            [{"name": "use", "arguments": ["value"], "source_file": "test", "line_number": 2}],
            [],
            [{"scope": "binding-cycle", "name": "value", "expression": "value", "source_file": "test",
              "line_number": 1, "evidence_kind": "ASSIGNMENT"}],
        )
        self.assertTrue(any(item["evidence_kind"] == "TRAVERSAL_LIMIT" for item in binding_cycle))

    def test_no_ownership_classification_is_created(self):
        forbidden = {"EXTERNAL_INPUT", "INTERNALLY_GENERATED", "GENERATED_RUNTIME", "CREDENTIAL", "SECRET"}
        for contract in self.contracts().values():
            self.assertTrue(forbidden.isdisjoint({item["evidence_kind"] for item in contract["value_provenance"]}))


if __name__ == "__main__":
    unittest.main()
