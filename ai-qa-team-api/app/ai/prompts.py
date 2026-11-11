import json

def generate_testcase_prompt(scenario):
    return f"""
You are an automation test generator. Convert the scenario into a structured test case.

STRICT RULES:
- OUTPUT JSON ONLY.
- DO NOT write code.
- Steps must be executable by a Playwright StepEngine:
  * action must be one of: navigate | click | type | fill | assert_text | wait | noop
  * locator must be a valid CSS/XPath selector OR null for navigation/assert_text
  * value may be static text OR a dataset variable like {{username}}
- Each step must include:
  step_id, description, action, locator, value

Here is the scenario:

{json.dumps(scenario, indent=2)}

Return JSON in this format:

{{
  "title": "<string>",
  "description": "<string>",
  "steps": [
    {{
      "step_id": "STEP001",
      "description": "<Natural Language>",
      "action": "<action>",
      "locator": "<selector or null>",
      "value": "<value or null>"
    }}
  ]
}}
"""