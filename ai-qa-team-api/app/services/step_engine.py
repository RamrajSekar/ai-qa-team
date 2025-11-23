from typing import Any, Dict, Optional

from playwright.async_api import Page, expect


class StepEngine:
    """
    Executes structured TestStep-like dictionaries on a Playwright Page.

    Expected step shape (aligned with TestStep):

    {
        "step_id": "STEP001",
        "description": "User enters username",
        "action": "type",             # navigate | click | type | assert_text | wait_for | custom
        "locator": "#username",
        "value": "{username}",        # supports dataset / credentials / env_vars binding
        "expected": "Welcome Ramraj",
        "url": "/login",
        "category": "Input"
    }
    """

    def __init__(
        self,
        *,
        page: Page,
        base_url: Optional[str],
        dataset: Optional[Dict[str, Any]] = None,
        env_vars: Optional[Dict[str, Any]] = None,
        credentials: Optional[Dict[str, Any]] = None,
        timeout_ms: int = 10_000,
    ) -> None:
        self.page = page
        self.base_url = base_url or ''
        self.dataset = dataset or {}
        self.env_vars = env_vars or {}
        self.credentials = credentials or {}
        self.timeout_ms = timeout_ms

    # -----------------------------------------------------
    # Value / URL resolution helpers
    # -----------------------------------------------------
    def _resolve_placeholder(self, key: str) -> Optional[str]:
        """
        Resolve {key} from dataset, then credentials, then env_vars.
        """
        if key in self.dataset:
            return str(self.dataset[key])
        if key in self.credentials:
            return str(self.credentials[key])
        if key in self.env_vars:
            return str(self.env_vars[key])
        return None

    def _resolve_value(self, raw: Optional[str]) -> Optional[str]:
        if raw is None:
            return None
        if isinstance(raw, str) and raw.startswith('{') and raw.endswith('}'):
            key = raw.strip('{}')
            resolved = self._resolve_placeholder(key)
            return resolved if resolved is not None else raw
        return raw

    def _resolve_url(self, step: Dict[str, Any]) -> str:
        """
        If step.url is absolute -> use as is.
        If relative -> join with base_url.
        If not present but value is URL-ish -> use value.
        Otherwise -> base_url.
        """
        url = step.get('url') or step.get('value')

        if isinstance(url, str) and url.startswith('http'):
            return url

        if isinstance(url, str):
            return self.base_url.rstrip('/') + '/' + url.lstrip('/')

        # fallback: just base_url
        return self.base_url

    # -----------------------------------------------------
    # Main execution entry
    # -----------------------------------------------------
    async def perform(self, step: Dict[str, Any]) -> None:
        action = (step.get('action') or '').lower()

        if action == 'navigate':
            await self._do_navigate(step)
        elif action == 'click':
            await self._do_click(step)
        elif action == 'type':
            await self._do_type(step)
        elif action == 'assert_text':
            await self._do_assert_text(step)
        elif action == 'wait_for':
            await self._do_wait_for(step)
        elif action == 'custom':
            await self._do_custom(step)
        else:
            raise ValueError(f'Unsupported action: {step.get("action")}')

    # -----------------------------------------------------
    # Action handlers
    # -----------------------------------------------------
    async def _do_navigate(self, step: Dict[str, Any]) -> None:
        url = self._resolve_url(step)
        await self.page.goto(url, wait_until='networkidle')

    async def _do_click(self, step: Dict[str, Any]) -> None:
        locator = step.get('locator')
        if not locator:
            raise ValueError('click requires a locator')

        await self.page.click(locator)

    async def _do_type(self, step: Dict[str, Any]) -> None:
        locator = step.get('locator')
        if not locator:
            raise ValueError('type requires a locator')

        raw_value = step.get('value')
        value = self._resolve_value(raw_value) or ''

        await self.page.fill(locator, value)

    async def _do_assert_text(self, step: Dict[str, Any]) -> None:
        """
        Assert that expected text is present either in:
        - specific locator (if provided), or
        - full page body.
        """
        expected = self._resolve_value(step.get('expected') or '')
        if not expected:
            raise ValueError('assert_text requires an expected value')

        locator = step.get('locator')

        if locator:
            element = self.page.locator(locator)
            await expect(element).to_contain_text(expected, timeout=self.timeout_ms)
        else:
            body_text = await self.page.inner_text('body')
            if expected.lower() not in body_text.lower():
                raise AssertionError(f"Expected text '{expected}' not found in page body.")

    async def _do_wait_for(self, step: Dict[str, Any]) -> None:
        locator = step.get('locator')
        if not locator:
            raise ValueError('wait_for requires a locator')

        timeout = step.get('timeout_ms') or self.timeout_ms
        await self.page.wait_for_selector(locator, timeout=timeout)

    async def _do_custom(self, step: Dict[str, Any]) -> None:
        """
        Placeholder for future custom actions.
        For now, we just raise to mark it as unsupported.
        """
        raise NotImplementedError('Custom actions not implemented yet in StepEngine.')
