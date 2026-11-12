// Intercepted UI verification only: no normal login, Mongo, AI or remote browser calls.
const { test, before, after } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright');
const base = process.env.FEATURE_UI_URL || 'http://127.0.0.1:3123';
const evidence = process.env.UI_EVIDENCE_DIR || path.resolve(__dirname, '../../tmp/design-ui-evidence');
let browser;
before(async () => { fs.mkdirSync(evidence, { recursive: true }); browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL || 'msedge', headless: true }); });
after(async () => { await browser?.close(); });

async function fixture(t, { step, owner = true, authenticated = true } = {}) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, colorScheme: 'light' });
  t.after(() => context.close());
  if (authenticated) await context.addCookies([{ name: 'access_token', value: 'synthetic-ui-fixture', url: base }]);
  const user = { name: 'QA reviewer', email: 'fixture@example.test', platform_role: owner ? 'OWNER' : 'NONE',
    onboarding: { onboarding_status: step ? 'in_progress' : 'completed', current_step: step || 5, context: { project_id: step === 1 ? null : 'P1' } },
    subscription: { plan: 'free', usage: {}, limits: {} } };
  const project = { project_id: 'P1', name: 'Customer portal', current_user_role: 'ADMIN', created_at: '2026-11-01' };
  const story = { project_id: 'P1', story_id: 'ST1', title: 'Save draft', acceptance_criteria: 'Show Draft saved.', created_at: '2026-11-01' };
  const definition = { prompt_key: 'LEGACY_STORY_SCENARIOS', name: 'Legacy Story Scenarios', description: 'Legacy compatibility instructions.', output_contract: 'LegacyScenarioSteps[]', template_variables: ['title'],
    active: { source: 'CODE_FALLBACK', resolved_version: 'CODE_DEFAULT_V1', system_prompt: 'Generate coverage for {{title}}. Return JSON.' } };
  const versions = [];
  let rejectProject = true;
  const calls = [];
  await context.route('http://feature-api.test/**', async route => {
    const req = route.request(), url = new URL(req.url());
    const headers = { 'access-control-allow-origin': base, 'access-control-allow-credentials': 'true', 'access-control-allow-headers': 'content-type', 'access-control-allow-methods': 'GET,POST,PATCH,PUT,OPTIONS' };
    if (req.method() === 'OPTIONS') return route.fulfill({ status: 204, headers });
    calls.push([req.method(), url.pathname]);
    let json = [];
    if (url.pathname === '/features') json = { product_knowledge: true, story_analysis: true, story_management: true, scenario_generation: true, test_generation: true };
    if (url.pathname === '/auth/me') {
      if (!authenticated) return route.fulfill({ status: 401, headers, json: { detail: 'Not authenticated' } });
      json = { user };
    }
    if (url.pathname === '/projects') {
      if (req.method() === 'POST') {
        if (rejectProject) { rejectProject = false; return route.fulfill({ status: 503, json: { detail: 'Synthetic project service unavailable.' }, headers }); }
        user.onboarding.context.project_id = 'P1'; user.onboarding.current_step = 2; json = project;
      } else json = [project];
    }
    if (url.pathname === '/projects/P1') json = project;
    if (url.pathname === '/stories' || url.pathname === '/stories/project-overview') json = [story];
    if (url.pathname === '/scenarios/project-list') json = [{ scenario_id: 'SC1', story_id: 'ST1', project_id: 'P1', title: 'Save draft coverage', steps: [], approved: false }];
    if (url.pathname === '/testcases/project-list') json = [{ testcase_id: 'TC1', scenario_id: 'SC1', project_id: 'P1', title: 'Save a draft', steps: [{ action: 'Click Save', expected: 'Draft saved' }], status: 'draft' }];
    if (url.pathname === '/projects/P1/knowledge') json = { sources: [], versions: [], active_version_id: null };
    if (url.pathname.startsWith('/environments')) json = [{ env_id: 'ENV1', env_type: 'qa', base_url: 'https://qa.example.test', project_id: 'P1', credentials: [], variables: {}, created_at: '2026-11-01' }];
    if (url.pathname === '/platform-admin/prompts') json = [definition];
    if (url.pathname === '/platform-admin/prompts/LEGACY_STORY_SCENARIOS') json = definition;
    if (url.pathname === '/platform-admin/prompts/LEGACY_STORY_SCENARIOS/versions') {
      if (req.method() === 'POST') { json = { version: 1, status: 'DRAFT', system_prompt: definition.active.system_prompt, created_by: user.email, created_at: '2026-11-12' }; versions.push(json); }
      else json = versions;
    }
    if (url.pathname.endsWith('/versions/1') && req.method() === 'PATCH') { versions[0].system_prompt = req.postDataJSON().system_prompt; json = versions[0]; }
    if (url.pathname.endsWith('/versions/1/activate')) { versions[0].status = 'ACTIVE'; definition.active = { ...versions[0], source: 'DATABASE', resolved_version: 1 }; json = versions[0]; }
    await route.fulfill({ json, headers });
  });
  const page = await context.newPage();
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  t.after(() => assert.deepEqual(errors, []));
  page.setDefaultTimeout(30000); page.setDefaultNavigationTimeout(90000);
  return { page, calls };
}
async function fits(page) {
  await page.waitForFunction(() => document.documentElement.scrollWidth <= innerWidth);
  const dialog = page.getByRole('dialog');
  if (await dialog.count()) {
    await page.waitForFunction(() => [...document.querySelectorAll('[role="dialog"]')].filter(el => !el.closest('[aria-hidden="true"]')).every(el => { const r = el.getBoundingClientRect(); return r.left >= 0 && r.right <= innerWidth && r.width > 0; })).catch(async error => {
      console.log('Synthetic dialog geometry:', await dialog.evaluateAll(elements => elements.map(el => ({ rect: el.getBoundingClientRect().toJSON(), width: getComputedStyle(el).width, minWidth: getComputedStyle(el).minWidth, viewport: innerWidth })))); throw error;
    });
  }
}
async function shot(page, name) { await page.screenshot({ path: path.join(evidence, name + '.png'), fullPage: true }); }

test('onboarding supports failure recovery, five steps, keyboard focus and nested environment dialog', async t => {
  const { page, calls } = await fixture(t, { step: 1 });
  await page.goto(base + '/onboarding');
  const dialog = page.getByRole('dialog', { name: 'Set up your QA workspace' });
  await dialog.waitFor();
  assert.equal(await dialog.locator('.onboarding-stepper li').count(), 5);
  assert.equal(await dialog.locator('[aria-current="step"]').innerText(), '1\nProject');
  await page.getByLabel('Project name', { exact: true }).fill('Synthetic QA project');
  await page.getByRole('button', { name: 'Create project & continue' }).click();
  await page.getByRole('alert').filter({ hasText: 'Synthetic project service unavailable.' }).waitFor();
  assert.equal(await dialog.getByRole('button', { name: 'Create project & continue' }).isEnabled(), true);
  await shot(page, 'onboarding-project');
  await page.getByRole('button', { name: 'Create project & continue' }).click();
  await page.getByRole('button', { name: 'Add Environment' }).click();
  const environment = page.getByRole('dialog', { name: 'Create Environment', exact: true });
  await environment.waitFor();
  await page.keyboard.press('Escape');
  await environment.waitFor({ state: 'hidden' });
  await dialog.waitFor();
  await page.setViewportSize({ width: 390, height: 844 });
  await fits(page); await shot(page, 'onboarding-mobile');
  for (let i = 0; i < 10; i++) {
    await page.keyboard.press('Tab');
    assert.equal(await dialog.evaluate(el => el.contains(document.activeElement)), true);
  }
  assert.ok(calls.filter(([method, p]) => method === 'GET' && p === '/auth/me').length <= 4, 'No user-refresh feedback loop');
});

test('platform prompt editor separates unsaved drafts from activation', async t => {
  const { page } = await fixture(t);
  await page.goto(base + '/platform-admin/prompts/LEGACY_STORY_SCENARIOS');
  const editor = page.getByLabel('System prompt');
  await editor.waitFor(); assert.equal(await editor.getAttribute('readonly'), '');
  await page.getByRole('button', { name: 'Create Draft', exact: true }).click();
  await editor.fill('Generate useful coverage for {{title}}. Return JSON only.');
  assert.equal(await page.getByRole('button', { name: 'Activate', exact: true }).isDisabled(), true);
  await page.getByRole('button', { name: 'Save Draft', exact: true }).click();
  await page.getByRole('button', { name: 'Activate', exact: true }).click();
  await page.getByRole('dialog', { name: 'Activate platform prompt' }).waitFor();
  await page.getByRole('button', { name: 'Confirm activation' }).click();
  await page.getByRole('status').filter({ hasText: 'active for future requests' }).waitFor();
  assert.equal(await editor.getAttribute('readonly'), '');
  await shot(page, 'platform-prompt');
});

test('core pages share readable controls and stay within mobile viewport', async t => {
  const { page } = await fixture(t);
  const pages = [
    ['/projects/P1', 'Customer portal'], ['/projects/P1/stories', 'Stories'],
    ['/projects/P1/scenarios', 'Scenarios'], ['/projects/P1/testcases', 'Test Cases'],
    ['/projects/P1/knowledge', 'Teach & review product knowledge'], ['/projects/P1/environments', 'Project Environments'],
  ];
  for (const [route, heading] of pages) {
    await page.goto(base + route);
    await page.getByRole('heading', { name: heading, exact: true }).waitFor();
    assert.match(await page.locator('.workspace-shell').evaluate(el => getComputedStyle(el).fontFamily), /system-ui/);
    await shot(page, heading.replaceAll(/[^a-zA-Z]+/g, '-'));
    await page.setViewportSize({ width: 390, height: 844 });
    await fits(page); await shot(page, heading.replaceAll(/[^a-zA-Z]+/g, '-') + '-mobile');
    await page.setViewportSize({ width: 1440, height: 1000 });
  }
  await page.goto(base + '/projects/P1/stories');
  await page.getByRole('button', { name: 'New Story' }).click();
  await page.getByRole('dialog', { name: 'Create New Story' }).waitFor();
  await page.getByLabel('Title', { exact: true }).fill('Synthetic story');
  await shot(page, 'story-dialog');
  await page.keyboard.press('Escape');
  await page.waitForFunction(() => document.activeElement?.textContent?.includes('New Story'));
});

test('project administrator does not see platform prompt management', async t => {
  const { page, calls } = await fixture(t, { owner: false });
  await page.goto(base + '/projects/P1');
  await page.getByRole('heading', { name: 'Customer portal' }).waitFor();
  assert.equal(await page.getByRole('link', { name: 'Prompts', exact: true }).count(), 0);
  await page.goto(base + '/platform-admin/prompts');
  await page.getByText('Platform administration unavailable', { exact: true }).waitFor();
  assert.equal(calls.filter(([, p]) => p.startsWith('/platform-admin')).length, 0);
});


test('public landing and authentication remain separate from workspace styling', async t => {
  const { page } = await fixture(t, { authenticated: false });
  await page.goto(base + '/');
  await page.locator('header').getByRole('link', { name: 'Sign In', exact: true }).click();
  const dialog = page.getByRole('dialog', { name: 'Welcome back' });
  await dialog.waitFor();
  await shot(page, 'sign-in');
  await page.getByRole('tab', { name: 'Sign up', exact: true }).click();
  await page.getByRole('dialog', { name: 'Create your account' }).waitFor();
  await page.getByLabel('Full name').fill('Synthetic reviewer');
  await page.setViewportSize({ width: 390, height: 844 });
  await fits(page); await shot(page, 'signup-mobile');
  assert.equal(await page.locator('html').getAttribute('data-workspace-theme'), null);
  await page.getByRole('button', { name: 'Close authentication dialog' }).click();
  await page.locator('.public-landing').waitFor(); await fits(page);
});
