const { test, before, after } = require('node:test');
const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright');
const base = process.env.FEATURE_UI_URL || 'http://localhost:3002';
let browser;
before(async () => { browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL || 'msedge', headless: true }); });
after(async () => { await browser?.close(); });
const flags = { automation_execution_ui: true, story_management: false, scenario_generation: false, test_generation: false, recorder: false, native_execution: false, repository_discovery: true, test_registry: true, test_data_generation: true };
async function fixture(t) {
  const context = await browser.newContext({ colorScheme: 'light' });
  t.after(() => context.close());
  await context.addCookies([{ name: 'access_token', value: 'test-only', url: base }]);
  const calls = [];
  const project = { id: 'P1', project_id: 'P1', current_user_role: 'ADMIN', name: 'Customer portal', description: 'Quality workspace for the customer experience.', created_at: '2026-09-01', agent_identities: {} };
  await context.route('**/*', async route => {
    const req = route.request(); const url = new URL(req.url());
    if (url.origin === new URL(base).origin || !['fetch', 'xhr'].includes(req.resourceType())) return route.continue();
    calls.push(url.pathname);
    let body = [];
    if (url.pathname === '/features') body = flags;
    if (url.pathname === '/auth/me') body = { user: { name: 'Ramraj', email: 'qa@example.com', subscription: {plan:'free',usage:{},limits:{}}, onboarding:{onboarding_status:'completed'} } };
    if (url.pathname === '/projects') body = [project];
    if (url.pathname === '/projects/P1') body = project;
    if (url.pathname.startsWith('/environments')) body = [{id:'E1', env_id:'ENV001', env_type:'qa', base_url:'https://qa.example.com',project_id:'P1',credentials:[],variables:{}}];
    await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(body),headers:{'access-control-allow-origin':base,'access-control-allow-credentials':'true'}});
  });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  t.after(() => assert.deepEqual(errors, []));
  page.setDefaultTimeout(20000); page.setDefaultNavigationTimeout(90000);
  return {page,context,calls};
}
async function appearance(page, name) {
  await page.getByRole('button',{name:'Account and appearance'}).click();
  await page.getByRole('menuitemradio',{name,exact:true}).click();
}
async function theme(page, expected) {
  await page.waitForFunction(value => document.documentElement.dataset.workspaceTheme === value, expected);
}
test('appearance persists, follows system, styles dialogs, and keeps disabled features off', async t => {
  const {page,calls}=await fixture(t);
  await page.goto(base+'/projects/P1');
  await page.getByRole('heading',{name:'Customer portal'}).waitFor();
  await theme(page,'light');
  await page.waitForFunction(()=>getComputedStyle(document.querySelector('.workspace-shell')).display === 'flex');
  assert.equal(await page.locator('[aria-current="page"]').count(),1);
  await page.screenshot({path:process.env.WORKSPACE_LIGHT_SCREENSHOT || 'tests/workspace-light.png',fullPage:true});
  await appearance(page,'Dark'); await theme(page,'dark');
  await page.reload(); await theme(page,'dark');
  await page.getByRole('heading',{name:'Customer portal'}).waitFor();
  await page.waitForFunction(()=>getComputedStyle(document.querySelector('.workspace-shell')).display === 'flex');
  assert.equal(await page.evaluate(()=>localStorage.getItem('qa-workspace-appearance')),'dark');
  await page.screenshot({path:process.env.WORKSPACE_DARK_SCREENSHOT || 'tests/workspace-dark.png',fullPage:true});
  await page.getByRole('button',{name:'Edit Project',exact:true}).click();
  const dialog = page.getByRole('dialog');
  await dialog.waitFor();
  assert.equal(await dialog.evaluate(el=>getComputedStyle(el).backgroundColor),'rgb(28, 32, 42)');
  await page.keyboard.press('Escape');
  await appearance(page,'Light'); await theme(page,'light');
  await appearance(page,'System'); await theme(page,'light');
  await page.emulateMedia({colorScheme:'dark'}); await theme(page,'dark');
  await page.emulateMedia({colorScheme:'light'}); await theme(page,'light');
  assert.deepEqual(calls.filter(p=>/^\/(stories|scenarios|recorder|testcases)/.test(p)),[]);
});
test('mobile workspace fits and landing page keeps its separate theme', async t => {
  const {page}=await fixture(t);
  await page.setViewportSize({width:390,height:844});
  await page.goto(base+'/projects/P1');
  await page.getByRole('heading',{name:'Customer portal'}).waitFor();
  await appearance(page,'Dark'); await theme(page,'dark');
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth <= innerWidth),true);
  await page.screenshot({path:process.env.WORKSPACE_MOBILE_SCREENSHOT || 'tests/workspace-mobile.png',fullPage:true});
  await page.goto(base+'/');
  assert.equal(await page.locator('html').getAttribute('data-workspace-theme'),null);
  assert.equal(await page.locator('.workspace-shell').count(),0);
});
