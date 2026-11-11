import os
from datetime import datetime, timezone
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

TEST_ENV = {
    "MONGO_URI": "mongodb://localhost:27017", "MONGO_DB": "playwright_discovery_tests",
    "REDIS_HOST": "localhost", "REDIS_PORT": "6379", "REDIS_USERNAME": "test",
    "REDIS_PASSWORD": "test-only", "SESSION_SECRET_KEY": "session-test-only",
    "JWT_SECRET_KEY": "jwt-test-only", "OPENAI_API_KEY": "",
}

with patch.dict(os.environ, TEST_ENV):
    from app.services.playwright_discovery_service import PLAYWRIGHT_SCANNER_VERSION, discover_playwright_tests
    from app.services.repository_discovery_service import content_commit_sha, scan_path
    from app.services.test_registry_service import build_test_contract

FIXTURE = Path(__file__).parent / "fixtures" / "playwright_structure"


class PlaywrightDiscoveryTests(unittest.TestCase):
    def test_discovers_typescript_and_nested_javascript_but_not_arbitrary_test_file(self):
        tests = discover_playwright_tests(FIXTURE)
        identities = {(item["relative_file_path"], item["test_name"]) for item in tests}
        self.assertEqual(identities, {
            ("tests/basic.spec.ts", "basic structure"),
            ("tests/nested.test.js", "nested javascript"),
        })
        nested_identities = {item["test_identity"] for item in tests if item["test_name"] == "nested javascript"}
        self.assertEqual(nested_identities, {
            "nested group > nested javascript", "second group > nested javascript",
        })

    def test_ordered_calls_preserve_arguments_and_resolution_statuses(self):
        test = next(item for item in discover_playwright_tests(FIXTURE) if item["test_name"] == "basic structure")
        steps = test["steps"]
        self.assertEqual([step["sequence"] for step in steps], list(range(1, len(steps) + 1)))
        by_name = {step["name"]: step for step in steps if step["name"] != "importedHelper"}
        imported = next(step for step in steps if step["name"] == "importedHelper" and len(step["arguments"]) == 3)
        self.assertEqual(by_name["localHelper"]["arguments"], ["'literal value'"])
        self.assertEqual(imported["arguments"], ["variableValue", "process.env.TEST_USER", "`${month}-${year}`"])
        self.assertEqual(by_name["localHelper"]["resolution_status"], "RESOLVED")
        self.assertEqual(imported["resolution_status"], "RESOLVED")
        self.assertEqual(by_name["duplicateHelper"]["resolution_status"], "AMBIGUOUS")
        self.assertEqual(by_name["examplePage.open"]["resolution_status"], "RESOLVED")
        self.assertEqual(by_name["page.goto"]["resolution_status"], "EXTERNAL_LIBRARY")
        self.assertEqual(by_name["expect(page.locator('.result')).toBeVisible"]["resolution_status"], "EXTERNAL_LIBRARY")
        self.assertEqual(by_name["unknownHelper"]["resolution_status"], "UNRESOLVED")
        self.assertEqual(by_name["handlers[methodName]"]["resolution_status"], "DYNAMIC")

    def test_imports_definitions_nested_calls_and_cycles_are_structural(self):
        test = next(item for item in discover_playwright_tests(FIXTURE) if item["test_name"] == "basic structure")
        imports = {(item["raw_path"], item["resolution_status"], item["resolved_path"]) for item in test["source_imports"]}
        self.assertIn(("@playwright/test", "EXTERNAL_LIBRARY", None), imports)
        self.assertIn(("../helpers/actions", "RESOLVED", "helpers/actions.ts"), imports)
        self.assertIn(("../../../../outside", "OUTSIDE_REPOSITORY", None), imports)
        definitions = {item["name"]: item for item in test["callable_references"]}
        self.assertIn("localHelper", definitions)
        self.assertIn("importedHelper", definitions)
        self.assertIn("ExamplePage.open", definitions)
        self.assertIn("recursiveHelper", definitions)
        self.assertIn("cycleA", definitions)
        self.assertIn("cycleB", definitions)
        self.assertEqual(definitions["localHelper"]["declared_parameters"], ["value: string"])
        recursive = definitions["recursiveHelper"]
        self.assertEqual(recursive["nested_calls"][0]["callable_reference"], recursive["callable_reference"])
        page_object = definitions["ExamplePage.open"]
        self.assertTrue(page_object["nested_calls"][0]["callable_reference"].endswith("method:ExamplePage.navigate"))
        self.assertLessEqual(len(definitions), 8)

    def test_contract_mapping_keeps_semantic_fields_empty(self):
        scanned = next(item for item in discover_playwright_tests(FIXTURE) if item["test_name"] == "basic structure")
        contract = build_test_contract(
            {"repository_id": "REP001", "project_id": "PRJ001"}, "a" * 40,
            scanned, datetime.now(timezone.utc),
        )
        self.assertEqual(contract["framework"], "playwright")
        self.assertEqual(contract["scanner_version"], PLAYWRIGHT_SCANNER_VERSION)
        self.assertTrue(contract["source_imports"])
        self.assertTrue(contract["callable_references"])
        self.assertEqual(contract["resource_imports"], [])
        self.assertEqual(contract["keyword_references"], [])
        for field in ("inputs", "runtime_dependencies", "capabilities", "assertions"):
            self.assertEqual(contract[field], [])
        self.assertIsNone(contract["confidence"])

    def test_combined_scanner_detects_playwright_and_content_revision_tracks_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "example.spec.ts"
            source.write_text("import { test } from '@playwright/test'; test('one', async () => {});", encoding="utf-8")
            first = content_commit_sha(root)
            commit, tests, framework = scan_path(root, first)
            self.assertEqual((commit, framework), (first, "playwright"))
            self.assertEqual([item["test_name"] for item in tests], ["one"])
            first_contract = build_test_contract(
                {"repository_id": "REP001", "project_id": "PRJ001"}, first,
                tests[0], datetime.now(timezone.utc),
            )
            source.write_text("import { test } from '@playwright/test'; test('one', async () => { /* revision two */ });", encoding="utf-8")
            second = content_commit_sha(root)
            self.assertNotEqual(first, second)
            _, second_tests, _ = scan_path(root, second)
            second_contract = build_test_contract(
                {"repository_id": "REP001", "project_id": "PRJ001"}, second,
                second_tests[0], datetime.now(timezone.utc),
            )
            self.assertNotEqual(first_contract["test_id"], second_contract["test_id"])


if __name__ == "__main__":
    unittest.main()
