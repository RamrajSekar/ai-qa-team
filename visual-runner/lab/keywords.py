"""Fixed server-owned fixture keywords. No public general-purpose execution API."""
from robot.api.deco import keyword, library
from functools import wraps


def diagnose(method):
    @wraps(method)
    def wrapped(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except Exception as exc:
            # Robot absorbs keyword exceptions into its result. Preserve only a
            # fixed error class/code, never its message or traceback.
            codes = {'BROWSER_SESSION_LOST', 'WEBDRIVER_TIMEOUT', 'WEBDRIVER_COMMAND_FAILED'}
            code = str(exc) if str(exc) in codes else type(exc).__name__
            if code not in codes | {'ReadTimeout', 'ConnectError', 'PermissionError', 'FileNotFoundError'}:
                code = 'RUNNER_INTERNAL_ERROR'
            self.context.state.setdefault('diagnostic_code', code)
            self.context.publish()
            raise
    return wrapped


@library(auto_keywords=False)
class SmokeLibrary:
    def __init__(self, context):
        self.context = context

    @keyword('Open Controlled Sample')
    @diagnose
    def open_sample(self):
        self.context.browser.navigate_sample()
        self.context.snapshot('01-open')

    @keyword('Fill Synthetic Form')
    @diagnose
    def fill_form(self):
        b = self.context.browser
        b.click(180, 150)
        b.keys('Sample Tester')
        b.click(180, 250)
        b.keys('\ue0033')  # Backspace existing 1, then quantity 3
        b.click(180, 350)
        b.keys('\ue015\ue007')  # ArrowDown, Enter: Plus
        self.context.snapshot('02-filled')

    @keyword('Confirm Synthetic Order')
    @diagnose
    def confirm(self):
        b = self.context.browser
        b.keys('\ue004\ue00f')  # Tab to button, End scrolls to document end
        self.context.pause(1)
        b.keys('\ue007')  # focused button activation
        self.context.snapshot('03-confirmed')

    @keyword('Hold For Lab Inspection')
    @diagnose
    def hold(self):
        self.context.pause(8)
