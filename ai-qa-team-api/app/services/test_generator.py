def generate_playwright_test(scenario):
    title = scenario["title"]
    steps = scenario["steps"]

    lines = [
        f"test('{title}', async ({'{ page }'}) => {{"
    ]

    for s in steps:
        action = s.get("action", "")
        lines.append(f"  // {action}")

    lines.append("});")

    return "\n".join(lines)
