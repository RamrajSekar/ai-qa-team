import json


def generate_playwright_test(scenario):
    title = scenario["title"]
    steps = scenario["steps"]

    lines = [
        f"test({json.dumps(title)}, async ({{ page }}) => {{"
    ]

    for s in steps:
        action = s.get("action", "")
        lines.extend(f"  // {line}" for line in action.splitlines())

    lines.append("});")

    return "\n".join(lines)
