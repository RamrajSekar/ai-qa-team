# app/services/step_mapper.py

from typing import Dict, Any, Optional
import re

class StepMapper:
    """
    Converts both recorder steps and natural-language steps
    into StepEngine-compatible structured steps.
    """

    # Recorder → structured mapping
    RECORDER_ACTION_MAP = {
        "click": "click",
        "change": "type",
        "input": "type",
        "fill": "type",
        "navigate": "navigate",
        "keydown": "custom",
        "keyup": "custom"
    }

    # Natural language → action mapping
    NL_ACTION_PATTERNS = {
        r"navigate to (.*)": "navigate",
        r"go to (.*)": "navigate",

        r"click (.*)": "click",
        r"press (.*)": "click",
        r"tap (.*)": "click",

        r"type (.*)": "type",
        r"enter (.*)": "type",
        r"input (.*)": "type",

        r"wait for (.*)": "wait_for",

        r"verify (.*)": "assert_text",
        r"ensure (.*)": "assert_text",
        r"check (.*)": "assert_text"
    }

    # Keyword → locator inference
    LOCATOR_MAP = {
        "username": "#username",
        "email": "#email",
        "password": "#password",
        "login": "#login-button",
        "submit": "button[type=submit]",
        "continue": "button:has-text('Continue')"
    }

    # ------------------------------
    # Helpers
    # ------------------------------
    def _infer_locator(self, text: str) -> Optional[str]:
        lower = text.lower()
        for key, sel in self.LOCATOR_MAP.items():
            if key in lower:
                return sel
        return None

    def _infer_action_nl(self, text: str) -> str:
        lower = text.lower()
        for pattern, action in self.NL_ACTION_PATTERNS.items():
            if re.search(pattern, lower):
                return action
        return "custom"

    def _extract_value(self, text: str) -> Optional[str]:
        # Extract anything inside quotes: "abc" or 'abc'
        match = re.search(r"'(.*?)'|\"(.*?)\"", text)
        return match.group(1) or match.group(2) if match else None

    # ------------------------------
    # Recorder Step → Structured Step
    # ------------------------------
    def from_recorder(self, step: Dict[str, Any]) -> Dict:
        event = step.get("event")
        selector = step.get("selector")
        value = step.get("value")

        action = self.RECORDER_ACTION_MAP.get(event, "custom")

        return {
            "step_id": step.get("step_id"),
            "description": step.get("description") or f"{event} {selector}",
            "action": action,
            "locator": selector,
            "value": value,
            "expected": step.get("expected"),
            "category": step.get("category", "Recorder")
        }

    # ------------------------------
    # Natural Language → Structured Step
    # ------------------------------
    def from_nl(self, step: Dict[str, Any]) -> Dict:
        action_text = step.get("action", "")
        expected = step.get("expected", "")
        step_id = step.get("step_id")

        action = self._infer_action_nl(action_text)
        locator = self._infer_locator(action_text)
        value = self._extract_value(action_text)

        return {
            "step_id": step_id,
            "description": action_text,
            "action": action,
            "locator": locator,
            "value": value,
            "expected": expected,
            "category": step.get("category", "General")
        }

    # ------------------------------
    # Main switch / unified entry
    # ------------------------------
    def to_structured(self, step: Dict[str, Any]) -> Dict[str, Any]:
        # Recorder event?
        if "event" in step:
            return self.from_recorder(step)

        # Natural-language action?
        if "action" in step:
            return self.from_nl(step)

        # Unknown → fallback
        return {
            "step_id": step.get("step_id"),
            "description": step.get("description") or "",
            "action": "custom",
            "locator": None,
            "value": None,
            "expected": step.get("expected"),
            "category": step.get("category", "Unknown")
        }
