import time
from playwright.async_api import Page

class StepEngine:
    """
    Central executor for all steps with:
    - Action normalizer
    - Dataset/variable interpolation
    - Navigation, click, type, assertions
    """

    def __init__(self, page: Page, base_url: str, dataset: dict, env_vars: dict):
        print(f"🔄 StepEngine LOADED (with action normalizer) {base_url}")
        self.page = page
        self.base_url = base_url
        self.dataset = dataset or {}
        self.env_vars = env_vars or {}

    # -------------------------------------------------------------
    # ACTION NORMALIZER
    # -------------------------------------------------------------
    ACTION_MAP = {
        "navigate to test url": "navigate",
        "navigate to": "navigate",
        "navigate_url": "navigate",
        "go to url": "navigate",
        "open url": "navigate",
        "launch": "navigate",
        "open browser": "navigate",
        "goto": "navigate",
    }

    # -------------------------------------------------------------
    # UTILITY — VAR INTERPOLATION
    # -------------------------------------------------------------
    def _resolve_value(self, value):
        if isinstance(value, str) and value.startswith("{") and value.endswith("}"):
            key = value.strip("{}")
            return self.dataset.get(key) or self.env_vars.get(key)
        return value

    # -------------------------------------------------------------
    # MAIN STEP PERFORMER
    # -------------------------------------------------------------
    async def perform(self, step: dict):
        """
        Executes a single step.

        Expected step fields:
        - action
        - locator
        - value
        - url
        - expected
        """
        raw_action = step.get("action", "").strip().lower()

        # Normalize action
        action = self.ACTION_MAP.get(raw_action, raw_action)

        locator = step.get("locator")
        value = self._resolve_value(step.get("value"))
        step_url = step.get("url")

        # Debug log
        print(f"➡️ Executing action: {raw_action} → {action}")

        # ---------------------------------------------------------
        # NAVIGATION
        # ---------------------------------------------------------
        if action == "navigate":
            return await self._perform_navigation(step_url, value)

        # ---------------------------------------------------------
        # CLICK
        # ---------------------------------------------------------
        if action == "click" or "click" in action and locator:
            return await self.page.click(locator)

        # ---------------------------------------------------------
        # TYPE / FILL
        # ---------------------------------------------------------
        if action in ["type", "input", "enter", "fill"] or "type" in action:
            if not locator:
                raise ValueError("Missing locator for type action")
            return await self.page.fill(locator, value or "")

        # ---------------------------------------------------------
        # ASSERTIONS
        # ---------------------------------------------------------
        if action in ["assert", "verify", "check"]:
            expected = step.get("expected")
            return await self._perform_assertion(expected)

        # ---------------------------------------------------------
        # WAIT
        # ---------------------------------------------------------
        if action.startswith("wait"):
            ms = int(value) if value else 500
            await self.page.wait_for_timeout(ms)
            return

        # ---------------------------------------------------------
        # UNSUPPORTED — THROW CLEAN ERROR
        # ---------------------------------------------------------
        raise ValueError(f"Unsupported action: {raw_action}")

    # -------------------------------------------------------------
    # INTERNAL EXECUTION HELPERS
    # -------------------------------------------------------------
    async def _perform_navigation(self, step_url, value):
        """
        Handles navigation logic with:
        - Full URL override
        - Relative paths
        - Dataset-backed URLs
        """
        # dataset variable interpolation
        url_value = self._resolve_value(value)

        # Full URL?
        if step_url and step_url.startswith("http"):
            url = step_url

        # Relative navigation
        elif step_url:
            url = self.base_url.rstrip("/") + "/" + step_url.lstrip("/")

        # Navigate using dataset URL
        elif url_value and isinstance(url_value, str) and url_value.startswith("http"):
            url = url_value

        # Default → base_url
        else:
            url = self.base_url

        print(f"🌐 Navigating to: {url}")
        await self.page.goto(url)

    async def _perform_assertion(self, expected):
        body_text = await self.page.inner_text("body")

        if not expected:
            raise ValueError("Missing 'expected' for assertion step")

        if expected.lower() not in body_text.lower():
            raise AssertionError(f"Expected '{expected}' not found on page")

        print(f"✔ Assertion passed: {expected}")
