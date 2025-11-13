def generate_playwright_test(scenario: dict) -> str:
    steps = scenario.get("steps", [])
    lines = [
        "from playwright.sync_api import sync_playwright",
        "",
        "def test_scenario():",
        "    with sync_playwright() as p:",
        "        browser = p.chromium.launch(headless=False)",
        "        page = browser.new_page()",
    ]

    for step in steps:
        action = step.get("action")
        target = step.get("target")
        value = step.get("value")

        if action == "goto":
            lines.append(f'        page.goto("{value}")')
        elif action == "click":
            lines.append(f'        page.click("{target}")')
        elif action == "fill":
            lines.append(f'        page.fill("{target}", "{value}")')

    lines.append("        browser.close()")
    return "\n".join(lines)
