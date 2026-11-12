// Intercepted UI check. No MongoDB, model provider, or BrowserStack traffic.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright');

test('story scenario approval creates a selectable visual-run test case and hides bug reproduction', async t => {
  const base = process.env.FEATURE_UI_URL || 'http://127.0.0.1:3123';
  const browser = await chromium.launch({ headless: true, channel: 'msedge' });
  t.after(() => browser.close());
  const context = await browser.newContext();
  await context.addCookies([{ name: 'access_token', value: 'synthetic-fixture', url: base }]);
  const story = { project_id: 'P1', story_id: 'ST1', title: 'Save draft', acceptance_criteria: 'Draft saved appears.' };
  const scenarios = [], testcases = [];
  let bugEnabled = false;
  let storiesUnavailable = true;
  await context.route('http://feature-api.test/**', async route => {
    const request = route.request();
    const url = new URL(request.url());
    const headers = {
      'access-control-allow-origin': base, 'access-control-allow-credentials': 'true',
      'access-control-allow-headers': 'content-type', 'access-control-allow-methods': 'GET,POST,PUT,OPTIONS',
    };
    if (request.method() === 'OPTIONS') return route.fulfill({ status: 204, headers });
    let json = [];
    if (url.pathname === '/features') json = { story_management: true, scenario_generation: true,
      test_generation: true, test_execution_ui: true, approved_visual_run_admission: true, bug_reproduction_ui: bugEnabled };
    if (url.pathname === '/auth/me') json = { user: { email: 'fixture@example.test', name: 'Fixture',
      onboarding: { onboarding_status: 'completed' }, subscription: { usage: {}, limits: {} } } };
    if (url.pathname === '/projects/P1') json = { project_id: 'P1', name: 'Fixture project', current_user_role: 'ADMIN' };
    if (url.pathname === '/stories/ST1') json = story;
    if (url.pathname === '/stories') {
      if (storiesUnavailable) return route.fulfill({ status: 503, headers, json: { detail: 'Fixture unavailable' } });
      json = [story];
    }
    if (url.pathname === '/scenarios') {
      if (request.method() === 'POST') {
        const body = request.postDataJSON();
        assert.equal(body.steps[0].expected, 'Draft saved');
        json = { ...body, scenario_id: 'SC1', project_id: 'P1', approved: false };
        scenarios.push(json);
      } else json = scenarios;
    }
    if (url.pathname === '/scenarios/SC1/approve') json = scenarios[0] = { ...scenarios[0], approved: true };
    if (url.pathname === '/testcases/generate') {
      assert.equal(url.searchParams.get('scenario_id'), 'SC1');
      assert.equal(url.searchParams.get('project_id'), 'P1');
      assert.equal(scenarios[0].approved, true);
      testcases.push({ testcase_id: 'TC1', project_id: 'P1', title: 'Draft scenario' });
      json = testcases;
    }
    if (url.pathname === '/testcases/testcases') json = testcases;
    return route.fulfill({ headers, json });
  });
  const page = await context.newPage();
  page.setDefaultTimeout(30000);
  page.setDefaultNavigationTimeout(90000);
  await page.goto(base + '/projects/P1/stories', { waitUntil: 'domcontentloaded' });
  await page.getByRole('alert').filter({ hasText: 'Could not load stories (HTTP 503)' }).waitFor();
  storiesUnavailable = false;
  await page.getByRole('button', { name: 'Try again' }).click();
  await page.getByRole('link', { name: 'Save draft', exact: true }).click();
  await page.getByRole('button', { name: 'Add Scenario' }).click();
  await page.getByLabel('Title', { exact: true }).fill('Draft scenario');
  await page.getByRole('button', { name: 'Add step' }).click();
  await page.getByLabel('Action 1').fill('Click Save draft');
  await page.getByLabel('Expected result 1').fill('Draft saved');
  await page.getByRole('button', { name: 'Save Scenario' }).click();
  await page.getByRole('button', { name: 'View', exact: true }).click();
  assert.equal(await page.getByRole('button', { name: 'Generate test case' }).count(), 0);
  await page.getByRole('button', { name: 'Approve scenario' }).click();
  await page.getByRole('button', { name: 'Generate test case' }).click();
  await page.getByRole('link', { name: 'Open Project Overview' }).click();
  await page.goto(base + '/projects/P1/test-execution');
  await page.getByRole('region', { name: 'Approved visual run' }).getByRole('option', { name: 'Draft scenario' }).waitFor({ state: 'attached' });
  assert.equal(await page.getByRole('link', { name: 'AI Generator' }).count(), 0);
  assert.equal(await page.getByRole('link', { name: 'Reproduce Bug' }).count(), 0);
  await page.goto(base + '/projects/P1/reproduce');
  await page.getByRole('status').filter({ hasText: 'This feature is disabled' }).waitFor();
  bugEnabled = true;
  await page.reload();
  await page.getByRole('heading', { name: 'Reproduce Bug' }).waitFor();
});
