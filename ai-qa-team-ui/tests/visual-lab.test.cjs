// Existing UI browser-test tooling only; never part of visual-runner dependencies.
const { test, before, after } = require('node:test');
const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright');
const base = process.env.FEATURE_UI_URL || 'http://127.0.0.1:3107';
let browser;
before(async () => { browser = await chromium.launch({ headless: true, channel: 'msedge' }); });
after(async () => { await browser?.close(); });

async function fixture(t, enabled = true) {
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  t.after(() => context.close());
  await context.addCookies([{ name: 'access_token', value: 'synthetic-test-only', url: base }]);
  let run;
  const posts = [];
  const calls = [];
  await context.route('http://feature-api.test/**', async route => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    const headers = { 'access-control-allow-origin': base, 'access-control-allow-credentials': 'true',
      'access-control-allow-headers': 'content-type', 'access-control-allow-methods': 'GET,POST,OPTIONS' };
    if (request.method() === 'OPTIONS') return route.fulfill({ status: 204, headers });
    calls.push(path);
    if (path.includes('/artifacts/')) return route.fulfill({ status: 200, headers, contentType: 'image/png',
      body: Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jD1sAAAAASUVORK5CYII=', 'base64') });
    let body = [];
    if (path === '/features') body = { visual_runner_lab: enabled };
    else if (path === '/auth/me') body = { user: { email: 'synthetic@example.test', name: 'Synthetic User', onboarding: { onboarding_status: 'completed' }, subscription: { plan: 'free', usage: {}, limits: {} } } };
    else if (path === '/projects') body = [{ project_id: 'P1', name: 'Controlled lab', current_user_role: 'TESTER' }];
    else if (path.endsWith('/cancel')) { posts.push('cancel'); run.state = 'cancelled'; run.logs = ['Browser smoke check cancelled.']; body = run; }
    else if (path.endsWith('/visual-lab/runs')) {
      if (request.method() === 'POST') {
        posts.push(request.postDataJSON());
        run = { run_id: 'a'.repeat(32), state: 'running', headed: request.postDataJSON().headed, created_at: '2026-10-31T12:00:00Z', logs: ['Synthetic inputs entered.'], screenshots: [], browser_version: '146.0.7680.31' };
        body = run;
      } else body = run ? [run] : [];
    }
    return route.fulfill({ status: 200, headers, contentType: 'application/json', body: JSON.stringify(body) });
  });
  const page = await context.newPage();
  page.setDefaultTimeout(20000);
  page.setDefaultNavigationTimeout(90000);
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.goto(base+'/projects/P1/visual-lab', { waitUntil: 'domcontentloaded' });
  return { page, posts, calls, errors, complete() { run.state = 'completed'; run.logs = ['Browser smoke check completed']; run.screenshots = ['03-confirmed']; },
    failStartup() {
      run.state = 'failed'; run.diagnostic_code = 'ReadTimeout'; run.startup_stage = 'browser_launch';
      run.startup_timings_ms = { browser_launch: 5000 };
      run.startup_diagnostics = { driver_version: '146.0.7680.31', driver_state: 'running',
        browser_state: 'running', devtools_port_file: 'absent', session_created: false,
        cleanup: 'driver_exited_job_closed', cleanup_driver_exit_code: 0,
        cleanup_browser_state: 'exited', native_errors: [] };
    } };
}

test('lab user starts, observes, cancels and separately chooses visible mode', async t => {
  const f = await fixture(t);
  await f.page.getByRole('heading', { name: 'Visual Runner Lab', exact: true }).waitFor();
  await f.page.getByRole('button', { name: 'Start browser smoke check' }).click();
  await f.page.getByRole('heading', { name: 'Smoke check: running' }).waitFor();
  assert.equal(await f.page.getByRole('button', { name: 'Start browser smoke check' }).isDisabled(), true);
  await f.page.getByRole('button', { name: 'Cancel smoke check' }).click();
  await f.page.getByRole('heading', { name: 'Smoke check: cancelled' }).waitFor();
  await f.page.getByRole('checkbox').check();
  await f.page.getByRole('button', { name: 'Start browser smoke check' }).click();
  f.complete();
  await f.page.getByRole('heading', { name: 'Browser smoke check completed', exact: true }).waitFor();
  await f.page.getByRole('img', { name: 'Controlled sample: 03-confirmed' }).waitFor();
  await f.page.waitForFunction(() => [...document.images].some(image => image.alt === 'Controlled sample: 03-confirmed' && image.naturalWidth > 0));
  assert.deepEqual(f.posts, [{ headed: false }, 'cancel', { headed: true }]);
  assert.deepEqual(f.errors, []);
  await f.page.screenshot({ path: '../tmp/visual-lab-ui.png', fullPage: true });
});

test('disabled lab does not mount or fetch its run API', async t => {
  const f = await fixture(t, false);
  await f.page.getByText('This feature is disabled.', { exact: true }).waitFor();
  assert.equal(f.calls.some(path => path.includes('/visual-lab')), false);
  assert.equal(await f.page.getByRole('link', { name: 'Visual Runner Lab', exact: true }).count(), 0);
});

test('startup failure displays bounded observations and phase timing', async t => {
  const f = await fixture(t);
  await f.page.getByRole('button', { name: 'Start browser smoke check' }).click();
  await f.page.getByRole('heading', { name: 'Smoke check: running' }).waitFor();
  f.failStartup();
  await f.page.getByRole('heading', { name: 'Smoke check: failed' }).waitFor();
  await f.page.getByText('Startup diagnostic bundle', { exact: true }).click();
  await f.page.getByText('driver_exited_job_closed', { exact: true }).waitFor();
  await f.page.getByText('absent', { exact: true }).waitFor();
  await f.page.getByText('browser_launch: 5000 ms', { exact: true }).waitFor();
  assert.equal(await f.page.getByRole('button', { name: 'Start browser smoke check' }).isEnabled(), true);
  assert.deepEqual(f.errors, []);
});
