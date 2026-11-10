"""Real PNG matching and assertion tests with a remote WebDriver double."""
from io import BytesIO
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from PIL import Image

from app.services import synthetic_visual_browser as runner


def screenshot(button, status, *, duplicate=False):
    frame = Image.new('RGB', (984, 649), 'white')
    frame.paste(button, (430, 130))
    if duplicate:
        frame.paste(button, (90, 130))
    if status:
        frame.paste(status, (430, 205))
    png = BytesIO()
    frame.save(png, 'PNG')
    return png.getvalue(), frame


class SyntheticBrowserTests(unittest.IsolatedAsyncioTestCase):
    async def exercise(self, *, expected='Draft saved', status='Draft saved', duplicate=False,
                       stale=False, lost_click=False, cancelled=False, color_index=0):
        with patch.object(runner.secrets, 'choice', side_effect=lambda options: options[color_index]):
            url, button, color, status_tiles = runner.fixture()
        before = screenshot(button, status_tiles['Ready'], duplicate=duplicate)
        after = screenshot(button, status_tiles.get(status))
        browser = runner.RemoteSyntheticBrowser('fixture', 'fixture')
        self.addAsyncCleanup(browser.client.aclose)
        browser.open = AsyncMock()
        browser.screenshot = AsyncMock(side_effect=[before, after if stale else before, after])
        click_calls = []

        async def command(method, path, payload=None):
            if path == 'url' and method == 'GET':
                return url
            if path == 'actions':
                click_calls.append(payload)
                if lost_click:
                    raise httpx.ReadTimeout('synthetic response lost')

        browser.command = command
        checkpoint = AsyncMock(side_effect=[None, None, RuntimeError('Cancelled')] if cancelled else None)
        with patch.object(runner, 'fixture', return_value=(url, button, color, status_tiles)):
            if cancelled:
                with self.assertRaises(RuntimeError):
                    await browser.execute('Save draft', expected, checkpoint)
                return None, click_calls
            result = await browser.execute('Save draft', expected, checkpoint)
            return result, click_calls

    async def test_correct_and_incorrect_expectations_are_independent_of_click(self):
        for index, expected, verdict in ((0, 'Draft saved', 'passed'), (1, 'Wrong text', 'failed')):
            result, calls = await self.exercise(expected=expected, color_index=index)
            self.assertEqual(result[:2], (verdict, 'Draft saved'))
            self.assertEqual(len(calls), 1)
            point = calls[0]['actions'][0]['actions'][0]
            self.assertEqual((point['x'], point['y']), (530, 156))
            self.assertTrue(result[2].startswith(b'\x89PNG'))

    async def test_ambiguous_stale_and_cancelled_targets_never_click(self):
        for options, reason in (({'duplicate': True}, 'BUTTON_NOT_UNIQUE'), ({'stale': True}, 'OBSERVATION_STALE')):
            result, calls = await self.exercise(**options)
            self.assertEqual((result[0], result[3]), ('needs_review', reason))
            self.assertFalse(calls)
        _, calls = await self.exercise(cancelled=True)
        self.assertFalse(calls)

    async def test_missing_assertion_evidence_and_uncertain_click_do_not_pass_or_replay(self):
        for options, reason in (({'status': None}, 'ASSERTION_EVIDENCE_UNREADABLE'),
                                ({'lost_click': True}, 'CLICK_OUTCOME_UNCERTAIN')):
            result, calls = await self.exercise(**options)
            self.assertEqual((result[0], result[3]), ('needs_review', reason))
            self.assertEqual(len(calls), 1)
