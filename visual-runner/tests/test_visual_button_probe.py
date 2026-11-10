import base64
from io import BytesIO
from pathlib import Path
import tempfile
import unittest

from PIL import Image, ImageDraw

from linux.visual_button_probe import BUTTON_RGB, run

BOUNDS = (260, 260, 250, 58)


def frame(*positions):
    image = Image.new('RGB', (800, 600), 'white')
    for left, top in positions:
        ImageDraw.Draw(image).rectangle((left, top, left + 247, top + 55), fill=BUTTON_RGB)
    output = BytesIO()
    image.save(output, format='PNG')
    return base64.b64encode(output.getvalue()).decode()


class BrowserDouble:
    sample_url = 'data:text/html,synthetic'

    def __init__(self, frames):
        self.frames = iter(frames)
        self.clicks = []

    def command(self, method, suffix):
        return {
            'screenshot': lambda: next(self.frames),
            'url': lambda: self.sample_url,
            'title': lambda: 'Synthetic button clicked' if self.clicks else 'QA Lab sample',
        }[suffix]()

    def click(self, x, y):
        self.clicks.append((x, y))


class VisualButtonProbeTest(unittest.TestCase):
    def test_clear_target_clicks_once_and_keeps_only_post_click_evidence(self):
        before = frame((261, 261))
        browser = BrowserDouble([before, before, frame()])
        proposals = []

        def propose(png):
            with Image.open(BytesIO(png)) as crop:
                proposals.append(crop.size)
            return {'confirmed': True}

        with tempfile.TemporaryDirectory() as folder:
            run(browser, Path(folder), BOUNDS, propose)
            self.assertEqual(list(Path(folder).iterdir()), [Path(folder, 'button-after-click.png')])
        self.assertEqual(proposals, [(248, 56)])
        self.assertEqual(browser.clicks, [(385, 289)])

    def test_uncertain_and_stale_proposals_never_click(self):
        before = frame((261, 261))
        for initial, decision, expected in (
            (frame(), True, 'VISUAL_TARGET_UNCERTAIN'),
            (frame((261, 261), (261, 400)), True, 'VISUAL_TARGET_UNCERTAIN'),
            (before, False, 'VISUAL_TARGET_UNCERTAIN'),
            (before, True, 'VISUAL_OBSERVATION_STALE'),
        ):
            with self.subTest(expected=expected, decision=decision), tempfile.TemporaryDirectory() as folder:
                browser = BrowserDouble([initial, frame()])
                with self.assertRaisesRegex(RuntimeError, expected):
                    run(browser, Path(folder), BOUNDS, lambda _: {'confirmed': decision})
                self.assertEqual(browser.clicks, [])

    def test_in_viewport_proposal_outside_button_retains_evidence_without_clicking(self):
        before = frame((80, 60))
        browser = BrowserDouble([before])
        with tempfile.TemporaryDirectory() as folder:
            evidence = Path(folder)
            with self.assertRaisesRegex(RuntimeError, 'VISUAL_TARGET_OUTSIDE_FIXTURE'):
                run(browser, evidence, BOUNDS, lambda _: self.fail('Rejected geometry called the model'))
            self.assertEqual((evidence / 'button-target-rejected.png').read_bytes(), base64.b64decode(before))
        self.assertEqual(browser.clicks, [])
