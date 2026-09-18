from datetime import datetime

from app.models.test_contract_model import TestContract
from app.services.repository_discovery_service import SCANNER_VERSION, discovered_test_id


CONTRACT_VERSION = "3"
REGISTRY_VERSION = "test-registry-3"


def build_test_contract(
    repository: dict,
    source_commit_sha: str,
    discovered_test: dict,
    discovered_at: datetime,
) -> dict:
    """Map deterministic scanner output into the canonical registry contract."""
    document = {
        "contract_version": CONTRACT_VERSION,
        "registry_version": REGISTRY_VERSION,
        "scanner_version": discovered_test.get("scanner_version", SCANNER_VERSION),
        "test_id": discovered_test_id(
            repository["repository_id"], source_commit_sha,
            discovered_test["relative_file_path"], discovered_test.get("test_identity", discovered_test["test_name"]),
        ),
        "project_id": repository["project_id"],
        "repository_id": repository["repository_id"],
        "source_commit_sha": source_commit_sha,
        "framework": discovered_test.get("framework", "robot"),
        "test_name": discovered_test["test_name"],
        "test_identity": discovered_test.get("test_identity", discovered_test["test_name"]),
        "relative_file_path": discovered_test["relative_file_path"],
        "line_number": discovered_test.get("line_number"),
        "tags": discovered_test.get("tags", []),
        "steps": discovered_test.get("steps", []),
        "resource_imports": discovered_test.get("resource_imports", []),
        "keyword_references": discovered_test.get("keyword_references", []),
        "source_imports": discovered_test.get("source_imports", []),
        "callable_references": discovered_test.get("callable_references", []),
        "inputs": [],
        "runtime_dependencies": [],
        "capabilities": [],
        "assertions": [],
        "confidence": None,
        "discovered_at": discovered_at,
        "updated_at": discovered_at,
    }
    return TestContract.model_validate(document).model_dump()


def canonical_test_contract(document: dict, repository: dict) -> dict:
    """Provide a complete contract for legacy discovered-test rows without rewriting Mongo."""
    discovered_at = document["discovered_at"]
    compatible = {
        **document,
        "contract_version": document.get("contract_version", CONTRACT_VERSION),
        "registry_version": document.get("registry_version", REGISTRY_VERSION),
        "scanner_version": document.get("scanner_version", repository.get("scanner_version", SCANNER_VERSION)),
        "test_identity": document.get("test_identity", document["test_name"]),
        "steps": document.get("steps", []),
        "resource_imports": document.get("resource_imports", []),
        "keyword_references": document.get("keyword_references", []),
        "source_imports": document.get("source_imports", []),
        "callable_references": document.get("callable_references", []),
        "inputs": document.get("inputs", []),
        "runtime_dependencies": document.get("runtime_dependencies", []),
        "capabilities": document.get("capabilities", []),
        "assertions": document.get("assertions", []),
        "confidence": document.get("confidence"),
        "updated_at": document.get("updated_at", discovered_at),
    }
    return TestContract.model_validate(compatible).model_dump()
