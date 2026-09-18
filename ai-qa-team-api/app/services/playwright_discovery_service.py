from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import re
from typing import Iterable

from tree_sitter import Language, Node, Parser
import tree_sitter_javascript
import tree_sitter_typescript


PLAYWRIGHT_SCANNER_VERSION = "playwright-tsjs-1"
SUPPORTED_SUFFIXES = (".spec.ts", ".test.ts", ".spec.js", ".test.js")
SOURCE_EXTENSIONS = (".ts", ".js", ".tsx", ".jsx")
PLAYWRIGHT_MODULE = "@playwright/test"
IGNORED_DIRECTORIES = {".git", ".next", "node_modules", "dist", "build"}
MAX_SOURCE_BYTES = 2 * 1024 * 1024


def _parser(path: Path) -> Parser:
    language = (
        Language(tree_sitter_typescript.language_typescript())
        if path.suffix.lower() in {".ts", ".tsx"}
        else Language(tree_sitter_javascript.language())
    )
    return Parser(language)


def _text(source: bytes, node: Node | None) -> str:
    return source[node.start_byte:node.end_byte].decode("utf-8") if node else ""


def _walk(node: Node) -> Iterable[Node]:
    yield node
    for child in node.named_children:
        yield from _walk(child)


def _string_value(source: bytes, node: Node | None) -> str | None:
    if node is None:
        return None
    raw = _text(source, node)
    if node.type == "string" and len(raw) >= 2:
        return raw[1:-1]
    if node.type == "template_string" and not any(child.type == "template_substitution" for child in node.named_children):
        return raw[1:-1]
    return None


def _parameters(source: bytes, node: Node | None) -> list[str]:
    if node is None:
        return []
    if node.type == "identifier":
        return [_text(source, node)]
    return [_text(source, child) for child in node.named_children]


def _reference(path: str, kind: str, name: str) -> str:
    return f"{path}::{kind}:{name}"


def _resolve_module(root: Path, importer: Path, raw_path: str) -> tuple[str, str | None]:
    if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*://", raw_path):
        return "REMOTE", None
    if not raw_path.startswith((".", "/")):
        return "EXTERNAL_LIBRARY", None
    base = (importer.parent / raw_path).resolve()
    try:
        base.relative_to(root)
    except ValueError:
        return "OUTSIDE_REPOSITORY", None
    candidates = [base] if base.suffix else [base.with_suffix(ext) for ext in SOURCE_EXTENSIONS]
    candidates.extend(base / f"index{ext}" for ext in SOURCE_EXTENSIONS)
    for candidate in candidates:
        if candidate.is_file():
            resolved = candidate.resolve()
            try:
                return "RESOLVED", resolved.relative_to(root).as_posix()
            except ValueError:
                return "OUTSIDE_REPOSITORY", None
    return "UNRESOLVED", None


def _import_names(source: bytes, node: Node) -> list[tuple[str, str]]:
    names: list[tuple[str, str]] = []
    for child in _walk(node):
        if child.type != "import_specifier":
            continue
        imported = child.child_by_field_name("name")
        alias = child.child_by_field_name("alias")
        original = _text(source, imported)
        names.append((original, _text(source, alias) or original))
    clause = node.child_by_field_name("import")
    if clause and clause.type == "identifier":
        names.append(("default", _text(source, clause)))
    return names


def _top_level_calls(body: Node | None) -> list[Node]:
    if body is None:
        return []
    calls: list[Node] = []

    def visit(node: Node, inside_call: bool = False) -> None:
        current_is_call = node.type == "call_expression"
        if current_is_call and not inside_call:
            calls.append(node)
            return
        for child in node.named_children:
            visit(child, inside_call or current_is_call)

    visit(body)
    return sorted(calls, key=lambda item: item.start_byte)


def _raw_call(source: bytes, node: Node, source_file: str, sequence: int) -> dict:
    function = node.child_by_field_name("function")
    arguments = node.child_by_field_name("arguments")
    return {
        "sequence": sequence,
        "name": _text(source, function),
        "arguments": [_text(source, child) for child in arguments.named_children] if arguments else [],
        "source_file": source_file,
        "line_number": node.start_point[0] + 1,
    }


def _test_tags(source: bytes, arguments: list[Node]) -> list[str]:
    tags: list[str] = []
    for argument in arguments[1:-1]:
        if argument.type != "object":
            continue
        for pair in argument.named_children:
            if pair.type != "pair" or _text(source, pair.child_by_field_name("key")) != "tag":
                continue
            value = pair.child_by_field_name("value")
            literal = _string_value(source, value)
            if literal is not None:
                tags.append(literal)
            elif value and value.type == "array":
                tags.extend(item for child in value.named_children if (item := _string_value(source, child)) is not None)
    return list(dict.fromkeys(tags))


def _test_identity(source: bytes, node: Node, aliases: set[str], test_name: str) -> str:
    groups: list[str] = []
    ancestor = node.parent
    while ancestor:
        if ancestor.type == "call_expression":
            function = _text(source, ancestor.child_by_field_name("function"))
            if function.endswith(".describe") and function.split(".", 1)[0] in aliases:
                arguments = ancestor.child_by_field_name("arguments")
                group = _string_value(source, arguments.named_children[0]) if arguments and arguments.named_children else None
                if group:
                    groups.append(group)
        ancestor = ancestor.parent
    return " > ".join([*reversed(groups), test_name])


def discover_playwright_tests(root: Path) -> list[dict]:
    root = root.resolve()
    files = sorted(
        path for path in root.rglob("*")
        if path.is_file()
        and path.suffix.lower() in SOURCE_EXTENSIONS
        and not any(part in IGNORED_DIRECTORIES for part in path.relative_to(root).parts)
        and path.stat().st_size <= MAX_SOURCE_BYTES
    )
    parsed: dict[str, tuple[bytes, Node]] = {}
    imports: dict[str, list[dict]] = defaultdict(list)
    import_bindings: dict[str, dict[str, tuple[str, str | None]]] = defaultdict(dict)
    definitions: dict[str, dict] = {}
    names_by_file: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    classes_by_file: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    playwright_test_aliases: dict[str, set[str]] = defaultdict(set)
    playwright_external_names: dict[str, set[str]] = defaultdict(set)

    for path in files:
        relative = path.resolve().relative_to(root).as_posix()
        source = path.read_bytes()
        tree = _parser(path).parse(source)
        parsed[relative] = (source, tree.root_node)
        for node in tree.root_node.named_children:
            if node.type == "import_statement":
                raw_path = _string_value(source, node.child_by_field_name("source"))
                if raw_path is None:
                    continue
                status, resolved_path = _resolve_module(root, path, raw_path)
                bindings = _import_names(source, node)
                imports[relative].append({
                    "importing_file": relative,
                    "raw_path": raw_path,
                    "imported_names": [local for _, local in bindings],
                    "resolved_path": resolved_path,
                    "resolution_status": status,
                })
                for original, local in bindings:
                    import_bindings[relative][local] = (original, resolved_path)
                    if raw_path == PLAYWRIGHT_MODULE:
                        playwright_external_names[relative].add(local)
                        if original == "test":
                            playwright_test_aliases[relative].add(local)

        for node in _walk(tree.root_node):
            if node.type != "variable_declarator":
                continue
            value = node.child_by_field_name("value")
            if not value or value.type != "call_expression":
                continue
            function = value.child_by_field_name("function")
            arguments = value.child_by_field_name("arguments")
            if _text(source, function) != "require" or not arguments or not arguments.named_children:
                continue
            raw_path = _string_value(source, arguments.named_children[0])
            if raw_path != PLAYWRIGHT_MODULE:
                continue
            pattern = node.child_by_field_name("name")
            local_names = [
                _text(source, child) for child in _walk(pattern)
                if child.type in {"shorthand_property_identifier_pattern", "identifier"}
            ]
            imports[relative].append({
                "importing_file": relative,
                "raw_path": raw_path,
                "imported_names": local_names,
                "resolved_path": None,
                "resolution_status": "EXTERNAL_LIBRARY",
            })
            playwright_external_names[relative].update(local_names)
            if "test" in local_names:
                playwright_test_aliases[relative].add("test")

        for node in _walk(tree.root_node):
            kind = None
            name = None
            parameters = None
            body = None
            class_name = None
            if node.type == "function_declaration":
                kind = "function"
                name = _text(source, node.child_by_field_name("name"))
                parameters = node.child_by_field_name("parameters")
                body = node.child_by_field_name("body")
            elif node.type == "variable_declarator":
                value = node.child_by_field_name("value")
                if value and value.type in {"arrow_function", "function_expression"}:
                    kind = "function"
                    name = _text(source, node.child_by_field_name("name"))
                    parameters = value.child_by_field_name("parameters") or value.child_by_field_name("parameter")
                    body = value.child_by_field_name("body")
            elif node.type == "method_definition":
                parent = node.parent
                while parent and parent.type != "class_declaration":
                    parent = parent.parent
                if parent:
                    class_name = _text(source, parent.child_by_field_name("name"))
                    method_name = _text(source, node.child_by_field_name("name"))
                    kind = "method"
                    name = f"{class_name}.{method_name}"
                    parameters = node.child_by_field_name("parameters")
                    body = node.child_by_field_name("body")
            if kind and name and body:
                reference = _reference(relative, kind, name)
                raw_calls = [_raw_call(source, call, relative, index + 1) for index, call in enumerate(_top_level_calls(body))]
                definitions[reference] = {
                    "callable_reference": reference,
                    "name": name,
                    "source_file": relative,
                    "line_number": node.start_point[0] + 1,
                    "declared_parameters": _parameters(source, parameters),
                    "nested_calls": raw_calls,
                }
                if kind == "method" and class_name:
                    classes_by_file[relative][name].append(reference)
                else:
                    names_by_file[relative][name].append(reference)

    def resolve_definition(source_file: str, name: str) -> list[str]:
        local = names_by_file[source_file].get(name, [])
        if local:
            return local
        binding = import_bindings[source_file].get(name)
        if binding and binding[1]:
            original, imported_file = binding
            return names_by_file[imported_file].get(original, [])
        return []

    def instances(source: bytes, scope: Node) -> dict[str, str]:
        result: dict[str, str] = {}
        for node in _walk(scope):
            if node.type != "variable_declarator":
                continue
            value = node.child_by_field_name("value")
            if not value or value.type != "new_expression":
                continue
            result[_text(source, node.child_by_field_name("name"))] = _text(source, value.child_by_field_name("constructor"))
        return result

    def resolve_call(
        call: dict,
        source_file: str,
        scope_instances: dict[str, str],
        current_definition: str | None = None,
    ) -> dict:
        name = call["name"]
        if "[" in name:
            return {**call, "resolution_status": "DYNAMIC", "keyword_reference": None, "callable_reference": None}
        matches = resolve_definition(source_file, name)
        if "." in name and not matches:
            object_name, method_name = name.rsplit(".", 1)
            class_name = scope_instances.get(object_name)
            if object_name == "this" and current_definition and "." in current_definition:
                class_name = current_definition.split(".", 1)[0]
            if class_name:
                local_class = class_name
                binding = import_bindings[source_file].get(class_name)
                class_file = source_file
                if binding and binding[1]:
                    local_class, class_file = binding
                matches = classes_by_file[class_file].get(f"{local_class}.{method_name}", [])
        if len(matches) == 1:
            return {**call, "resolution_status": "RESOLVED", "keyword_reference": None, "callable_reference": matches[0]}
        if len(matches) > 1:
            return {**call, "resolution_status": "AMBIGUOUS", "keyword_reference": None, "callable_reference": None}
        first = name.split(".", 1)[0]
        external_call = any(name == item or name.startswith(f"{item}(") or name.startswith(f"{item}.")
                            for item in playwright_external_names[source_file])
        if external_call or first in {"page", "expect", "request", "browser", "context"}:
            status = "EXTERNAL_LIBRARY"
        else:
            status = "UNRESOLVED"
        return {**call, "resolution_status": status, "keyword_reference": None, "callable_reference": None}

    resolved_definitions: dict[str, dict] = {}
    for reference, definition in definitions.items():
        source, root_node = parsed[definition["source_file"]]
        scope_instances = instances(source, root_node)
        resolved_definitions[reference] = {
            **definition,
            "nested_calls": [
                resolve_call(call, definition["source_file"], scope_instances, definition["name"])
                for call in definition["nested_calls"]
            ],
        }

    discovered: list[dict] = []
    for relative, (source, root_node) in parsed.items():
        if not relative.endswith(SUPPORTED_SUFFIXES) or not playwright_test_aliases[relative]:
            continue
        scope_instances = instances(source, root_node)
        aliases = playwright_test_aliases[relative]
        for node in _walk(root_node):
            if node.type != "call_expression":
                continue
            function_text = _text(source, node.child_by_field_name("function"))
            root_name = function_text.split(".", 1)[0]
            if root_name not in aliases or function_text.endswith(".describe"):
                continue
            arguments_node = node.child_by_field_name("arguments")
            arguments = arguments_node.named_children if arguments_node else []
            if len(arguments) < 2:
                continue
            test_name = _string_value(source, arguments[0])
            callback = arguments[-1]
            if test_name is None or callback.type not in {"arrow_function", "function_expression"}:
                continue
            body = callback.child_by_field_name("body")
            raw_calls = [
                _raw_call(source, call, relative, index + 1)
                for index, call in enumerate(_top_level_calls(body))
                if _text(source, call.child_by_field_name("function")).split(".", 1)[0] not in aliases
            ]
            steps = [resolve_call(call, relative, scope_instances) for call in raw_calls]
            referenced: dict[str, dict] = {}
            pending = [step["callable_reference"] for step in steps if step["callable_reference"]]
            while pending:
                reference = pending.pop()
                if reference in referenced:
                    continue
                definition = resolved_definitions[reference]
                referenced[reference] = definition
                pending.extend(
                    call["callable_reference"] for call in definition["nested_calls"]
                    if call["callable_reference"] and call["callable_reference"] not in referenced
                )
            discovered.append({
                "framework": "playwright",
                "scanner_version": PLAYWRIGHT_SCANNER_VERSION,
                "test_name": test_name,
                "test_identity": _test_identity(source, node, aliases, test_name),
                "relative_file_path": relative,
                "line_number": node.start_point[0] + 1,
                "tags": _test_tags(source, arguments),
                "steps": steps,
                "resource_imports": [],
                "keyword_references": [],
                "source_imports": imports[relative],
                "callable_references": sorted(referenced.values(), key=lambda item: item["callable_reference"]),
            })
    return discovered
