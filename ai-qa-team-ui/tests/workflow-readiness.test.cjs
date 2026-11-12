// Intercepted UI/API/auth only. No real MongoDB, BrowserStack or model traffic.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright');

test('saved admission restores and readiness controls never imply a business pass', async t => {
  const base = process.env.FEATURE_UI_URL || 'http://127.0.0.1:3123';
  const browser = await chromium.launch({ headless: true, channel: 'msedge' });
  t.after(() => browser.close());
  const context = await browser.newContext();
  await context.addCookies([{ name: 'access_token', value: 'fixture-only', url: base }]);
  let workerEnabled = true;
  let run = { run_id: 'a'.repeat(64), manifest_digest: 'b'.repeat(64), state: 'prepared', execution_ready: false, reason: 'GENERAL_WORKER_NOT_ENABLED' };
  let queued = 0;
  await context.route('http://feature-api.test/**', async route => {
    const request = route.request(), url = new URL(request.url());
    const headers = { 'access-control-allow-origin': base, 'access-control-allow-credentials': 'true',
      'access-control-allow-headers': 'content-type', 'access-control-allow-methods': 'GET,POST,OPTIONS' };
    if (request.method() === 'OPTIONS') return route.fulfill({ status: 204, headers });
    let json = [];
    if (url.pathname === '/features') json = { test_generation: true, reusable_workflows: true, approved_visual_run_admission: true, approved_workflow_worker: workerEnabled };
    if (url.pathname === '/auth/me') json = { user: { email: 'fixture@example.test', name: 'Fixture', onboarding: { onboarding_status: 'completed' }, subscription: { usage: {}, limits: {} } } };
    if (url.pathname === '/projects') json = [{ project_id: 'P1', name: 'Fixture', current_user_role: 'ADMIN' }];
    if (url.pathname === '/projects/P1') json = { project_id: 'P1', name: 'Fixture', current_user_role: 'ADMIN' };
    if (url.pathname === '/testcases/project-list') json = [{ testcase_id: 'TC1', scenario_id: 'SC1', title: 'Readiness fixture', status: 'draft', steps: [] }];
    if (url.pathname.endsWith('/visual-specifications/cases/TC1')) json = { version: { version_id: 'c'.repeat(32), status: 'approved', steps: [{ action: 'assert_text', expected: 'Synthetic confirmation' }], story_id: 'ST1', acceptance_criteria_snapshot: 'Show synthetic confirmation' }, review_required: false };
    if (url.pathname === '/environments') json = [{ env_id: 'ENV1', env_type: 'qa', credentials: [] }];
    if (url.pathname.endsWith('/cases/TC1/runs') || url.pathname.endsWith('/runs/' + run.run_id)) json = run;
    if (url.pathname.endsWith('/browser-preflight')) { assert.equal(request.method(), 'POST'); queued++; json = run = { ...run, state: 'queued', reason: 'BROWSER_PREFLIGHT_QUEUED' }; }
    if (url.pathname.endsWith('/cancel')) json = run = { ...run, state: 'cancelled', verdict: 'cancelled', reason: null };
    return route.fulfill({ headers, json });
  });
  const page = await context.newPage(); page.setDefaultTimeout(45000); page.setDefaultNavigationTimeout(90000);
  await page.goto(base + '/projects/P1/testcases', { waitUntil: 'domcontentloaded' });
  await page.getByText('Visual execution specification', { exact: true }).click();
  const queue = page.getByRole('button', { name: 'Check isolated browser readiness only' });
  await queue.click(); assert.equal(queued, 1);
  await page.getByRole('button', { name: 'Cancel admission or readiness check' }).click();
  await page.getByRole('status').filter({ hasText: 'cancelled' }).waitFor();
  run = { ...run, state: 'completed', verdict: 'blocked', browser_readiness: 'ready', cleanup_confirmed: true, reason: 'ACTION_RUNTIME_NOT_ENABLED' };
  await page.getByRole('button', { name: 'Refresh readiness status' }).click();
  await page.getByText('Browser readiness: ready · Verdict: blocked. Cleanup: confirmed.', { exact: true }).waitFor();
  assert.equal(await queue.count(), 0);
  workerEnabled = false;
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.getByText('Visual execution specification', { exact: true }).click();
  await page.getByText('Browser readiness: ready · Verdict: blocked. Cleanup: confirmed.', { exact: true }).waitFor();
  assert.equal(await queue.count(), 0);
});
