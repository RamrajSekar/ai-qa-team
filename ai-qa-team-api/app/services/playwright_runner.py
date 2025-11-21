# app/workers/playwright_runner.py

import os
import time
from datetime import datetime, timezone

from playwright.async_api import async_playwright

from app.services.step_engine import StepEngine


def _build_headers(auth_type: str | None, auth_token: str | None, env_vars: dict) -> dict:
    """
    Build global headers injected into every request.
    """
    headers = {
        'X-ENV-VARS': str(env_vars or {}),
    }

    if auth_type == 'bearer' and auth_token:
        headers['Authorization'] = f'Bearer {auth_token}'
    elif auth_type == 'basic' and auth_token:
        headers['Authorization'] = f'Basic {auth_token}'

    return headers


async def _perform_login(page, base_url: str, username: str, password: str):
    """
    Simple login helper – customize per app under test.
    """
    login_url = base_url.rstrip('/') + '/login'
    await page.goto(login_url)

    # Generic selectors – adjust for your AUT
    await page.fill('#username', username)
    await page.fill('#password', password)
    await page.click('#login-button')

    await page.wait_for_timeout(1500)


async def _finalize(db, execution_id: str, start_time: datetime, step_results: list[dict], final_status: str):
    end_time = datetime.now(timezone.utc)
    duration = (end_time - start_time).total_seconds() * 1000

    await db['executions'].update_one(
        {'execution_id': execution_id},
        {
            '$set': {
                'status': final_status,
                'completed_at': end_time.isoformat(),
                'duration_ms': int(duration),
                'step_results': step_results,
                'logs.status': final_status,
            }
        },
    )

    return final_status


async def execute_playwright_test(job: dict, db):
    """
    Executes a test case with the NEW environment+role model.

    job contains:
    - execution_id
    - testcase_id
    - env_type
    - environment  (full env_doc)
    - credentials  (role-specific creds, if any)
    - dataset
    - browser
    - headed
    - runner_type
    - user_identifier
    """

    execution_id = job['execution_id']
    testcase_id = job['testcase_id']

    # Environment model
    env_doc = job.get('environment') or {}
    credentials = job.get('credentials') or {}

    base_url = env_doc.get('base_url')
    api_base_url = env_doc.get('api_base_url')  # not used yet, but reserved
    env_vars = env_doc.get('variables', {}) or {}
    auth_type = env_doc.get('auth_type') or 'none'
    auth_token = env_doc.get('auth_token')

    username = credentials.get('username')
    password = credentials.get('password')

    # Browser
    browser_type = job.get('browser', 'chromium') or 'chromium'
    headed_mode = bool(job.get('headed', False))
    runner_type = job.get('runner_type', 'playwright-local')

    # Safety: disable headed mode for non-local runners
    if runner_type != 'playwright-local':
        headed_mode = False

    # Dataset
    dataset = job.get('dataset') or {}

    # Load testcase definition
    testcase = await db['testcases'].find_one({'testcase_id': testcase_id})
    if not testcase:
        await db['executions'].update_one(
            {'execution_id': execution_id},
            {'$set': {'status': 'error', 'logs.error': 'Test case not found'}},
        )
        return

    steps = testcase.get('steps', [])

    # Mark execution as running
    start_time = datetime.now(timezone.utc)
    await db['executions'].update_one(
        {'execution_id': execution_id},
        {
            '$set': {
                'status': 'running',
                'started_at': start_time.isoformat(),
                'logs.message': 'Execution started',
            }
        },
    )

    step_results: list[dict] = []
    final_status = 'passed'

    print(f'🖥️ Starting Playwright: browser={browser_type}, headed={headed_mode}')
    print(f'🌍 Base URL: {base_url}')
    print(f'👤 Credentials role: {credentials.get("role")}')

    try:
        async with async_playwright() as p:
            browser = await getattr(p, browser_type).launch(headless=not headed_mode)

            context = await browser.new_context(
                base_url=base_url,
                extra_http_headers=_build_headers(auth_type, auth_token, env_vars),
            )

            page = await context.new_page()

            # Optional login
            if username and password and base_url:
                try:
                    await _perform_login(page, base_url, username, password)
                    print(f'🔐 Login success: {username}')
                except Exception as e:
                    print(f'❌ Login failed: {e}')
                    step_results.append(
                        {
                            'step_id': 'login',
                            'status': 'failed',
                            'message': f'Login failed: {e}',
                        }
                    )
                    final_status = 'failed'
                    await browser.close()
                    return await _finalize(db, execution_id, start_time, step_results, final_status)

            # Step Engine
            engine = StepEngine(
                page=page,
                base_url=base_url,
                dataset=dataset,
                env_vars=env_vars,
            )

            for step in steps:
                step_start = time.time()
                step_id = step.get('step_id', 'unknown')

                try:
                    await engine.perform(step)

                    step_results.append(
                        {
                            'step_id': step_id,
                            'status': 'passed',
                            'duration_ms': int((time.time() - step_start) * 1000),
                        }
                    )

                except Exception as e:
                    os.makedirs('screenshots', exist_ok=True)
                    screenshot_path = f'screenshots/{execution_id}_{step_id}.png'
                    await page.screenshot(path=screenshot_path)

                    step_results.append(
                        {
                            'step_id': step_id,
                            'status': 'failed',
                            'message': str(e),
                            'duration_ms': int((time.time() - step_start) * 1000),
                            'screenshot_path': screenshot_path,
                        }
                    )

                    final_status = 'failed'
                    break

            await browser.close()

    except Exception as e:
        final_status = 'error'
        step_results.append(
            {
                'step_id': 'internal',
                'status': 'failed',
                'message': f'Internal runner error: {str(e)}',
            }
        )

    return await _finalize(db, execution_id, start_time, step_results, final_status)
