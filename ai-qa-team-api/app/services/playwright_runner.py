from playwright.async_api import async_playwright
from datetime import datetime, timezone
import time
import os

ENVIRONMENTS = {
    "dev": "https://dev.example.com",
    "qa": "https://google.com",
    "staging": "https://staging.example.com"
}

BROWSERS = {
    "chromium": "chromium",
    "chrome": "chromium",
    "firefox": "firefox",
    "webkit": "webkit"
}


async def execute_playwright_test(job: dict, db):
    """
    Execute a test case using Playwright inside the worker.
    """

    execution_id = job["execution_id"]
    testcase_id = job["testcase_id"]
    browser_type = job["browser"]
    headed_mode = job["headed"]
    environment = job["environment"]
    runner_type = job.get("runner_type", "playwright-local")

    # SAFETY RULE
    if runner_type != "playwright-local":
        headed_mode = False

    # Load the test case
    testcase = await db["testcases"].find_one({"testcase_id": testcase_id})
    if not testcase:
        await db["executions"].update_one(
            {"execution_id": execution_id},
            {"$set": {"status": "error", "logs": {"error": "Test case not found"}}},
        )
        return

    steps = testcase.get("steps", [])

    # Mark execution as RUNNING
    start_time = datetime.now(timezone.utc)
    await db["executions"].update_one(
        {"execution_id": execution_id},
        {
            "$set": {
                "status": "running",
                "started_at": start_time.isoformat(),
                "logs": {"message": "Execution started"},
            }
        }
    )

    step_results = []
    print(f"🖥️ Launching browser {browser_type}. Headed: {headed_mode}")
    
    try:
        async with async_playwright() as p:
            # DEBUG_SHOW_BROWSER = True
            browser = await getattr(p, browser_type).launch(headless=not DEBUG_SHOW_BROWSER)
            # browser = await getattr(p, browser_type).launch(headless=not headed_mode)
            context = await browser.new_context()
            page = await context.new_page()

            for step in steps:
                step_start = time.time()

                try:
                    action = step.get("action", "").lower()
                    locator = step.get("locator")
                    value = step.get("value")

                    # ----------------------------------
                    # UI NAVIGATION
                    # ----------------------------------
                    if action.startswith("navigate"):
                        base_url = ENVIRONMENTS.get(environment.lower(), "https://example.com")

                        # Step may have its own path or override
                        step_url = step.get("url") or value
                        # Rules:
                        # 1. If step defines a full URL → use it
                        # 2. If step defines a relative path → join with base_url
                        # 3. Else → open base_url
                        if step_url:
                            if step_url.startswith("http"):
                                url = step_url
                            else:
                                # build relative navigation
                                url = base_url.rstrip("/") + "/" + step_url.lstrip("/")
                        else:
                            url = base_url

                        print(f"🌐 Navigating to: {url}")
                        await page.goto(url)
                    # ----------------------------------
                    # CLICK
                    # ----------------------------------
                    elif "click" in action and locator:
                        await page.click(locator)

                    # ----------------------------------
                    # TYPE INPUT
                    # ----------------------------------
                    elif ("enter" in action or "type" in action) and locator:
                        await page.fill(locator, value or "")

                    # ----------------------------------
                    # ASSERTIONS
                    # ----------------------------------
                    elif "verify" in action or "assert" in action:
                        expected = step.get("expected", "")
                        text = await page.inner_text("body")
                        assert expected.lower() in text.lower()

                    # Unknown action
                    else:
                        raise Exception(f"Unsupported step action: {action}")

                    step_results.append({
                        "step_id": step["step_id"],
                        "status": "passed",
                        "duration_ms": int((time.time() - step_start) * 1000),
                    })

                except Exception as e:
                    screenshot_path = f"screenshots/{execution_id}_{step['step_id']}.png"
                    await page.screenshot(path=screenshot_path)

                    step_results.append({
                        "step_id": step["step_id"],
                        "status": "failed",
                        "message": str(e),
                        "duration_ms": int((time.time() - step_start) * 1000),
                        "screenshot_path": screenshot_path,
                    })

                    # Stop execution after failure
                    final_status = "failed"
                    break
            else:
                final_status = "passed"

            await browser.close()

    except Exception as e:
        final_status = "error"
        step_results.append({
            "step_id": "internal",
            "status": "error",
            "message": str(e),
        })

    # Save results
    end_time = datetime.now(timezone.utc)
    duration = (end_time - start_time).total_seconds() * 1000

    await db["executions"].update_one(
        {"execution_id": execution_id},
        {
            "$set": {
                "status": final_status,
                "completed_at": end_time.isoformat(),
                "duration_ms": int(duration),
                "step_results": step_results,
                "logs": {"status": final_status},
            }
        }
    )

    return final_status
