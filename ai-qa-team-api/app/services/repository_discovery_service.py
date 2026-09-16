import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from urllib.parse import urlparse

from fastapi import HTTPException
from robot.api import get_model
from robot.parsing.model.blocks import TestCaseSection
from robot.parsing.model.statements import Tags


SCANNER_VERSION = "robot-basic-1"
GITHUB_PATH = re.compile(r"^/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?$")


def validate_public_github_url(value: str) -> str:
    parsed = urlparse(value.strip())
    if (
        parsed.scheme != "https"
        or parsed.hostname != "github.com"
        or parsed.username
        or parsed.password
        or parsed.port
        or parsed.query
        or parsed.fragment
        or not GITHUB_PATH.fullmatch(parsed.path)
    ):
        raise HTTPException(422, "Use a public GitHub HTTPS URL such as https://github.com/user/repository")
    return value.strip().rstrip("/")


def validate_branch(value: str) -> str:
    branch = value.strip()
    if not branch or branch.startswith("-") or ".." in branch or not re.fullmatch(r"[A-Za-z0-9._/-]+", branch):
        raise HTTPException(422, "Invalid branch name")
    return branch


def validate_local_repository_path(value: str) -> Path:
    root = Path(value).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise HTTPException(422, "Local repository path does not exist or is not a directory")
    return root


def git_commit_sha(path: Path) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"], capture_output=True,
        text=True, timeout=15, check=False,
    )
    if result.returncode != 0:
        return None
    sha = result.stdout.strip()
    return sha if re.fullmatch(r"[0-9a-fA-F]{40,64}", sha) else None


def content_commit_sha(path: Path) -> str:
    digest = hashlib.sha256()
    for robot_file in sorted(path.rglob("*.robot")):
        digest.update(robot_file.relative_to(path).as_posix().encode())
        digest.update(robot_file.read_bytes())
    return digest.hexdigest()


def clone_public_repository(repository_url: str, branch: str, destination: Path) -> str:
    git_environment = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    result = subprocess.run(
        ["git", "clone", "--depth", "1", "--branch", branch, "--single-branch", repository_url, str(destination)],
        capture_output=True, text=True, timeout=120, check=False, env=git_environment,
    )
    if result.returncode != 0:
        detail = result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "Git clone failed"
        raise RuntimeError(detail)
    commit_sha = git_commit_sha(destination)
    if not commit_sha:
        raise RuntimeError("Unable to determine the cloned repository commit")
    return commit_sha


def discover_robot_tests(root: Path) -> list[dict]:
    discovered: list[dict] = []
    for robot_file in sorted(root.rglob("*.robot")):
        try:
            model = get_model(str(robot_file))
        except Exception as exc:
            raise RuntimeError(f"Could not parse {robot_file.relative_to(root).as_posix()}: {exc}") from exc
        for section in model.sections:
            if not isinstance(section, TestCaseSection):
                continue
            for test in section.body:
                tags: list[str] = []
                for statement in test.body:
                    if isinstance(statement, Tags):
                        tags.extend(statement.values)
                discovered.append({
                    "test_name": test.name,
                    "relative_file_path": robot_file.relative_to(root).as_posix(),
                    "line_number": getattr(test, "lineno", None),
                    "tags": list(dict.fromkeys(tags)),
                })
    return discovered


def scan_path(root: Path, commit_sha: str) -> tuple[str, list[dict], bool]:
    has_robot_files = any(root.rglob("*.robot"))
    return commit_sha, discover_robot_tests(root), has_robot_files


def static_scan(source_type: str, repository_url: str | None, local_path: str | None, branch: str) -> tuple[str, list[dict], bool]:
    if source_type == "LOCAL":
        root = validate_local_repository_path(local_path or "")
        return scan_path(root, git_commit_sha(root) or content_commit_sha(root))

    url = validate_public_github_url(repository_url or "")
    safe_branch = validate_branch(branch)
    workspace = Path(tempfile.mkdtemp(prefix="aiqa-scan-"))
    try:
        commit_sha = clone_public_repository(url, safe_branch, workspace)
        return scan_path(workspace, commit_sha)
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def discovered_test_id(repository_id: str, commit_sha: str, relative_path: str, test_name: str) -> str:
    value = f"{repository_id}:{commit_sha}:{relative_path}:{test_name}".encode()
    return "TST" + hashlib.sha256(value).hexdigest()[:20].upper()
