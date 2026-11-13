// Intercepted UI workflow. No BrowserStack, live API, or MongoDB.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright');

test('select a case, approve, preview, admit, reload, start and cancel', async t => {
  const base = process.env.FEATURE_UI_URL || 'http://127.0.0.1:3123';
  const browser = await chromium.launch({ headless: true, channel: 'msedge' });
  t.after(() => browser.close());
  const context = await browser.newContext();
  await context.addCookies([{ name: 'access_token', value: 'synthetic-fixture', url: base }]);
  const admissionPath = '/projects/P1/approved-visual-runs';
  let approval = null;
  let run = null;
  let startBody;
  let featureEnabled = true;
  let executionUiEnabled = true;
  let executionDataReads = 0;
  let admissionReads = 0;
  await context.route('http://feature-api.test/**', async route => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    const headers = {
      'access-control-allow-origin': base, 'access-control-allow-credentials': 'true',
      'access-control-allow-headers': 'content-type', 'access-control-allow-methods': 'GET,POST,OPTIONS',
    };
    if (request.method() === 'OPTIONS') return route.fulfill({ status: 204, headers });
    let json = [];
    if (path === '/features') json = { automation_execution_ui: true, test_generation: true, test_execution_ui: executionUiEnabled, approved_visual_run_admission: featureEnabled,
      approved_visual_run_execution: featureEnabled };
    if (path === '/auth/me') json = { user: { email: 'synthetic@example.test', name: 'Synthetic User',
      onboarding: { onboarding_status: 'completed' }, subscription: { plan: 'free', usage: {}, limits: {} } } };
    if (path === '/projects/P1') json = { project_id: 'P1', name: 'Synthetic project', current_user_role: 'ADMIN' };
    if (path === '/testcases/testcases') json = [{ project_id: 'P1', testcase_id: 'TC1', title: 'Save draft' }];
    if (path === '/environments') json = [{ project_id: 'P1', env_id: 'ENV1', name: 'Example staging' }];
    if (path.startsWith(admissionPath)) admissionReads++;
    if (["/projects/P1", "/testcases/testcases", "/environments"].includes(path)) executionDataReads++;
    if (path === admissionPath + '/testcases/TC1') json = { approval, latest_run: run };
    if (path.endsWith('/approve')) {
      approval = { ...request.postDataJSON(), version_id: 'a'.repeat(32), story_id: 'ST1' };
      json = approval;
    }
    if (path.endsWith('/preview')) json = { test: approval, environment_id: 'ENV1', preview_digest: 'b'.repeat(64) };
    if (path === admissionPath) {
      startBody = request.postDataJSON();
      run = { test: approval, environment_id: 'ENV1', preview_digest: 'b'.repeat(64), run_id: 'c'.repeat(64), state: 'admitted' };
      json = run;
    }
    if (path === admissionPath + '/' + run?.run_id) json = run;
    if (path.endsWith('/start')) json = run = { ...run, state: 'running' };
    if (path.endsWith('/cancel')) json = run = { ...run, state: 'cancelled', verdict: 'cancelled' };
    return route.fulfill({ headers, json });
  });
  const page = await context.newPage();
  page.setDefaultTimeout(30000);
  page.setDefaultNavigationTimeout(90000);
  await page.goto(base + '/projects/P1/test-execution', { waitUntil: 'domcontentloaded' });
  const panel = page.getByRole('region', { name: 'Approved visual run' });
  await panel.getByLabel('Test case').selectOption('TC1');
  await panel.getByLabel('Visible button label').fill('Save draft');
  await panel.getByLabel('Expected visible text').fill('Draft saved');
  await panel.getByRole('button', { name: 'Approve synthetic specification' }).click();
  await panel.getByLabel('Saved environment').selectOption('ENV1');
  await panel.getByRole('button', { name: 'Preview synthetic run' }).click();
  await panel.getByText('Target: Controlled synthetic sample', { exact: false }).waitFor();
  await panel.getByText('Verify “Draft saved”.').waitFor();
  await panel.getByRole('button', { name: 'Admit synthetic run' }).click();
  await panel.getByRole('status').filter({ hasText: 'Admitted' }).waitFor();
  assert.deepEqual(Object.keys(startBody).sort(), ['approved_test_version_id', 'environment_id', 'idempotency_key', 'preview_digest']);
  assert.match(startBody.idempotency_key, /^[a-f0-9]{32}$/);
  await page.reload({ waitUntil: 'domcontentloaded' });
  await panel.getByLabel('Test case').selectOption('TC1');
  await panel.getByRole('status').filter({ hasText: 'Admitted' }).waitFor();
  await panel.getByRole('button', { name: 'Start synthetic browser run' }).click();
  await panel.getByRole('status').filter({ hasText: 'Running' }).waitFor();
  await panel.getByRole('button', { name: 'Refresh status' }).click();
  await panel.getByRole('button', { name: 'Cancel browser run' }).click();
  await panel.getByRole('status').filter({ hasText: 'Cancelled' }).waitFor();

  featureEnabled = false;
  const previousReads = admissionReads;
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.getByText('Test execution is currently hidden.').waitFor();
  assert.equal(await panel.count(), 0);
  assert.equal(admissionReads, previousReads);
  featureEnabled = true;
  executionUiEnabled = false;
  const previousDataReads = executionDataReads;
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.getByText('This feature is disabled.').waitFor();
  assert.equal(executionDataReads, previousDataReads);
  assert.equal(admissionReads, previousReads);
  await page.goto(base + '/projects/P1');
  await page.getByRole('heading', { name: 'Recent Testcases' }).waitFor();
  assert.equal(await panel.count(), 0);
});
