import os
from datetime import datetime, timezone
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
TEST_ENV = {
    "MONGO_URI": "mongodb://localhost:27017", "MONGO_DB": "selenium_java_tests",
    "REDIS_HOST": "localhost", "REDIS_PORT": "6379", "REDIS_USERNAME": "test",
    "REDIS_PASSWORD": "test-only", "SESSION_SECRET_KEY": "session-test-only",
    "JWT_SECRET_KEY": "jwt-test-only", "OPENAI_API_KEY": "",
}
with patch.dict(os.environ, TEST_ENV):
    from app.services.repository_discovery_service import content_commit_sha, scan_path
    from app.services.repository_discovery_service import discover_robot_tests
    from app.services.playwright_discovery_service import discover_playwright_tests
    from app.services.selenium_java_discovery_service import SELENIUM_JAVA_SCANNER_VERSION, discover_selenium_java_tests
    from app.services.test_registry_service import build_test_contract

FIXTURE = Path(__file__).parent / "fixtures" / "selenium_java"


class SeleniumJavaDiscoveryTests(unittest.TestCase):
    def test_discovers_junit4_junit5_and_testng_but_not_non_selenium(self):
        tests = discover_selenium_java_tests(FIXTURE)
        self.assertEqual({item["test_identity"] for item in tests}, {
            "com.example.tests.JUnit4SeleniumTest.legacyFlow",
            "com.example.tests.JUnit5SeleniumTest.modernFlow",
            "com.example.tests.TestNgSeleniumTest.testNgFlow",
        })
        runners = {item["test_name"]: item["tags"] for item in tests}
        self.assertEqual(runners, {
            "legacyFlow": ["runner:junit4"], "modernFlow": ["runner:junit5"],
            "testNgFlow": ["runner:testng"],
        })

    def test_ordered_calls_preserve_arguments_and_resolution(self):
        test = next(item for item in discover_selenium_java_tests(FIXTURE) if item["test_name"] == "legacyFlow")
        steps = test["steps"]
        self.assertEqual([item["sequence"] for item in steps], list(range(1, len(steps) + 1)))
        by_name = {item["name"]: item for item in steps}
        self.assertEqual(by_name["loginPage.login"]["arguments"], ['"literal"', "code", 'System.getenv("TEST_USER")', "data.getCode()"])
        expected = {
            "loginPage.login": "RESOLVED", "loginPage.navigate": "RESOLVED",
            "driver.get": "EXTERNAL_LIBRARY", "Assert.assertTrue": "EXTERNAL_LIBRARY",
            "TestHelper.overloaded": "AMBIGUOUS", "action.perform": "DYNAMIC",
            "localHelper": "RESOLVED", "unknownMethod": "UNRESOLVED",
        }
        for name, status in expected.items():
            self.assertEqual(by_name[name]["resolution_status"], status)

    def test_imports_page_objects_inheritance_nested_calls_and_cycles(self):
        test = next(item for item in discover_selenium_java_tests(FIXTURE) if item["test_name"] == "legacyFlow")
        imports = {(item["raw_path"], item["resolution_status"], item["resolved_path"]) for item in test["source_imports"]}
        self.assertIn(("com.example.pages.LoginPage", "RESOLVED", "src/test/java/com/example/pages/LoginPage.java"), imports)
        self.assertIn(("org.openqa.selenium.WebDriver", "EXTERNAL_LIBRARY", None), imports)
        definitions = {item["name"]: item for item in test["callable_references"]}
        for name in ("LoginPage.login", "BasePage.navigate", "TestHelper.prepare", "CycleA.first", "CycleB.second", "JUnit4SeleniumTest.recursiveHelper"):
            self.assertIn(name, definitions)
        recursive = definitions["JUnit4SeleniumTest.recursiveHelper"]
        self.assertEqual(recursive["nested_calls"][0]["callable_reference"], recursive["callable_reference"])

    def test_contract_mapping_is_generic_and_semantics_remain_empty(self):
        scanned = next(item for item in discover_selenium_java_tests(FIXTURE) if item["test_name"] == "legacyFlow")
        contract = build_test_contract(
            {"repository_id": "REP001", "project_id": "PRJ001"}, "a" * 40,
            scanned, datetime.now(timezone.utc),
        )
        self.assertEqual((contract["framework"], contract["scanner_version"]), ("selenium_java", SELENIUM_JAVA_SCANNER_VERSION))
        self.assertTrue(contract["steps"] and contract["source_imports"] and contract["callable_references"])
        for field in ("inputs", "runtime_dependencies", "capabilities", "assertions"):
            self.assertEqual(contract[field], [])
        self.assertIsNone(contract["confidence"])

    def test_robot_playwright_and_selenium_map_to_same_canonical_structure(self):
        robot_root = Path(__file__).parent / "fixtures" / "robot_structure"
        playwright_root = Path(__file__).parent / "fixtures" / "playwright_structure"
        scanned = [
            discover_robot_tests(robot_root)[0],
            discover_playwright_tests(playwright_root)[0],
            discover_selenium_java_tests(FIXTURE)[0],
        ]
        contracts = [
            build_test_contract(
                {"repository_id": "REP001", "project_id": "PRJ001"}, "a" * 40,
                item, datetime.now(timezone.utc),
            )
            for item in scanned
        ]
        canonical_fields = {
            "test_identity", "steps", "source_imports", "callable_references",
            "source_commit_sha", "relative_file_path", "framework",
        }
        self.assertTrue(all(canonical_fields.issubset(contract) for contract in contracts))
        self.assertEqual({contract["framework"] for contract in contracts}, {"robot", "playwright", "selenium_java"})

    def test_java_revision_and_test_id_are_commit_isolated(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "ExampleTest.java"
            content = "import org.junit.Test; import org.openqa.selenium.WebDriver; class ExampleTest { WebDriver driver; @Test void works() { driver.quit(); } }"
            source.write_text(content, encoding="utf-8")
            first = content_commit_sha(root)
            _, tests, framework = scan_path(root, first)
            self.assertEqual(framework, "selenium_java")
            first_contract = build_test_contract({"repository_id": "REP001", "project_id": "PRJ001"}, first, tests[0], datetime.now(timezone.utc))
            source.write_text(content + " // revision two", encoding="utf-8")
            second = content_commit_sha(root)
            _, tests, _ = scan_path(root, second)
            second_contract = build_test_contract({"repository_id": "REP001", "project_id": "PRJ001"}, second, tests[0], datetime.now(timezone.utc))
            self.assertNotEqual(first, second)
            self.assertNotEqual(first_contract["test_id"], second_contract["test_id"])


if __name__ == "__main__":
    unittest.main()
