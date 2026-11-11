import hashlib
from collections import defaultdict
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from urllib.parse import urlparse

from fastapi import HTTPException
from robot.api import get_model
from robot.libdoc import LibraryDocumentation
from robot.parsing.model.blocks import KeywordSection, SettingSection, TestCaseSection, VariableSection
from robot.parsing.model.statements import Arguments, KeywordCall, LibraryImport, ResourceImport, Tags, Variable

from app.services.playwright_discovery_service import discover_playwright_tests
from app.services.selenium_java_discovery_service import discover_selenium_java_tests
from app.services.value_provenance_service import build_value_provenance


SCANNER_VERSION = "robot-provenance-3"
REPOSITORY_SCANNER_VERSION = "repository-static-4"
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
    path = path.resolve()
    digest = hashlib.sha256()
    ignored = {".git", ".gradle", ".idea", ".next", "node_modules", "target", "dist", "build"}
    source_files = sorted({
        *path.rglob("*.robot"), *path.rglob("*.resource"), *path.rglob("*.ts"),
        *path.rglob("*.js"), *path.rglob("*.tsx"), *path.rglob("*.jsx"), *path.rglob("*.java"),
    })
    for source_file in source_files:
        if any(part in ignored for part in source_file.relative_to(path).parts):
            continue
        resolved = source_file.resolve()
        try:
            relative = resolved.relative_to(path)
        except ValueError:
            continue
        digest.update(relative.as_posix().encode())
        with resolved.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
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


def _normalized_keyword(name: str) -> str:
    return re.sub(r"[ _]", "", name).casefold()


def _relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _keyword_reference(relative_path: str, name: str) -> str:
    return f"{relative_path}::{_normalized_keyword(name)}"


def _resolve_resource(root: Path, importer: Path, raw_path: str) -> tuple[str, str | None]:
    if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*://", raw_path):
        return "REMOTE", None
    if "${" in raw_path or "%{" in raw_path:
        return "DYNAMIC", None
    candidate = (importer.parent / raw_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return "OUTSIDE_REPOSITORY", None
    if not candidate.is_file() or candidate.suffix.lower() not in {".robot", ".resource"}:
        return "UNRESOLVED", None
    return "RESOLVED", _relative(root, candidate)


def _call(statement: KeywordCall, source_file: str, sequence: int) -> dict:
    return {
        "sequence": sequence,
        "name": statement.keyword,
        "arguments": list(statement.args),
        "source_file": source_file,
        "line_number": getattr(statement, "lineno", None),
        "assignments": list(statement.assign),
    }


def discover_robot_tests(root: Path) -> list[dict]:
    root = root.resolve()
    parsed: dict[str, object] = {}
    resource_imports: dict[str, list[dict]] = {}
    libraries: dict[str, set[str]] = {}
    definitions: dict[str, dict] = {}
    variable_bindings: dict[str, list[dict]] = defaultdict(list)

    source_files = sorted({*root.rglob("*.robot"), *root.rglob("*.resource")})
    for source_file in source_files:
        relative_path = _relative(root, source_file.resolve())
        try:
            model = get_model(str(source_file))
        except Exception as exc:
            raise RuntimeError(f"Could not parse {relative_path}: {exc}") from exc
        parsed[relative_path] = model
        imports: list[dict] = []
        imported_libraries: set[str] = set()
        for section in model.sections:
            if isinstance(section, SettingSection):
                for statement in section.body:
                    if isinstance(statement, ResourceImport):
                        raw_path = statement.name
                        status, resolved_path = _resolve_resource(root, source_file, raw_path)
                        imports.append({
                            "importing_file": relative_path,
                            "raw_path": raw_path,
                            "resolved_path": resolved_path,
                            "resolution_status": status,
                        })
                    elif isinstance(statement, LibraryImport):
                        imported_libraries.add(statement.name)
            elif isinstance(section, KeywordSection):
                for keyword in section.body:
                    declared_arguments: list[str] = []
                    nested_calls: list[dict] = []
                    for statement in keyword.body:
                        if isinstance(statement, Arguments):
                            declared_arguments.extend(statement.values)
                        elif isinstance(statement, KeywordCall):
                            nested_calls.append(_call(statement, relative_path, len(nested_calls) + 1))
                    reference = _keyword_reference(relative_path, keyword.name)
                    definitions[reference] = {
                        "keyword_reference": reference,
                        "name": keyword.name,
                        "source_file": relative_path,
                        "line_number": getattr(keyword, "lineno", None),
                        "declared_arguments": declared_arguments,
                        "nested_calls": nested_calls,
                    }
            elif isinstance(section, VariableSection):
                for statement in section.body:
                    if isinstance(statement, Variable) and statement.value:
                        variable_bindings[relative_path].append({
                            "name": statement.name.strip("${}@&%{}"),
                            "expression": " ".join(statement.value), "source_file": relative_path,
                            "line_number": getattr(statement, "lineno", None), "evidence_kind": "DECLARATION",
                            "origin_kind": "LITERAL",
                        })
        resource_imports[relative_path] = imports
        libraries[relative_path] = imported_libraries

    builtins = {_normalized_keyword(keyword.name) for keyword in LibraryDocumentation("BuiltIn").keywords}

    def visible_files(source_file: str) -> tuple[list[str], list[dict]]:
        visible: list[str] = []
        imports_seen: list[dict] = []
        visited: set[str] = set()

        def visit(current: str) -> None:
            if current in visited:
                return
            visited.add(current)
            for item in resource_imports.get(current, []):
                if item not in imports_seen:
                    imports_seen.append(item)
                resolved_path = item.get("resolved_path")
                if item["resolution_status"] == "RESOLVED" and resolved_path:
                    if resolved_path not in visible:
                        visible.append(resolved_path)
                    visit(resolved_path)

        visit(source_file)
        return visible, imports_seen

    def resolve_call(call: dict, source_file: str) -> dict:
        normalized = _normalized_keyword(call["name"])
        local_matches = [
            definition for definition in definitions.values()
            if definition["source_file"] == source_file and _normalized_keyword(definition["name"]) == normalized
        ]
        visible, _ = visible_files(source_file)
        resource_matches = [
            definition for definition in definitions.values()
            if definition["source_file"] in visible and _normalized_keyword(definition["name"]) == normalized
        ]
        matches = local_matches or resource_matches
        if len(matches) == 1:
            return {**call, "resolution_status": "RESOLVED", "keyword_reference": matches[0]["keyword_reference"]}
        if len(matches) > 1:
            return {**call, "resolution_status": "AMBIGUOUS", "keyword_reference": None}
        library_prefixes = {
            name.rsplit(".", 1)[-1].casefold() for name in libraries.get(source_file, set())
        }
        call_prefix = call["name"].split(".", 1)[0].casefold() if "." in call["name"] else None
        if normalized in builtins or (call_prefix and call_prefix in library_prefixes):
            status = "BUILTIN_OR_LIBRARY"
        else:
            status = "UNRESOLVED"
        return {**call, "resolution_status": status, "keyword_reference": None}

    resolved_definitions: dict[str, dict] = {}
    for reference, definition in definitions.items():
        resolved_definitions[reference] = {
            **definition,
            "nested_calls": [resolve_call(call, definition["source_file"]) for call in definition["nested_calls"]],
        }

    discovered: list[dict] = []
    for relative_path, model in parsed.items():
        if not relative_path.endswith(".robot"):
            continue
        for section in model.sections:
            if isinstance(section, TestCaseSection):
                for test in section.body:
                    tags: list[str] = []
                    raw_calls: list[dict] = []
                    for statement in test.body:
                        if isinstance(statement, Tags):
                            tags.extend(statement.values)
                        elif isinstance(statement, KeywordCall):
                            raw_calls.append(_call(statement, relative_path, len(raw_calls) + 1))
                    steps = [resolve_call(call, relative_path) for call in raw_calls]
                    _, imports = visible_files(relative_path)
                    referenced: dict[str, dict] = {}
                    pending = [step["keyword_reference"] for step in steps if step["keyword_reference"]]
                    while pending:
                        reference = pending.pop()
                        if reference in referenced:
                            continue
                        definition = resolved_definitions[reference]
                        referenced[reference] = definition
                        pending.extend(
                            call["keyword_reference"] for call in definition["nested_calls"]
                            if call["keyword_reference"] and call["keyword_reference"] not in referenced
                        )
                    discovered.append({
                        "framework": "robot",
                        "scanner_version": SCANNER_VERSION,
                        "test_name": test.name,
                        "relative_file_path": relative_path,
                        "line_number": getattr(test, "lineno", None),
                        "tags": list(dict.fromkeys(tags)),
                        "steps": steps,
                        "resource_imports": imports,
                        "keyword_references": sorted(referenced.values(), key=lambda item: item["keyword_reference"]),
                        "value_provenance": build_value_provenance(
                            test.name,
                            steps,
                            list(referenced.values()),
                            [
                                {**item, "scope": test.name, "name": item["name"]}
                                for item in variable_bindings.get(relative_path, [])
                            ] + [
                                {
                                    "scope": test.name,
                                    "name": assignment.rstrip("=").strip().strip("${}@&%{}"),
                                    "expression": f"{call['name']}({', '.join(call['arguments'])})",
                                    "source_file": relative_path, "line_number": call.get("line_number"),
                                    "evidence_kind": "ASSIGNMENT",
                                    "origin_kind": "CALL_RESULT",
                                }
                                for call in raw_calls for assignment in call.get("assignments", [])
                            ],
                        ),
                    })
    return discovered


def _scan_robot(root: Path) -> tuple[list[dict], bool]:
    detected = any(root.rglob("*.robot"))
    return (discover_robot_tests(root) if detected else []), detected


def _scan_playwright(root: Path) -> tuple[list[dict], bool]:
    tests = discover_playwright_tests(root)
    return tests, bool(tests)


def _scan_selenium_java(root: Path) -> tuple[list[dict], bool]:
    tests = discover_selenium_java_tests(root)
    return tests, bool(tests)


FRAMEWORK_SCANNERS = {
    "robot": _scan_robot,
    "playwright": _scan_playwright,
    "selenium_java": _scan_selenium_java,
}


def scan_path(root: Path, commit_sha: str) -> tuple[str, list[dict], str]:
    tests: list[dict] = []
    frameworks: set[str] = set()
    for framework, scanner in FRAMEWORK_SCANNERS.items():
        discovered, detected = scanner(root)
        tests.extend(discovered)
        if detected:
            frameworks.add(framework)
    detected = "mixed" if len(frameworks) > 1 else next(iter(frameworks), "unsupported")
    return commit_sha, tests, detected


def static_scan(source_type: str, repository_url: str | None, local_path: str | None, branch: str) -> tuple[str, list[dict], str]:
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
