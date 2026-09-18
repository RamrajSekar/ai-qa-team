import hashlib


_ORIGIN_RULES = {
    "LITERAL": ("STATIC_INTERNAL", "STATIC_LITERAL_ORIGIN"),
    "CALL_RESULT": ("GENERATED_RUNTIME", "CALL_RESULT_ORIGIN"),
    "ENV_ACCESS_EXPRESSION": ("ENVIRONMENT", "ENV_ACCESS_ORIGIN"),
}


def build_value_ownership(test_identity: str, provenance: list[dict]) -> list[dict]:
    """Classify argument ownership solely from one contract's canonical provenance graph."""
    by_id = {record["provenance_id"]: record for record in provenance}

    def trace(provenance_id: str, path: frozenset[str] = frozenset()) -> tuple[set[str], set[str], set[str], set[str]]:
        if provenance_id in path:
            return {"UNKNOWN"}, {"TRAVERSAL_LIMIT"}, {provenance_id}, {"PARTIAL"}
        record = by_id.get(provenance_id)
        if record is None:
            return {"UNKNOWN"}, {"UNRESOLVED_ORIGIN"}, set(), {"UNRESOLVED"}

        evidence_ids = {provenance_id}
        status = record.get("resolution_status", "UNRESOLVED")
        kind = record.get("evidence_kind")
        statuses = {status}

        if kind in _ORIGIN_RULES:
            ownership, reason = _ORIGIN_RULES[kind]
            return {ownership}, {reason}, evidence_ids, statuses
        if kind == "TRAVERSAL_LIMIT":
            return {"UNKNOWN"}, {"TRAVERSAL_LIMIT"}, evidence_ids, {"PARTIAL"}
        if kind == "UNKNOWN_EXPRESSION" or status == "DYNAMIC":
            return {"UNKNOWN"}, {"DYNAMIC_ORIGIN"}, evidence_ids, {"DYNAMIC"}

        source_ids = record.get("source_ids", [])
        if not source_ids:
            return {"UNKNOWN"}, {"UNRESOLVED_ORIGIN"}, evidence_ids, {"UNRESOLVED"}

        categories: set[str] = set()
        reasons: set[str] = set()
        child_statuses: set[str] = set()
        for source_id in source_ids:
            child_categories, child_reasons, child_evidence, child_status = trace(source_id, path | {provenance_id})
            categories.update(child_categories)
            reasons.update(child_reasons)
            evidence_ids.update(child_evidence)
            child_statuses.update(child_status)
        statuses.update(child_statuses)
        if kind == "MEMBER_REFERENCE" and categories == {"GENERATED_RUNTIME"}:
            reasons.add("MEMBER_ORIGIN")
            statuses.add("PARTIAL")
        return categories, reasons, evidence_ids, statuses

    def final_status(categories: set[str], statuses: set[str]) -> str:
        if len(categories) > 1:
            return "AMBIGUOUS"
        if "AMBIGUOUS" in statuses:
            return "AMBIGUOUS"
        if "DYNAMIC" in statuses:
            return "DYNAMIC"
        if "PARTIAL" in statuses:
            return "PARTIAL"
        if "UNRESOLVED" in statuses:
            return "UNRESOLVED"
        return "RESOLVED"

    results = []
    for target in provenance:
        if target.get("evidence_kind") != "ARGUMENT":
            continue
        categories, reasons, evidence_ids, statuses = trace(target["provenance_id"])
        concrete = categories - {"UNKNOWN"}
        if len(concrete) == 1 and categories == concrete:
            ownership = next(iter(concrete))
            reason = sorted(reasons)[0]
        elif len(concrete) == 1 and categories == concrete | {"UNKNOWN"}:
            ownership = "UNKNOWN"
            reason = "AMBIGUOUS_ORIGINS"
        elif len(concrete) > 1:
            ownership = "UNKNOWN"
            reason = "CONFLICTING_OWNERSHIP"
        else:
            ownership = "UNKNOWN"
            reason = sorted(reasons)[0] if reasons else "UNRESOLVED_ORIGIN"
        status = final_status(categories, statuses)
        if ownership == "UNKNOWN" and len(categories) > 1:
            status = "AMBIGUOUS"
        seed = f"{test_identity}|{target['provenance_id']}|{ownership}|{reason}"
        results.append({
            "ownership_id": "OWN" + hashlib.sha256(seed.encode()).hexdigest()[:20].upper(),
            "provenance_id": target["provenance_id"],
            "ownership": ownership,
            "status": status,
            "evidence_ids": sorted(evidence_ids),
            "reason_code": reason,
            "source_file": target["source_file"],
            "line_number": target.get("line_number"),
        })
    return results
