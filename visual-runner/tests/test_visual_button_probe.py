import base64
from pathlib import Path
import struct
import tempfile
import unittest

from linux.visual_button_probe import run

BOUNDS = (260, 260, 250, 58)


def frame(marker):
    header = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'
    return base64.b64encode(header + struct.pack('>II', 800, 600) + marker * 9).decode()


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
        browser = BrowserDouble([frame(b'a'), frame(b'a'), frame(b'b')])
        proposals = []

        def propose(png, width, height):
            proposals.append((png, width, height))
            return {'found': True, 'candidate_count': 1, 'x': 388, 'y': 467}

        with tempfile.TemporaryDirectory() as folder:
            run(browser, Path(folder), BOUNDS, propose)
            self.assertEqual(list(Path(folder).iterdir()), [Path(folder, 'button-after-click.png')])
        self.assertEqual(proposals, [(base64.b64decode(frame(b'a')), 800, 600)])
        self.assertEqual(browser.clicks, [(310, 280)])

    def test_uncertain_invalid_and_stale_proposals_never_click(self):
        for count, x, refresh, expected in (
            (2, 300, b'a', 'VISUAL_TARGET_UNCERTAIN'),
            (1, 1000, b'a', 'VISUAL_COORDINATES_INVALID'),
            (1, True, b'a', 'VISUAL_COORDINATES_INVALID'),
            (1, 388, b'b', 'VISUAL_OBSERVATION_STALE'),
        ):
            with self.subTest(expected=expected, x=x), tempfile.TemporaryDirectory() as folder:
                browser = BrowserDouble([frame(b'a'), frame(refresh)])
                with self.assertRaisesRegex(RuntimeError, expected):
                    run(browser, Path(folder), BOUNDS, lambda *_: {
                        'found': True, 'candidate_count': count, 'x': x, 'y': 467,
                    })
                self.assertEqual(browser.clicks, [])
                self.assertEqual(list(Path(folder).iterdir()), [])

    def test_in_viewport_proposal_outside_button_retains_evidence_without_clicking(self):
        browser = BrowserDouble([frame(b'a')])
        with tempfile.TemporaryDirectory() as folder:
            evidence = Path(folder)
            with self.assertRaisesRegex(RuntimeError, 'VISUAL_TARGET_OUTSIDE_FIXTURE'):
                run(browser, evidence, BOUNDS, lambda *_: {
                    'found': True, 'candidate_count': 1, 'x': 100, 'y': 100,
                })
            self.assertEqual((evidence / 'button-target-rejected.png').read_bytes(), base64.b64decode(frame(b'a')))
        self.assertEqual(browser.clicks, [])
