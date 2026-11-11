// Intercepted UI regression fixtures only. Not real authentication/Mongo/browser execution.
const { test, before, after } = require('node:test');
const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright');
const base = process.env.FEATURE_UI_URL || 'http://127.0.0.1:3121';
let browser;
before(async () => { browser = await chromium.launch({ headless: true, channel: 'msedge' }); });
after(async () => { await browser?.close(); });

async function fixture(t, { enabled = true, seed = false, loseResponse = false, denied = false } = {}) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  t.after(() => context.close());
  await context.addCookies([{ name: 'access_token', value: 'synthetic-fixture', url: base }]);
  const batches = [], calls = [], posts = [], byKey = new Map();
  let id = 1, caseId = 1000, lose = loseResponse;
  function make(count, state) {
    const batch_id = (id++).toString(16).padStart(32, '0');
    const cases = Array.from({ length: count }, (_, index) => ({ case_run_id: (caseId++).toString(16).padStart(32, '0'),
      state: state === 'completed' ? 'completed' : index === 0 && state === 'running' ? 'running' : 'queued',
      verdict: null, logs: ['Synthetic inputs entered.'], screenshots: state === 'completed' ? ['01-open', '02-filled', '03-confirmed'] : [],
      evidence_complete: state === 'completed', diagnostic_code: null, started_at: null, finished_at: null }));
    const row = { schema_version: '1.0', batch_id, project_id: 'P1', state, adapter: 'robot-direct-webdriver-batch-v1',
      mode: 'mechanical-smoke', metering: 'unbilled-development', created_at: '2026-11-02T12:00:00Z', updated_at: '2026-11-02T12:00:00Z',
      diagnostic_code: null, cases, manifest: { schema_version: '1.0', batch_id, adapter: 'robot-direct-webdriver-batch-v1',
        mode: 'mechanical-smoke', environment: 'controlled-synthetic-v1', case_timeout_seconds: 90,
        batch_timeout_seconds: count * 110, cases: cases.map(c => ({ case_run_id: c.case_run_id, specification: 'synthetic-form-v1', authorization: 'server-owned-fixture' })) } };
    batches.push(row); return row;
  }
  if (seed) { make(2, 'running'); make(2, 'running'); make(1, 'queued'); }
  await context.route('http://feature-api.test/**', async route => {
    const request = route.request(), path = new URL(request.url()).pathname;
    const headers = { 'access-control-allow-origin': base, 'access-control-allow-credentials': 'true',
      'access-control-allow-headers': 'content-type', 'access-control-allow-methods': 'GET,POST,OPTIONS' };
    if (request.method() === 'OPTIONS') return route.fulfill({ status: 204, headers });
    calls.push({ path, method: request.method() });
    if (path.includes('/artifacts/')) return route.fulfill({ status: 200, headers, contentType: 'image/png',
      body: Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jD1sAAAAASUVORK5CYII=', 'base64') });
    let body = [], status = 200;
    if (path === '/features') body = { visual_runner_lab: true, visual_runner_batches: enabled };
    else if (path === '/auth/me') body = { user: { email: 'synthetic@example.test', name: 'Synthetic User',
      onboarding: { onboarding_status: 'completed' }, subscription: { plan: 'free', usage: {}, limits: {} } } };
    else if (path === '/projects') body = [{ project_id: 'P1', name: 'Controlled batch lab', current_user_role: 'TESTER' }];
    else if (path.includes('/visual-lab/batches')) {
      if (denied) return route.fulfill({ status: 404, headers, contentType: 'application/json', body: JSON.stringify({ detail: 'No access' }) });
      if (path.endsWith('/cancel')) {
        const run = batches.find(b => path.includes(b.batch_id));
        run.state = 'cancelled'; run.cases.forEach(c => { if (c.state !== 'completed') c.state = 'cancelled'; });
        body = run;
      } else if (request.method() === 'POST') {
        const payload = request.postDataJSON(); posts.push(payload);
        if (!byKey.has(payload.idempotency_key)) byKey.set(payload.idempotency_key, make(payload.case_count, 'queued'));
        body = byKey.get(payload.idempotency_key); status = 202;
        if (lose) { lose = false; return route.abort('failed'); }
      } else body = [...batches].reverse();
    }
    return route.fulfill({ status, headers, contentType: 'application/json', body: JSON.stringify(body) });
  });
  const page = await context.newPage();
  page.setDefaultTimeout(25000); page.setDefaultNavigationTimeout(90000);
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  await page.goto(base + '/projects/P1/visual-lab', { waitUntil: 'domcontentloaded' });
  return { page, context, batches, make, posts, calls, errors };
}

test('batch form sends bounded synthetic input only and preserves single history', async t => {
  const f = await fixture(t);
  await f.page.getByRole('heading', { name: 'Linux smoke batches' }).waitFor();
  assert.equal(await f.page.getByRole('button', { name: 'Start browser smoke check', exact: true }).count(), 0);
  assert.equal(await f.page.getByRole('heading', { name: 'Single smoke history' }).count(), 1);
  const count = f.page.getByLabel('Number of synthetic checks');
  assert.equal(await count.locator('option').count(), 10);
  await count.selectOption('10');
  await f.page.getByRole('button', { name: 'Start synthetic batch', exact: true }).click();
  await f.page.getByRole('heading', { name: 'Batch: queued', exact: true }).waitFor();
  assert.equal(f.posts.length, 1); assert.equal(f.posts[0].case_count, 10);
  assert.match(f.posts[0].idempotency_key, /^[0-9a-f]{32}$/);
  assert.deepEqual(Object.keys(f.posts[0]).sort(), ['case_count', 'idempotency_key', 'schema_version']);
  assert.equal(await f.page.getByText(/Your onboarding URL is not used/).count(), 1);
  assert.deepEqual(f.errors, []);
});

test('two active batches and a queued batch display and cancel independently', async t => {
  const f = await fixture(t, { seed: true });
  await f.page.getByText(/This project: 2 active, 1 queued/).waitFor();
  const first = f.page.getByRole('article', { name: `Batch ${f.batches[0].batch_id}`, exact: true });
  const second = f.page.getByRole('article', { name: `Batch ${f.batches[1].batch_id}`, exact: true });
  await first.getByRole('button', { name: 'Cancel batch', exact: true }).click();
  await first.getByRole('heading', { name: 'Batch: cancelled', exact: true }).waitFor();
  assert.equal(f.batches[1].state, 'running');
  assert.equal(await second.getByRole('button', { name: 'Cancel batch', exact: true }).isEnabled(), true);
  await f.page.reload({ waitUntil: 'domcontentloaded' });
  await f.page.getByRole('heading', { name: 'Batch: cancelled', exact: true }).waitFor();
  await f.page.screenshot({ path: '../tmp/visual-batches-ui.png', fullPage: true });
  assert.deepEqual(f.errors, []);
});

test('lost submission response survives refresh and resolves with the same key', async t => {
  const f = await fixture(t, { loseResponse: true });
  await f.page.getByRole('button', { name: 'Start synthetic batch', exact: true }).click();
  await f.page.getByText(/Submission outcome is unknown/).waitFor();
  await f.page.reload({ waitUntil: 'domcontentloaded' });
  await f.page.getByRole('button', { name: 'Resolve submitted batch', exact: true }).waitFor();
  assert.equal(f.posts.length, 1); // No automatic resubmission on reload/polling.
  await f.page.getByRole('button', { name: 'Resolve submitted batch', exact: true }).click();
  await f.page.getByRole('button', { name: 'Start synthetic batch', exact: true }).waitFor();
  assert.equal(f.posts.length, 2); assert.equal(f.batches.length, 1);
  assert.equal(f.posts[0].idempotency_key, f.posts[1].idempotency_key);
  assert.equal(await f.page.getByLabel('Number of synthetic checks').isEnabled(), true);
  assert.deepEqual(f.errors, []);
});

test('evidence is lazy, incomplete state visible, and terminal history stops polling', async t => {
  const f = await fixture(t);
  const run = f.make(1, 'completed'); run.cases[0].evidence_complete = false;
  await f.page.getByRole('button', { name: 'Refresh batches', exact: true }).click();
  await f.page.getByText(/Evidence incomplete/).waitFor();
  assert.equal(f.calls.filter(c => c.path.includes('/artifacts/')).length, 0);
  await f.page.getByRole('button', { name: 'View evidence', exact: true }).click();
  await f.page.getByRole('img', { name: 'Controlled sample: 01-open', exact: true }).waitFor();
  // Strict Mode can start/abort effects twice in dev. Check the three protected
  // artifact identities, not transport-attempt counts.
  assert.equal(new Set(f.calls.filter(c => c.path.includes('/artifacts/')).map(c => c.path)).size, 3);
  await f.page.clock.install();
  const before = f.calls.filter(c => c.path.endsWith('/batches')).length;
  await f.page.clock.runFor(6000);
  assert.equal(f.calls.filter(c => c.path.endsWith('/batches')).length, before);
  assert.deepEqual(f.errors, []);
});

test('disabled batch flag retains single-smoke controls without batch requests', async t => {
  const f = await fixture(t, { enabled: false });
  await f.page.getByRole('button', { name: 'Start browser smoke check', exact: true }).waitFor();
  assert.equal(await f.page.getByRole('heading', { name: 'Linux smoke batches' }).count(), 0);
  assert.equal(f.calls.some(c => c.path.includes('/batches')), false);
});

test('authorization/load error is visible and never presented as empty history', async t => {
  const f = await fixture(t, { denied: true });
  await f.page.getByText(/Unable to load batches/).waitFor();
  assert.equal(await f.page.getByText('No synthetic batches yet.', { exact: true }).count(), 0);
  assert.deepEqual(f.errors, []);
});

test('startup evidence shows sanitized stages and observations with legacy fallback', async t => {
  const f = await fixture(t);
  const run = f.make(2, 'failed');
  run.cases.forEach(c => { c.state = 'failed'; });
  Object.assign(run.cases[0], { diagnostic_code: 'ReadTimeout', startup_stage: 'session_handshake',
    startup_timings_ms: { browser_launch: 37667, devtools_connect: 5739, session_handshake: 1851 },
    startup_diagnostics: { driver_version: '146.0.7680.31', driver_state: 'running', browser_state: 'unavailable',
      devtools_port_file: 'present', session_created: false, cleanup: 'unverified',
      cleanup_driver_exit_code: -9, cleanup_browser_state: 'unavailable', native_errors: [] } });
  await f.page.getByRole('button', { name: 'Refresh batches', exact: true }).click();
  const article = f.page.getByRole('article', { name: `Batch ${run.batch_id}`, exact: true });
  await article.getByRole('button', { name: 'View evidence', exact: true }).first().click();
  await article.getByText('Startup diagnostics — session_handshake', { exact: true }).click();
  await article.getByText('browser_launch: 37667 ms', { exact: true }).waitFor();
  await article.getByText('devtools_connect: 5739 ms', { exact: true }).waitFor();
  await article.getByText(/Cleanup-induced termination is not proof/).waitFor();
  await article.getByRole('button', { name: 'View evidence', exact: true }).click();
  await article.getByText('Startup details were not recorded or are unavailable for this check.', { exact: true }).waitFor();
  assert.deepEqual(f.errors, []);
});
