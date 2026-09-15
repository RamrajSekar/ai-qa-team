// Run against an isolated Next dev server with NEXT_PUBLIC_API_URL=http://feature-api.test.
// PLAYWRIGHT_MODULE_PATH can point to an existing Playwright installation.
const { test, before, after } = require('node:test');
const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright');
const baseURL = process.env.FEATURE_UI_URL || 'http://127.0.0.1:3107';
const apiOrigin = 'http://feature-api.test';
let browser;
const defaults = {
  story_management: false, scenario_generation: false, test_generation: false,
  recorder: false, native_execution: false, jira_trigger: false,
  failure_diagnostics: false, self_healing: false, playwright_repo_adapter: false,
  selenium_repo_adapter: false, repository_discovery: true, test_registry: true,
  test_data_generation: true,
};
const project = { project_id: 'P1', id: 'P1', name: 'Flag test project',
  created_at: '2026-01-01', agent_identities: {} };
const user = { email: 'tester@example.com', name: 'Tester',
  onboarding: { onboarding_status: 'completed' },
  subscription: { plan: 'free', usage: {}, limits: {} } };

before(async () => {
  browser = await chromium.launch({ headless: true, channel: process.env.PLAYWRIGHT_CHANNEL || 'msedge' });
});
after(async () => { if (browser) await browser.close(); });

async function fixture(t, options = {}) {
  const context = await browser.newContext();
  t.after(() => context.close());
  await context.addCookies([{ name: 'access_token', value: 'test-only', url: baseURL }]);
  const calls = [];
  const errors = [];
  const page = await context.newPage();
  page.setDefaultNavigationTimeout(90000);
  page.on('pageerror', (error) => errors.push(error.message));
  await context.route(`${apiOrigin}/**`, async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (request.method() === 'OPTIONS') {
      return route.fulfill({ status: 204, headers: {
        'access-control-allow-origin': baseURL, 'access-control-allow-credentials': 'true',
        'access-control-allow-headers': 'content-type', 'access-control-allow-methods': 'GET,POST,PATCH,DELETE,PUT',
      } });
    }
    calls.push(url.pathname);
    let body = [];
    let status = 200;
    if (url.pathname === '/features') {
      if (options.waitForFeatures) await options.waitForFeatures;
      status = options.failed ? 503 : 200;
      body = options.invalid ? { recorder: 'true' } : { ...defaults, ...options.flags };
    } else if (url.pathname === '/auth/me') body = { user: options.user || user };
    else if (url.pathname === '/projects') body = [project];
    else if (url.pathname === '/projects/P1') body = project;
    else if (url.pathname === '/stories/S1') body = {
      story_id: 'S1', project_id: 'P1', title: 'Existing story', created_at: '2026-01-01',
    };
    else if (url.pathname.startsWith('/stories')) body = [];
    else if (url.pathname === '/execute') body = [{ execution_id: 'EX1', status: 'passed', project_id: 'P1' }];
    await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body), headers: {
      'access-control-allow-origin': baseURL, 'access-control-allow-credentials': 'true',
    } });
  });
  return { page, calls, errors };
}

async function visible(page, text) {
  await page.getByText(text, { exact: true }).first().waitFor({ state: 'visible', timeout: 60000 });
}
function noLegacyCalls(calls) {
  assert.deepEqual(calls.filter((path) => /^\/(stories|scenarios|recorder|testcases|integrations)(\/|$)/.test(path)), []);
}

test('disabled direct story URL does not mount pages or fetch legacy APIs', async (t) => {
  const { page, calls, errors } = await fixture(t);
  await page.goto(`${baseURL}/projects/P1/stories/S1`);
  await visible(page, 'This feature is disabled.');
  noLegacyCalls(calls);
  assert.equal(await page.getByRole('link', { name: 'Stories', exact: true }).count(), 0);
  assert.equal(await page.getByRole('link', { name: 'AI Generator', exact: true }).count(), 0);
  assert.deepEqual(errors, []);
});

test('project overview skips disabled APIs while retaining environments and execution history', async (t) => {
  const { page, calls, errors } = await fixture(t);
  await page.goto(`${baseURL}/projects/P1`);
  await visible(page, 'Execution #EX1');
  noLegacyCalls(calls);
  assert.ok(calls.includes('/environments'));
  assert.ok(calls.includes('/execute'));
  assert.equal(await page.getByText('Recent Stories', { exact: true }).count(), 0);
  assert.equal(await page.getByRole('button', { name: 'Agent Settings', exact: true }).count(), 0);
  assert.deepEqual(errors, []);
});

test('Story can be enabled while Recorder and Scenario remain independently disabled', async (t) => {
  const { page, calls, errors } = await fixture(t, { flags: { story_management: true } });
  await page.goto(`${baseURL}/projects/P1/stories/S1`);
  await visible(page, 'Existing story');
  assert.ok(calls.includes('/stories/S1'));
  assert.deepEqual(calls.filter((path) => /^\/(recorder|scenarios)/.test(path)), []);
  assert.equal(await page.getByRole('button', { name: 'Record Steps' }).count(), 0);
  assert.equal(await page.getByText('Scenarios', { exact: true }).count(), 0);
  assert.deepEqual(errors, []);
});

test('disabled page stays unmounted while feature request is pending', async (t) => {
  let release;
  const waitForFeatures = new Promise((resolve) => { release = resolve; });
  const { page, calls } = await fixture(t, { waitForFeatures });
  try {
    await page.goto(`${baseURL}/projects/P1/stories`, { waitUntil: 'domcontentloaded' });
    await visible(page, 'Loading features...');
    noLegacyCalls(calls);
  } finally { release(); }
  await visible(page, 'This feature is disabled.');
  noLegacyCalls(calls);
});

for (const mode of ['failed', 'invalid']) {
  test(`${mode} feature response fails closed without blocking core project UI`, async (t) => {
    const { page, calls } = await fixture(t, { [mode]: true });
    await page.goto(`${baseURL}/projects/P1/stories`);
    await visible(page, 'Feature availability could not be loaded. Reload to try again.');
    noLegacyCalls(calls);
    await page.goto(`${baseURL}/projects/P1`);
    await visible(page, 'Execution #EX1');
    noLegacyCalls(calls);
  });
}


test('onboarding skips disabled import and proceeds to completion', async (t) => {
  const onboardingUser = { ...user, onboarding: {
    onboarding_status: 'in_progress', current_step: 3, context: { project_id: 'P1' },
  } };
  const { page, calls } = await fixture(t, { user: onboardingUser });
  await page.goto(`${baseURL}/dashboard`);
  await visible(page, 'Test import is currently disabled. You can continue setting up your project.');
  await page.getByRole('button', { name: 'Continue', exact: true }).click();
  await page.getByRole('button', { name: 'Go to Dashboard', exact: true }).waitFor();
  noLegacyCalls(calls);
  assert.equal(await page.getByText('Import Tests (Optional)', { exact: true }).count(), 0);
});
