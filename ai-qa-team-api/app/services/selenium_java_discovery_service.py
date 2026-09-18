from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Iterable

from tree_sitter import Language, Node, Parser
import tree_sitter_java

from app.services.value_provenance_service import build_value_provenance


SELENIUM_JAVA_SCANNER_VERSION = "selenium-java-provenance-2"
IGNORED_DIRECTORIES = {".git", ".gradle", ".idea", "node_modules", "target", "build", "dist"}
MAX_SOURCE_BYTES = 2 * 1024 * 1024
TEST_IMPORTS = {
    "org.junit.Test": "junit4",
    "org.junit.jupiter.api.Test": "junit5",
    "org.testng.annotations.Test": "testng",
}
SELENIUM_PACKAGE = "org.openqa.selenium"
ASSERTION_TYPES = {"Assert", "Assertions"}


def _text(source: bytes, node: Node | None) -> str:
    return source[node.start_byte:node.end_byte].decode("utf-8") if node else ""


def _walk(node: Node) -> Iterable[Node]:
    yield node
    for child in node.named_children:
        yield from _walk(child)


def _parser() -> Parser:
    return Parser(Language(tree_sitter_java.language()))


def _clean_import(raw: str) -> tuple[str, bool, bool]:
    value = raw.removeprefix("import ").removesuffix(";").strip()
    is_static = value.startswith("static ")
    if is_static:
        value = value.removeprefix("static ").strip()
    wildcard = value.endswith(".*")
    return value.removesuffix(".*"), is_static, wildcard


def _package_name(source: bytes, root: Node) -> str:
    for node in root.named_children:
        if node.type == "package_declaration":
            raw = _text(source, node).removeprefix("package ").removesuffix(";").strip()
            return raw
    return ""


def _annotations(source: bytes, method: Node) -> list[str]:
    modifiers = method.child_by_field_name("modifiers")
    if not modifiers:
        modifiers = next((child for child in method.named_children if child.type == "modifiers"), None)
    return [_text(source, node) for node in _walk(modifiers) if node.type in {"annotation", "marker_annotation"}] if modifiers else []


def _parameters(source: bytes, node: Node | None) -> list[str]:
    if not node:
        return []
    return [_text(source, child) for child in node.named_children if child.type in {"formal_parameter", "spread_parameter"}]


def _method_calls(body: Node | None) -> list[Node]:
    if not body:
        return []
    calls: list[Node] = []

    def visit(node: Node, inside_call: bool = False) -> None:
        current = node.type == "method_invocation"
        if current and not inside_call:
            calls.append(node)
            return
        for child in node.named_children:
            visit(child, inside_call or current)

    visit(body)
    return sorted(calls, key=lambda item: item.start_byte)


def _raw_call(source: bytes, node: Node, source_file: str, sequence: int) -> dict:
    object_node = node.child_by_field_name("object")
    method_name = _text(source, node.child_by_field_name("name"))
    callee = f"{_text(source, object_node)}.{method_name}" if object_node else method_name
    arguments = node.child_by_field_name("arguments")
    return {
        "sequence": sequence,
        "name": callee,
        "arguments": [_text(source, child) for child in arguments.named_children] if arguments else [],
        "source_file": source_file,
        "line_number": node.start_point[0] + 1,
    }


def _declared_variables(source: bytes, scope: Node | None) -> dict[str, str]:
    variables: dict[str, str] = {}
    if not scope:
        return variables
    for declaration in _walk(scope):
        if declaration.type not in {"field_declaration", "local_variable_declaration"}:
            continue
        declared_type = _text(source, declaration.child_by_field_name("type"))
        if not declared_type:
            continue
        for child in declaration.named_children:
            if child.type == "variable_declarator":
                name = _text(source, child.child_by_field_name("name"))
                if name:
                    variables[name] = declared_type
    return variables


def _class_ancestor(node: Node) -> Node | None:
    parent = node.parent
    while parent and parent.type not in {"class_declaration", "interface_declaration"}:
        parent = parent.parent
    return parent


def _value_bindings(source: bytes, scope_node: Node | None, scope: str, source_file: str) -> list[dict]:
    bindings: list[dict] = []
    if not scope_node:
        return bindings
    for node in _walk(scope_node):
        name_node = None
        value_node = None
        evidence_kind = "ASSIGNMENT"
        if node.type == "variable_declarator":
            name_node = node.child_by_field_name("name")
            value_node = node.child_by_field_name("value")
            evidence_kind = "DECLARATION"
        elif node.type == "assignment_expression":
            name_node = node.child_by_field_name("left")
            value_node = node.child_by_field_name("right")
        if not name_node or not value_node or name_node.type != "identifier":
            continue
        ancestor = node.parent
        ambiguous = False
        while ancestor and ancestor != scope_node:
            if ancestor.type in {"if_statement", "switch_expression", "for_statement", "while_statement"}:
                ambiguous = True
                break
            ancestor = ancestor.parent
        bindings.append({
            "scope": scope, "name": _text(source, name_node), "expression": _text(source, value_node),
            "source_file": source_file, "line_number": node.start_point[0] + 1,
            "evidence_kind": evidence_kind, "ambiguous": ambiguous,
            "origin_kind": "CALL_RESULT" if any(child.type == "method_invocation" for child in _walk(value_node)) else None,
        })
    return bindings


def discover_selenium_java_tests(root: Path) -> list[dict]:
    root = root.resolve()
    files: list[Path] = []
    for path in root.rglob("*.java"):
        if any(part in IGNORED_DIRECTORIES for part in path.relative_to(root).parts):
            continue
        resolved = path.resolve()
        try:
            resolved.relative_to(root)
        except ValueError:
            continue
        if resolved.is_file() and resolved.stat().st_size <= MAX_SOURCE_BYTES:
            files.append(resolved)
    files.sort()
    parsed: dict[str, tuple[bytes, Node]] = {}
    file_imports: dict[str, list[tuple[str, bool, bool]]] = defaultdict(list)
    classes: dict[str, dict] = {}
    simple_classes: dict[str, list[str]] = defaultdict(list)
    definitions: dict[str, dict] = {}

    parser = _parser()
    for path in files:
        relative = path.resolve().relative_to(root).as_posix()
        source = path.read_bytes()
        tree = parser.parse(source)
        parsed[relative] = (source, tree.root_node)
        package = _package_name(source, tree.root_node)
        for node in tree.root_node.named_children:
            if node.type == "import_declaration":
                file_imports[relative].append(_clean_import(_text(source, node)))
        for node in _walk(tree.root_node):
            if node.type not in {"class_declaration", "interface_declaration"}:
                continue
            simple_name = _text(source, node.child_by_field_name("name"))
            if not simple_name:
                continue
            qualified_name = f"{package}.{simple_name}" if package else simple_name
            superclass_node = node.child_by_field_name("superclass")
            superclass = _text(source, superclass_node).removeprefix("extends ").strip() if superclass_node else None
            body = node.child_by_field_name("body")
            class_data = {
                "qualified_name": qualified_name,
                "simple_name": simple_name,
                "package": package,
                "source_file": relative,
                "line_number": node.start_point[0] + 1,
                "superclass": superclass,
                "is_interface": node.type == "interface_declaration",
                "fields": _declared_variables(source, body),
                "methods": defaultdict(list),
                "node": node,
            }
            classes[qualified_name] = class_data
            simple_classes[simple_name].append(qualified_name)

    for qualified_name, class_data in classes.items():
        source, _ = parsed[class_data["source_file"]]
        for node in _walk(class_data["node"]):
            if node.type != "method_declaration" or _class_ancestor(node) != class_data["node"]:
                continue
            method_name = _text(source, node.child_by_field_name("name"))
            body = node.child_by_field_name("body")
            reference = f"{class_data['source_file']}::method:{qualified_name}.{method_name}:{node.start_point[0] + 1}"
            definition = {
                "callable_reference": reference,
                "name": f"{class_data['simple_name']}.{method_name}",
                "source_file": class_data["source_file"],
                "line_number": node.start_point[0] + 1,
                "declared_parameters": _parameters(source, node.child_by_field_name("parameters")),
                "nested_calls": [
                    _raw_call(source, call, class_data["source_file"], index + 1)
                    for index, call in enumerate(_method_calls(body))
                ],
                "class_name": qualified_name,
                "method_name": method_name,
                "annotations": _annotations(source, node),
                "body": body,
            }
            definitions[reference] = definition
            class_data["methods"][method_name].append(reference)

    def imported_class(source_file: str, simple_name: str) -> list[str]:
        matches: list[str] = []
        source_package = next((item["package"] for item in classes.values() if item["source_file"] == source_file), "")
        same_package = f"{source_package}.{simple_name}" if source_package else simple_name
        if same_package in classes:
            matches.append(same_package)
        for path, _, wildcard in file_imports[source_file]:
            candidate = f"{path}.{simple_name}" if wildcard else path
            if candidate in classes and candidate.split(".")[-1] == simple_name:
                matches.append(candidate)
        return list(dict.fromkeys(matches or simple_classes.get(simple_name, [])))

    def class_methods(class_name: str, method_name: str, visited: set[str] | None = None) -> list[str]:
        visited = visited or set()
        if class_name in visited or class_name not in classes:
            return []
        visited.add(class_name)
        found = list(classes[class_name]["methods"].get(method_name, []))
        if found:
            return found
        superclass = classes[class_name].get("superclass")
        if not superclass:
            return []
        parents = imported_class(classes[class_name]["source_file"], superclass)
        inherited: list[str] = []
        for parent in parents:
            inherited.extend(class_methods(parent, method_name, visited))
        return inherited

    def resolve_call(call: dict, definition: dict) -> dict:
        source, _ = parsed[definition["source_file"]]
        owner = classes[definition["class_name"]]
        variables = {**owner["fields"], **_declared_variables(source, definition["body"])}
        name = call["name"]
        object_name, method_name = name.rsplit(".", 1) if "." in name else (None, name)
        matches: list[str] = []
        dynamic = False
        external = False
        if object_name is None or object_name == "this":
            matches = class_methods(definition["class_name"], method_name)
        else:
            declared_type = variables.get(object_name)
            candidate_classes = imported_class(definition["source_file"], declared_type or object_name)
            if declared_type and candidate_classes and any(classes[item]["is_interface"] for item in candidate_classes):
                dynamic = True
            elif candidate_classes:
                for candidate in candidate_classes:
                    matches.extend(class_methods(candidate, method_name))
            imported_types = {path.split(".")[-1]: path for path, _, _ in file_imports[definition["source_file"]]}
            external_type = imported_types.get(declared_type or object_name, "")
            if external_type.startswith(SELENIUM_PACKAGE) or (declared_type or object_name) in ASSERTION_TYPES:
                external = True
            if object_name in {"driver", "element", "webDriver", "webElement"}:
                external = True
        if len(matches) == 1:
            status, reference = "RESOLVED", matches[0]
        elif len(matches) > 1:
            status, reference = "AMBIGUOUS", None
        elif dynamic:
            status, reference = "DYNAMIC", None
        elif external or object_name in ASSERTION_TYPES:
            status, reference = "EXTERNAL_LIBRARY", None
        else:
            status, reference = "UNRESOLVED", None
        return {**call, "resolution_status": status, "keyword_reference": None, "callable_reference": reference}

    resolved_definitions: dict[str, dict] = {}
    for reference, definition in definitions.items():
        resolved_definitions[reference] = {
            key: value for key, value in definition.items()
            if key not in {"class_name", "method_name", "annotations", "body"}
        }
        resolved_definitions[reference]["nested_calls"] = [resolve_call(call, definition) for call in definition["nested_calls"]]

    source_imports: dict[str, list[dict]] = defaultdict(list)
    for source_file, import_items in file_imports.items():
        for path, is_static, wildcard in import_items:
            local_matches = [name for name in classes if name == path or (wildcard and name.startswith(f"{path}."))]
            source_imports[source_file].append({
                "importing_file": source_file,
                "raw_path": path,
                "imported_names": [path.split(".")[-1] + (".*" if wildcard else "")],
                "resolved_path": classes[local_matches[0]]["source_file"] if len(local_matches) == 1 else None,
                "resolution_status": "RESOLVED" if len(local_matches) == 1 else "EXTERNAL_LIBRARY",
            })

    discovered: list[dict] = []
    for reference, definition in definitions.items():
        source_file = definition["source_file"]
        imported = {path: runner for path, runner in TEST_IMPORTS.items() if any(item[0] == path for item in file_imports[source_file])}
        runner = next(iter(imported.values()), None)
        has_test_annotation = any(annotation.split("(", 1)[0].endswith("@Test") for annotation in definition["annotations"])
        has_selenium = any(item[0].startswith(SELENIUM_PACKAGE) for item in file_imports[source_file])
        if not runner or not has_test_annotation or not has_selenium:
            continue
        steps = [resolve_call(call, definition) for call in definition["nested_calls"]]
        referenced: dict[str, dict] = {}
        pending = [step["callable_reference"] for step in steps if step["callable_reference"]]
        while pending:
            item = pending.pop()
            if item in referenced:
                continue
            target = resolved_definitions[item]
            referenced[item] = target
            pending.extend(
                call["callable_reference"] for call in target["nested_calls"]
                if call["callable_reference"] and call["callable_reference"] not in referenced
            )
        qualified_class = definition["class_name"]
        discovered.append({
            "framework": "selenium_java",
            "scanner_version": SELENIUM_JAVA_SCANNER_VERSION,
            "test_name": definition["method_name"],
            "test_identity": f"{qualified_class}.{definition['method_name']}",
            "relative_file_path": source_file,
            "line_number": definition["line_number"],
            "tags": [f"runner:{runner}"],
            "steps": steps,
            "resource_imports": [],
            "keyword_references": [],
            "source_imports": source_imports[source_file],
            "callable_references": sorted(referenced.values(), key=lambda item: item["callable_reference"]),
            "value_provenance": build_value_provenance(
                f"{qualified_class}.{definition['method_name']}",
                steps,
                list(referenced.values()),
                _value_bindings(
                    parsed[source_file][0], definition.get("body"),
                    f"{qualified_class}.{definition['method_name']}", source_file,
                ) + [
                    binding
                    for item in referenced
                    for binding in _value_bindings(
                        parsed[definitions[item]["source_file"]][0], definitions[item].get("body"),
                        item, definitions[item]["source_file"],
                    )
                ],
            ),
        })
    return discovered
