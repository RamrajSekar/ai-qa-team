import hashlib
import re


MAX_PROVENANCE_DEPTH = 8
MAX_PROVENANCE_NODES = 256


def parameter_name(value: str) -> str:
    value = value.strip()
    robot = re.search(r"[$@&%]\{([^}]+)\}", value)
    if robot:
        return robot.group(1)
    value = value.split("=", 1)[0].split(":", 1)[0].strip()
    return re.sub(r"[^A-Za-z0-9_$]", " ", value).split()[-1] if value else value


def expression_kind(expression: str) -> str:
    value = expression.strip()
    if re.fullmatch(r"(?:['\"`].*['\"`]|-?\d+(?:\.\d+)?|true|false|null|None)", value, re.S):
        return "LITERAL"
    if "process.env" in value or "System.getenv" in value or re.search(r"%\{[^}]+\}", value):
        return "ENV_ACCESS_EXPRESSION"
    if re.search(r"\w+\s*\(.*\)$", value, re.S):
        return "CALL_RESULT"
    if "." in value:
        return "MEMBER_REFERENCE"
    if re.fullmatch(r"[$@&%]?\{?[A-Za-z_$][\w$]*\}?", value):
        return "VARIABLE_REFERENCE"
    return "UNKNOWN_EXPRESSION"


def build_value_provenance(
    test_identity: str,
    steps: list[dict],
    definitions: list[dict],
    bindings: list[dict] | None = None,
) -> list[dict]:
    """Build a bounded framework-neutral evidence graph from adapter-supplied static facts."""
    records: list[dict] = []
    definition_map = {item.get("callable_reference") or item.get("keyword_reference"): item for item in definitions}
    binding_items = bindings or []
    visited: set[str] = set()

    def add(kind: str, expression: str, source_file: str, line: int | None, status: str = "RESOLVED",
            sources: list[str] | None = None, callable_reference: str | None = None,
            parameter: str | None = None) -> str:
        if len(records) >= MAX_PROVENANCE_NODES:
            return ""
        seed = f"{test_identity}|{len(records)}|{kind}|{source_file}|{line}|{expression}"
        record_id = "PV" + hashlib.sha256(seed.encode()).hexdigest()[:20].upper()
        records.append({
            "provenance_id": record_id, "expression": expression, "evidence_kind": kind,
            "source_file": source_file, "line_number": line, "resolution_status": status,
            "source_ids": [item for item in (sources or []) if item],
            "callable_reference": callable_reference, "parameter_name": parameter,
        })
        return record_id

    def origin(expression: str, scope: str, source_file: str, line: int | None,
               parameter_sources: dict[str, str], forced_kind: str | None = None,
               depth: int = 0, binding_path: frozenset[tuple] = frozenset()) -> str:
        if depth > MAX_PROVENANCE_DEPTH or len(records) >= MAX_PROVENANCE_NODES:
            return add("TRAVERSAL_LIMIT", expression, source_file, line, "PARTIAL")
        kind = forced_kind or expression_kind(expression)
        if kind == "VARIABLE_REFERENCE":
            name = parameter_name(expression)
            if name in parameter_sources:
                return add("PARAMETER", expression, source_file, line, sources=[parameter_sources[name]], parameter=name)
            candidates = [item for item in binding_items if item["scope"] == scope and item["name"] == name
                          and (line is None or item.get("line_number") is None or item["line_number"] <= line)]
            if candidates:
                latest_line = max(item.get("line_number") or 0 for item in candidates)
                latest = ([item for item in candidates if item.get("ambiguous")]
                          if any(item.get("ambiguous") for item in candidates)
                          else [item for item in candidates if (item.get("line_number") or 0) == latest_line])
                source_ids = []
                for item in latest:
                    binding_key = (scope, item["name"], item.get("line_number"), item["expression"])
                    if binding_key in binding_path:
                        source_ids.append(add("TRAVERSAL_LIMIT", item["expression"], item["source_file"],
                                              item.get("line_number"), "PARTIAL"))
                    else:
                        source_ids.append(origin(
                            item["expression"], scope, item["source_file"], item.get("line_number"),
                            parameter_sources, item.get("origin_kind"), depth + 1, binding_path | {binding_key},
                        ))
                status = "AMBIGUOUS" if len(latest) > 1 or any(item.get("ambiguous") for item in latest) else "RESOLVED"
                evidence = latest[0].get("evidence_kind", "ASSIGNMENT")
                binding_id = add(evidence, name, source_file, latest_line, status, source_ids)
                return add("VARIABLE_REFERENCE", expression, source_file, line, status, [binding_id])
            return add("VARIABLE_REFERENCE", expression, source_file, line, "UNRESOLVED")
        if kind == "MEMBER_REFERENCE":
            base = expression.strip().split(".", 1)[0]
            base_id = origin(base, scope, source_file, line, parameter_sources, depth=depth + 1,
                             binding_path=binding_path)
            return add(kind, expression, source_file, line, sources=[base_id])
        return add(kind, expression, source_file, line, "DYNAMIC" if kind == "UNKNOWN_EXPRESSION" else "RESOLVED")

    def visit_calls(calls: list[dict], scope: str, parameter_sources: dict[str, str], depth: int) -> None:
        if depth > MAX_PROVENANCE_DEPTH or len(records) >= MAX_PROVENANCE_NODES:
            add("TRAVERSAL_LIMIT", scope, calls[0]["source_file"] if calls else "", None, "PARTIAL")
            return
        for call in calls:
            argument_ids = []
            for expression in call.get("arguments", []):
                origin_id = origin(expression, scope, call["source_file"], call.get("line_number"), parameter_sources)
                argument_ids.append(add("ARGUMENT", expression, call["source_file"], call.get("line_number"), sources=[origin_id],
                                        callable_reference=call.get("callable_reference") or call.get("keyword_reference")))
            reference = call.get("callable_reference") or call.get("keyword_reference")
            if not reference or reference not in definition_map or reference in visited:
                continue
            visited.add(reference)
            definition = definition_map[reference]
            parameters = definition.get("declared_parameters", definition.get("declared_arguments", []))
            aligned = {parameter_name(value): argument_ids[index] for index, value in enumerate(parameters) if index < len(argument_ids)}
            visit_calls(definition.get("nested_calls", []), reference, aligned, depth + 1)

    visit_calls(steps, test_identity, {}, 0)
    if len(records) >= MAX_PROVENANCE_NODES:
        records = records[:MAX_PROVENANCE_NODES - 1]
        add("TRAVERSAL_LIMIT", test_identity, steps[0]["source_file"] if steps else "", None, "PARTIAL")
    return records
