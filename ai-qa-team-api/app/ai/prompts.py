import json
from app.services.legacy_prompt_defaults import LEGACY_PROMPT_DEFAULTS
from app.services.prompt_templates import render_template


def generate_testcase_prompt(scenario, *, template=None):
    """Preserved compatibility helper; there are currently no runtime callers."""
    return render_template(template or LEGACY_PROMPT_DEFAULTS['LEGACY_TESTCASE']['system_prompt'],
                           {"scenario_json": json.dumps(scenario, indent=2)})
