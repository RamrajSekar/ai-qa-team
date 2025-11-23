from datetime import datetime, timezone
import time
import os
from typing import Any, Dict, Optional

from playwright.async_api import async_playwright

from app.services.step_engine import StepEngine


def _build_headers(auth_type: Optional[str], auth_token: Optional[str], env_vars: Dict[str, Any]) -> Dict[str, str]:
    """
    Build global headers injected into every request.
    """
    headers: Dict[str, str] = {
        'X-ENV-VARS': str(env_vars)
    }

    if auth_type == 'bearer' and auth_token:
        headers['Authorization'] = f'Bearer {auth_token}'
    elif auth_type == 'basic' and auth_token:
        headers['Authorization'] = f'Basic {auth_token}'

    return headers


async def _perform_login(page, base_url: str, username: str, password: str) -> None:
    """
    Simple login flow for demo.
    You can customize selectors later.
    """
    login_url = base_url.rstrip('/') + '/login'
    await page.goto(login_url)

    await page.fill('#username', username)
    await page.fill('#password', password)
    await page.click('#login-button')

    await page.wait_for_timeout(1500)


async def _finalize(db, execution_id: str, start_time: datetime, step_results: list, final_status: str) -> str:
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
    Executes a test case with the NEW environment-role model.

    job contains:
      - execution_id
      - testcase_id
      - env_type
      - environment: full environment_doc
      - credentials: selected role credentials
      - dataset
      - browser
      - headed
      - runner_type
    """

    execution_id = job['execution_id']
    testcase_id = job['testcase_id']

    env_doc: Dict[str, Any] = job.get('environment') or {}
    credentials: Dict[str, Any] = job.get('credentials') or {}

    base_url = env_doc.get('base_url')
    api_base_url = env_doc.get('api_base_url')
    env_vars = env_doc.get('variables', {}) or {}
    auth_type = env_doc.get('auth_type', 'none')
    auth_token = env_doc.get('auth_token') if env_doc.get('auth_token') != 'none' else None

    username = credentials.get('username')
    password = credentials.get('password')

    browser_type = job.get('browser', 'chromium')
    headed_mode = job.get('headed', False)
    runner_type = job.get('runner_type', 'playwright-local')

    # Safety: disable headed when not local
    if runner_type != 'playwright-local':
        headed_mode = False

    dataset = job.get('dataset') or {}
    timeout_ms = env_doc.get('default_timeout_ms', 10_000)

    # Load testcase and steps
    testcase = await db['testcases'].find_one({'testcase_id': testcase_id})
    if not testcase:
        await db['executions'].update_one(
            {'execution_id': execution_id},
            {'$set': {'status': 'error', 'logs.error': 'Testcase not found'}},
        )
        return 'error'

    steps = testcase.get('steps', [])

    # Mark RUNNING
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

    step_results = []
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

            # Optional: auto-login
            if username and password and base_url:
                try:
                    await _perform_login(page, base_url, username, password)
                    print(f'🔐 Login success for user {username}')
                except Exception as e:
                    print(f'❌ Login failure: {e}')
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

            # Step engine
            engine = StepEngine(
                page=page,
                base_url=base_url,
                dataset=dataset,
                env_vars=env_vars,
                credentials=credentials,
                timeout_ms=timeout_ms,
            )

            # Execute each step
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
                    screenshot_path = f'screenshots/{execution_id}_{step_id}.png'
                    os.makedirs('screenshots', exist_ok=True)
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
