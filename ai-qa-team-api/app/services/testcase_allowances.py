"""Effective test-case entitlements. Resolving policy never writes or resets usage."""
from copy import deepcopy
from fastapi import HTTPException

TIERS = ("basic", "medium", "advanced")


def testcase_allowances(subscription):
    limits = subscription.get("limits", {})
    if not any(key in limits for key in ("testcases_limit", *(f"testcases_{tier}_limit" for tier in TIERS))):
        raise HTTPException(503, "Test case allowance is not configured.")
    total = limits.get("testcases_limit")
    tiers = {tier: limits.get(f"testcases_{tier}_limit") for tier in TIERS}
    if any(value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 0)
           for value in (total, *tiers.values())):
        raise HTTPException(503, "Test case allowance is not configured.")
    free = subscription.get("plan") == "free"
    shared = free or subscription.get("entitlement_version") == 2 or subscription.get("plan") in ("team", "business")
    versioned = subscription.get("entitlement_version") == 2 or subscription.get("plan") in ("team", "business")
    if versioned and (not isinstance(total, int) or isinstance(total, bool) or total < 0):
        raise HTTPException(503, "Shared test case allowance is not configured.")
    if not versioned and total in (None, 0) and any(value is not None for value in tiers.values()):
        # Old Free subscriptions used only their Basic cap, with an unused total.
        # Do not sum three shared caps and accidentally turn 10 into 30.
        total = tiers["basic"] if free and tiers["basic"] is not None else sum(value or 0 for value in tiers.values())
    return {"testcases_limit": total, **{f"testcases_{tier}_limit": total if shared else tiers[tier] for tier in TIERS}}


def effective_subscription(subscription):
    result = deepcopy(subscription)
    if (result.get("plan") in ("free", "team", "business") or result.get("entitlement_version") == 2) and any(key.startswith("testcases_") for key in result.get("limits", {})):
        result["limits"].update(testcase_allowances(result))
        result["testcase_complexity_policy"] = "SHARED_TOTAL"
    return result
