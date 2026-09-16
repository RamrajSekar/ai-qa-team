import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

TEST_ENV = {
    "MONGO_URI": "mongodb://localhost:27017",
    "MONGO_DB": "repository_tests",
    "REDIS_HOST": "localhost",
    "REDIS_PORT": "6379",
    "REDIS_USERNAME": "test",
    "REDIS_PASSWORD": "test-only",
    "SESSION_SECRET_KEY": "session-test-only",
    "JWT_SECRET_KEY": "jwt-test-only",
    "OPENAI_API_KEY": "",
}

with patch.dict(os.environ, TEST_ENV):
    from app.routes import repository_routes, user_routes
    from app.models.repository_model import RepositoryConnectRequest
    from app.services.repository_discovery_service import (
        discover_robot_tests,
        git_commit_sha,
        static_scan,
        validate_public_github_url,
    )


ROBOT_ONE = """*** Test Cases ***
Valid Login
    [Tags]    smoke    login
    Log    ok
"""

ROBOT_TWO = """*** Test Cases ***
Search Tour
    [Tags]    regression
    Log    search

Invalid Tour
    Log    invalid
"""


class _Collection:
    def __init__(self):
        self.documents = []
        self.update_calls = []

    async def update_one(self, query, update):
        self.update_calls.append((query, update))
        for document in self.documents:
            if all(document.get(key) == value for key, value in query.items()):
                document.update(update.get("$set", {}))
                break

    async def delete_many(self, query):
        self.documents = [
            document for document in self.documents
            if not all(document.get(key) == value for key, value in query.items())
        ]

    async def insert_many(self, documents):
        self.documents.extend(documents)

    async def find_one(self, query):
        return next((document for document in self.documents if all(document.get(k) == v for k, v in query.items())), None)


class _DB(dict):
    def __missing__(self, key):
        value = _Collection()
        self[key] = value
        return value


def git(path: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True)


class RepositoryDiscoveryTests(unittest.IsolatedAsyncioTestCase):
    def test_public_github_url_validation(self):
        valid = "https://github.com/example/robot-suite"
        self.assertEqual(validate_public_github_url(valid), valid)
        for invalid in (
            "http://github.com/example/repo",
            "https://gitlab.com/example/repo",
            "https://token@github.com/example/repo",
            "https://github.com/example/repo?token=secret",
            "https://github.com/example/too/many",
        ):
            with self.subTest(invalid=invalid), self.assertRaises(HTTPException):
                validate_public_github_url(invalid)

    def test_local_repository_policy_and_missing_path(self):
        with patch.object(repository_routes.settings, "enable_local_repositories", True):
            with patch.object(repository_routes.settings, "app_env", "development"):
                self.assertTrue(repository_routes.local_repositories_enabled())
            with patch.object(repository_routes.settings, "app_env", "production"):
                self.assertFalse(repository_routes.local_repositories_enabled())
        with self.assertRaises(HTTPException):
            static_scan("LOCAL", None, "Z:/missing/robot-repository", "main")

    def test_robot_detection_multiple_files_names_lines_and_tags(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tests").mkdir()
            (root / "tests" / "login.robot").write_text(ROBOT_ONE, encoding="utf-8")
            (root / "tests" / "tour.robot").write_text(ROBOT_TWO, encoding="utf-8")
            discovered = discover_robot_tests(root)

        self.assertEqual([item["test_name"] for item in discovered], ["Valid Login", "Search Tour", "Invalid Tour"])
        self.assertEqual(discovered[0]["relative_file_path"], "tests/login.robot")
        self.assertEqual(discovered[0]["line_number"], 2)
        self.assertEqual(discovered[0]["tags"], ["smoke", "login"])

    def test_git_commit_sha_capture(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            git(root, "init")
            git(root, "config", "user.email", "tests@example.com")
            git(root, "config", "user.name", "Repository Tests")
            (root / "suite.robot").write_text(ROBOT_ONE, encoding="utf-8")
            git(root, "add", "suite.robot")
            git(root, "commit", "-m", "initial")
            expected = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
            self.assertEqual(git_commit_sha(root), expected)

    async def test_rescan_keeps_commit_registries_separate_and_current_metadata_isolated(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            git(root, "init")
            git(root, "config", "user.email", "tests@example.com")
            git(root, "config", "user.name", "Repository Tests")
            suite = root / "suite.robot"
            suite.write_text(ROBOT_ONE, encoding="utf-8")
            git(root, "add", "suite.robot")
            git(root, "commit", "-m", "first")
            repository = {
                "repository_id": "REP001", "project_id": "PRJ001", "source_type": "LOCAL",
                "provider": "local", "repository_url": None, "local_path": str(root),
                "branch": "main", "framework": "auto", "scan_status": "scanning",
                "scanner_version": "robot-basic-1", "created_by": "owner@example.com",
            }
            fake_db = _DB()
            fake_db["repositories"].documents.append(repository.copy())
            with patch.object(repository_routes, "db", fake_db):
                first = await repository_routes.scan_repository(repository)
                suite.write_text(ROBOT_TWO, encoding="utf-8")
                git(root, "add", "suite.robot")
                git(root, "commit", "-m", "second")
                second = await repository_routes.scan_repository({**repository, **first})

        self.assertNotEqual(first["source_commit_sha"], second["source_commit_sha"])
        commits = {document["source_commit_sha"] for document in fake_db["discovered_tests"].documents}
        self.assertEqual(commits, {first["source_commit_sha"], second["source_commit_sha"]})
        current = [document for document in fake_db["discovered_tests"].documents if document["source_commit_sha"] == second["source_commit_sha"]]
        self.assertEqual(len(current), 2)
        self.assertTrue(all(document["project_id"] == "PRJ001" and document["repository_id"] == "REP001" for document in current))

    async def test_scan_failure_updates_only_repository_state(self):
        fake_db = _DB()
        repository = {
            "repository_id": "REP001", "project_id": "PRJ001", "source_type": "GITHUB_PUBLIC",
            "provider": "github", "repository_url": "https://github.com/example/repo",
            "local_path": None, "branch": "main", "framework": "auto", "created_by": "owner@example.com",
        }
        fake_db["repositories"].documents.append(repository.copy())
        with (
            patch.object(repository_routes, "db", fake_db),
            patch.object(repository_routes, "run_in_threadpool", new=AsyncMock(side_effect=RuntimeError("clone failed"))),
        ):
            result = await repository_routes.scan_repository(repository)

        self.assertEqual(result["scan_status"], "failed")
        self.assertIn("clone failed", result["scan_error"])
        self.assertEqual(fake_db["projects"].update_calls, [])
        self.assertEqual(fake_db["environments"].update_calls, [])

    async def test_project_ownership_is_enforced(self):
        fake_db = _DB()
        fake_db["projects"].documents.append({"project_id": "PRJ001", "created_by": "owner@example.com"})
        with patch.object(repository_routes, "db", fake_db):
            await repository_routes.owned_project("PRJ001", "owner@example.com")
            with self.assertRaises(HTTPException):
                await repository_routes.owned_project("PRJ001", "other@example.com")

    async def test_local_connect_is_rejected_server_side_in_production(self):
        fake_db = _DB()
        fake_db["projects"].documents.append({"project_id": "PRJ001", "created_by": "owner@example.com"})
        with tempfile.TemporaryDirectory() as directory:
            with (
                patch.object(repository_routes, "db", fake_db),
                patch.object(repository_routes.settings, "enable_local_repositories", True),
                patch.object(repository_routes.settings, "app_env", "production"),
            ):
                with self.assertRaises(HTTPException) as raised:
                    await repository_routes.connect_repository(
                        RepositoryConnectRequest(
                            project_id="PRJ001", source_type="LOCAL", local_path=directory
                        ),
                        {"email": "owner@example.com"},
                    )
        self.assertEqual(raised.exception.status_code, 403)
        self.assertEqual(fake_db["repositories"].documents, [])

    async def test_skip_for_now_only_advances_onboarding(self):
        fake_db = _DB()
        fake_db["users"].documents.append({"email": "owner@example.com"})
        with patch.object(user_routes, "db", fake_db):
            result = await user_routes.update_onboarding(
                {"step_key": "test_import", "current_step": 4}, {"email": "owner@example.com"}
            )
        self.assertEqual(result, {"success": True})
        self.assertEqual(fake_db["projects"].update_calls, [])
        self.assertEqual(fake_db["environments"].update_calls, [])


if __name__ == "__main__":
    unittest.main()
