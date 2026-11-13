// Synthetic intercepted UI checks. Real Mongo/auth API verification is a separate script.
const { test, before, after } = require('node:test');
const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright');
const base = process.env.FEATURE_UI_URL || 'http://127.0.0.1:3123';
let browser;
before(async () => { browser = await chromium.launch({ headless: true, channel: process.env.PLAYWRIGHT_CHANNEL || 'msedge' }); });
after(async () => browser?.close());

async function fixture(t, { role = 'OWNER', pending = false, signup = false, emailDelivery = false, aiUnlimited = false, splitAI = false, resumeAI = false, missingTier = false, savedBYOK = false } = {}) {
  const context = await browser.newContext(); t.after(() => context.close());
  await context.addCookies([{ name: 'access_token', value: 'intercepted-ui-fixture', url: base }]);
  let authenticated = !signup;
  let aiConfiguration = savedBYOK ? {provider_id:'openai',mode:'BYOK',model:'gpt-4o-mini',configuration:{},status:'ACTIVE',credential_configured:true} : null;
  const user = { name: 'Fixture', email: 'fixture@example.com', account_id: 'ACC_one', account_role: role,
    onboarding: { onboarding_status: pending ? 'in_progress' : 'completed', current_step: resumeAI ? 5 : 1, context: { project_id: resumeAI ? "P1" : null } }, subscription: { usage: {}, limits: {} } };
  const account = { account_id: 'ACC_one', name: pending ? null : 'Customer One', setup_status: pending ? 'PENDING' : 'COMPLETE', current_user_role: role };
  const project = { project_id: 'P1', name: 'Module One', current_user_role: 'ADMIN' };
  const calls = []; const invites = [];
  await context.route('http://feature-api.test/**', async route => {
    const request = route.request(), url = new URL(request.url());
    const headers = { 'access-control-allow-origin': base, 'access-control-allow-credentials': 'true', 'access-control-allow-headers': 'content-type', 'access-control-allow-methods': 'GET,POST,PATCH,DELETE,OPTIONS' };
    if (request.method() === 'OPTIONS') return route.fulfill({ status: 204, headers });
    const body = request.postData() ? request.postDataJSON() : null;
    calls.push({ method: request.method(), path: url.pathname, body });
    let json = [];
    if (url.pathname === '/features') json = { customer_accounts: true, account_invitation_email: emailDelivery };
    if (url.pathname === '/auth/me') {
      if (!authenticated) return route.fulfill({ status: 401, headers, json: { detail: 'Fixture signed out' } });
      json = { user };
    }
    if (url.pathname === '/auth/signup') { authenticated = true; user.account_role = 'MEMBER'; user.onboarding.onboarding_status = 'completed'; json = { user }; }
    if (url.pathname === '/account') {
      if (request.method() === 'PATCH') { account.name = body.name; account.setup_status = 'COMPLETE'; }
      json = account;
    }
    if (url.pathname === '/account/projects') json = [project];
    if (url.pathname === '/account/subscription') json = { billing_scope: 'ACCOUNT', subscription: { plan: 'free', status: 'active', usage: { projects_used: 1, stories_used: 1, scenarios_used: 2, testcases_used: 3, testcases_basic_used: 3, testcases_medium_used: 0, testcases_advanced_used: 0, team_members_used: 1, executions_used: 0, ai_gen_used: 1 }, limits: { ai_gen_limit: aiUnlimited ? null : 3, stories_limit: 5, scenarios_limit: 10, executions_limit: 20, projects_limit: 1, testcases_limit: 0, testcases_basic_limit: 10, testcases_medium_limit: 0, testcases_advanced_limit: 0, team_members_limit: 2 } } };
    if (url.pathname === '/account/subscription' && splitAI) { json.subscription.ai_allowance_version = 1; Object.assign(json.subscription.usage, { managed_ai_credits_used: 1, byok_ai_requests_used: 2 }); Object.assign(json.subscription.limits, { managed_ai_credits_limit: 25, byok_ai_requests_limit: 25 }); }
    if (url.pathname === '/account/subscription' && missingTier) delete json.subscription.limits.testcases_advanced_limit;
    if (url.pathname === '/account/members') json = [{ email: user.email, account_role: role }];
    if (url.pathname === '/account/invitations') {
      if (request.method() === 'POST') {
        const item = { invitation_id: 'a'.repeat(32), email: body.email, role: body.role, expires_at: '2026-12-01T00:00:00Z' };
        invites.push(item); json = body.delivery === 'EMAIL' ? { ...item, email_delivery: 'SENT' } : { ...item, token: 'synthetic-ui-invitation' };
      } else json = invites;
    }
    if (url.pathname.startsWith('/account/invitations/') && request.method() === 'DELETE') { invites.length = 0; json = { revoked: true }; }
    if (url.pathname === '/projects') {
      if (request.method() === 'POST') { user.onboarding.current_step = 2; user.onboarding.context.project_id = 'P1'; json = project; }
      else json = role === 'MEMBER' ? [] : [project];
    }
    if (url.pathname === '/projects/P1/ai/providers') json = [
      {provider_id:'managed',label:'Managed',fields:[{name:'model',label:'Model',secret:false}],capabilities:[]},
      {provider_id:'openai',label:'OpenAI',fields:[{name:'model',label:'Model',secret:false},{name:'api_key',label:'API key',secret:true}],capabilities:[]}
    ];
    if (url.pathname === '/projects/P1/ai/configuration') { if(request.method()==='PUT') aiConfiguration={provider_id:body.provider_id,mode:body.mode,model:body.model,configuration:{},status:'ACTIVE',credential_configured:body.mode==='BYOK'}; json=aiConfiguration; }
    if (url.pathname === '/projects/P1/ai/configuration/test') json = {ok:true};
    if (url.pathname === '/onboarding/progress') {user.onboarding.current_step=body.current_step;json={success:true};}
    if (url.pathname === '/projects/P1') json = project;
    if (url.pathname === '/projects/P1/team') json = { current_user_role: 'ADMIN', members: [] };
    return route.fulfill({ json, headers });
  });
  const page = await context.newPage(); page.setDefaultTimeout(30000); page.setDefaultNavigationTimeout(90000);
  const errors = []; page.on('pageerror', error => errors.push(error.message)); t.after(() => assert.deepEqual(errors, []));
  return { page, calls, account };
}

test('owner names existing pending account in first onboarding step before project creation', async t => {
  const { page, calls, account } = await fixture(t, { pending: true });
  await page.goto(base + '/onboarding');
  await page.getByRole('heading', { name: 'Name your account & first project' }).waitFor();
  await page.getByLabel('Project name', { exact: true }).fill('Module One');
  const save = page.getByRole('button', { name: 'Create project & continue' });
  assert.equal(await save.isDisabled(), true);
  await page.getByLabel('Customer / account name').fill('Customer Alpha');
  await save.click();
  await page.getByRole('button', { name: 'Add Environment' }).waitFor();
  const writes = calls.filter(call => ['POST', 'PATCH'].includes(call.method));
  assert.equal(writes[0].path, '/account'); assert.equal(writes[1].path, '/projects');
  assert.equal(account.account_id, 'ACC_one'); assert.equal(account.name, 'Customer Alpha');
  assert.equal(writes[1].body.account_id, undefined);
});

test('account owner creates private invitation link and can revoke it', async t => {
  const { page, calls } = await fixture(t);
  await page.goto(base + '/settings/account/team');
  await page.getByLabel('New member email').fill('teammate@example.com');
  await page.getByRole('button', { name: 'Create invitation link' }).click();
  const link = page.getByLabel('Private invitation link'); await link.waitFor();
  assert.ok((await link.inputValue()).includes('#invite=synthetic-ui-invitation'));
  assert.equal(calls.filter(call => call.path.includes('send')).length, 0);
  await page.getByRole('button', { name: 'Revoke invitation', exact: true }).click();
  await page.getByRole('status').filter({ hasText: 'Invitation revoked.' }).waitFor();
  assert.equal(await link.count(), 0);
});

test('account member cannot invite or rename and does not start new-customer onboarding', async t => {
  const { page, calls } = await fixture(t, { role: 'MEMBER' });
  await page.goto(base + '/settings/account');
  const name = page.getByLabel('Customer / account name'); await name.waitFor();
  assert.equal(await name.isDisabled(), true);
  assert.equal(await page.getByRole('button', { name: 'Create invitation link' }).count(), 0);
  assert.equal(calls.filter(call => call.path === '/account/invitations').length, 0);
  await page.goto(base + '/dashboard');
  await page.getByRole('button', { name: /Create Project/ }).first().waitFor();
  assert.equal(await page.getByRole('dialog').count(), 0);
  assert.equal(await page.getByRole('button', { name: /Create Project/ }).first().isDisabled(), true);
});

test('invited local signup submits token in body and clears fragment on success', async t => {
  const { page, calls } = await fixture(t, { signup: true });
  await page.goto(base + '/auth?mode=signup#invite=synthetic-ui-invitation');
  await page.getByLabel('Full name').fill('Synthetic Member');
  await page.getByLabel('Work email').fill('member@example.com');
  await page.getByLabel('Password', { exact: true }).fill('synthetic-test-password');
  await page.getByRole('button', { name: 'Create account', exact: true }).click();
  await page.waitForURL('**/dashboard');
  const signup = calls.find(call => call.path === '/auth/signup');
  assert.equal(signup.body.invitation_token, 'synthetic-ui-invitation');
  assert.equal(new URL(page.url()).hash, '');
});


test('account owner assigns self through central team and project navigation hides Team', async t => {
  const { page, calls } = await fixture(t);
  await page.goto(base + '/settings/account/team');
  await page.getByLabel('Project', { exact: true }).selectOption('P1');
  await page.getByLabel('Team member email').selectOption('fixture@example.com');
  await page.getByLabel('Team member role').selectOption('ADMIN');
  await page.getByRole('button', { name: 'Add member', exact: true }).click();
  await page.waitForFunction(() => document.querySelector('[aria-label="Team member email"]')?.value === '');
  const assignment = calls.find(call => call.path === '/projects/P1/team' && call.method === 'POST');
  assert.deepEqual(assignment.body, { email: 'fixture@example.com', role: 'ADMIN' });
  await page.goto(base + '/projects/P1/settings/team');
  await page.getByRole('heading', { name: 'Team management moved' }).waitFor();
  assert.equal(await page.locator('aside').getByRole('link', { name: 'Team', exact: true }).count(), 0);
});

test('account details displays shared plan and usage', async t => {
  const { page } = await fixture(t);
  await page.goto(base + '/settings/account');
  await page.getByRole('heading', { name: 'Subscription & usage' }).waitFor();
  await page.getByText('1 / 1', { exact: true }).waitFor();
});


test('account details hides its ID, groups Test Cases and uses title-case usage labels', async t => {
  const { page } = await fixture(t);
  await page.goto(base + '/settings/account');
  await page.getByRole('heading', { name: 'Subscription & usage' }).waitFor();
  assert.equal(await page.getByText('ACC_one', { exact: false }).count(), 0);
  assert.equal(await page.locator('dt').filter({ hasText: /^Test Cases$/ }).count(), 1);
  const tiers = page.getByLabel('Test case usage by complexity');
  await tiers.getByText('Basic', { exact: true }).waitFor();
  await tiers.getByText('Medium', { exact: true }).waitFor();
  await tiers.getByText('Advanced', { exact: true }).waitFor();
  assert.equal(await page.locator('dt').filter({ hasText: /testcases|projects|team_members/ }).count(), 0);
  const links = await page.locator('aside .workspace-nav-link').allTextContents();
  assert.deepEqual(links.slice(0, 4), ['Dashboard', 'Account', 'AI Configuration', 'Projects']);
});


test('configured email mode sends without exposing a manual invitation link', async t => {
  const { page, calls } = await fixture(t, { emailDelivery: true });
  await page.goto(base + '/settings/account/team');
  await page.getByLabel('New member email').fill('synthetic@example.com');
  await page.getByRole('button', { name: 'Send Invitation', exact: true }).click();
  await page.getByRole('status').filter({ hasText: 'Invitation email sent.' }).waitFor();
  assert.equal(calls.find(call => call.method === 'POST' && call.path === '/account/invitations').body.delivery, 'EMAIL');
  assert.equal(await page.getByLabel('Private invitation link').count(), 0);
});


test('subscription redesign has bold plan/status and explains monthly AI credits separately from execution', async t => {
  const { page } = await fixture(t);
  await page.goto(base + '/settings/account');
  const section = page.getByRole('region', { name: 'Subscription & usage' });
  await section.getByRole('heading', { name: 'AI Requests', exact: true }).waitFor();
  for (const text of ['Free', 'Active']) {
    const label = section.locator('strong').filter({ hasText: new RegExp('^' + text + '$') });
    assert.equal(await label.count(), 1);
    assert.ok(await label.evaluate(node => Number(getComputedStyle(node).fontWeight) >= 700));
  }
  const meter = section.getByRole('progressbar', { name: 'AI Requests usage', exact: true });
  assert.equal(await meter.getAttribute('value'), '1');
  assert.equal(await meter.getAttribute('max'), '3');
  await section.getByText(/Monthly allowance shared by product knowledge extraction/).waitFor();
  await section.getByText('AI used during browser execution is not included in this counter yet.', { exact: true }).waitFor();
  await section.getByRole('heading', { name: 'Workspace Capacity', exact: true }).waitFor();
  await section.getByRole('heading', { name: 'Team Capacity', exact: true }).waitFor();
  assert.equal(await section.getByRole('heading', { name: 'Execution Usage', exact: true }).count(), 0);
  assert.equal(await section.getByText('AI Generations', { exact: true }).count(), 0);
  if (process.env.ACCOUNT_UI_SCREENSHOT) await page.screenshot({path: process.env.ACCOUNT_UI_SCREENSHOT, fullPage: true});
  await page.setViewportSize({ width: 390, height: 844 });
  assert.ok(await section.evaluate(node => node.scrollWidth <= node.clientWidth + 1));
});

test('unlimited AI allowance has no misleading bounded progress bar', async t => {
  const { page } = await fixture(t, { aiUnlimited: true });
  await page.goto(base + '/settings/account');
  const section = page.getByRole('region', { name: 'Subscription & usage' });
  await section.getByText('Unlimited allowance', { exact: true }).waitFor();
  assert.equal(await section.getByRole('progressbar', { name: 'AI Requests usage', exact: true }).count(), 0);
});


test('split AI allowances show separate Managed credits and BYOK requests', async t => {
  const { page } = await fixture(t, { splitAI: true });
  await page.goto(base + '/settings/account');
  const section = page.getByRole('region', { name: 'Subscription & usage' });
  const managed = section.getByRole('progressbar', { name: 'Managed AI Requests usage', exact: true });
  const byok = section.getByRole('progressbar', { name: 'BYOK AI Requests usage', exact: true });
  await managed.waitFor();
  assert.equal(await managed.getAttribute('value'), '1'); assert.equal(await managed.getAttribute('max'), '25');
  assert.equal(await byok.getAttribute('value'), '2'); assert.equal(await byok.getAttribute('max'), '25');
  await section.getByText(/Each AI request uses one unit/).waitFor();
  await section.getByText(/BYOK uses your key and provider billing/).waitFor();
  assert.equal(await section.getByRole('heading', { name: 'Execution Usage', exact: true }).count(), 0);
  assert.equal(await section.getByRole('progressbar', { name: 'AI Requests usage', exact: true }).count(), 0);
});

test('zero complexity allowances say Not included instead of 0 / 0',async t=>{
 const {page}=await fixture(t,{splitAI:true});await page.goto(base+'/settings/account');
 const tiers=page.getByLabel('Test case usage by complexity');await tiers.waitFor();
 assert.equal(await tiers.locator('dd').filter({hasText:/^Not included$/}).count(),2);
 assert.equal(await tiers.getByText('0 / 0',{exact:true}).count(),0);
 assert.equal(await page.getByText(/earlier AI units could not be attributed/).count(),0);
});
test('onboarding AI Setup can be skipped without activation or connection calls',async t=>{
 const {page,calls}=await fixture(t,{pending:true,resumeAI:true});await page.goto(base+'/onboarding');
 await page.getByRole('heading',{name:'AI Setup',exact:true}).waitFor();
 await page.getByRole('button',{name:'Skip for now',exact:true}).click();
 await page.getByRole('heading',{name:'Project ready',exact:true}).waitFor();
 assert.equal(calls.filter(call=>call.path.includes('/ai/configuration')&&call.method!=='GET').length,0);
 assert.equal(calls.find(call=>call.path==='/onboarding/progress').body.current_step,6);
});
test('onboarding reuses Managed and BYOK configuration with explicit activation',async t=>{
 const {page,calls}=await fixture(t,{pending:true,resumeAI:true});await page.goto(base+'/onboarding');
 const provider=page.getByLabel('Provider',{exact:true});await provider.locator('option[value=managed]').waitFor({state:'attached'});assert.equal(await provider.inputValue(),'managed');assert.equal(await page.getByLabel('API key',{exact:true}).count(),0);
 await page.getByRole('button',{name:'Test Connection',exact:true}).click();
 await page.getByText('Connection successful.',{exact:true}).waitFor();
 const managed=calls.find(call=>call.path.endsWith('/configuration/test')).body;
 assert.equal(managed.mode,'MANAGED');assert.equal(managed.api_key,undefined);
 await provider.selectOption('openai');await page.getByLabel('API key',{exact:true}).fill('synthetic-test-key');
 await page.getByRole('button',{name:'Test Connection',exact:true}).click();await page.getByText('Connection successful.',{exact:true}).waitFor();
 const byok=calls.filter(call=>call.path.endsWith('/configuration/test')).at(-1).body;
 assert.equal(byok.mode,'BYOK');assert.equal(byok.api_key,'synthetic-test-key');
 await page.getByRole('button',{name:'Activate',exact:true}).click();
 await page.getByText('Provider saved and activated.',{exact:true}).waitFor();
 assert.equal(calls.find(call=>call.path.endsWith('/ai/configuration')&&call.method==='PUT').body.mode,'BYOK');
 assert.equal(await page.getByLabel('API key',{exact:true}).inputValue(),'');
 await page.getByRole('button',{name:'Continue',exact:true}).click();await page.getByRole('heading',{name:'Project ready',exact:true}).waitFor();
});

test('missing complexity allowance is Unavailable rather than Not included',async t=>{
 const {page}=await fixture(t,{missingTier:true});await page.goto(base+'/settings/account');
 const tiers=page.getByLabel('Test case usage by complexity');await tiers.waitFor();
 assert.equal(await tiers.locator('dd').filter({hasText:/^Unavailable$/}).count(),1);
 assert.equal(await tiers.locator('dd').filter({hasText:/^Not included$/}).count(),1);
});

test('onboarding preserves saved BYOK instead of silently selecting Managed',async t=>{
 const {page,calls}=await fixture(t,{pending:true,resumeAI:true,savedBYOK:true});
 let release;const held=new Promise(resolve=>{release=resolve;});t.after(()=>release());
 await page.route('**/projects/P1/ai/configuration',async route=>{await held;await route.fallback();});
 await page.goto(base+'/onboarding');
 const activate=page.getByRole('button',{name:'Activate',exact:true});await activate.waitFor();assert.equal(await activate.isDisabled(),true);release();
 const provider=page.getByLabel('Provider',{exact:true});await provider.locator('option[value=openai]').waitFor({state:'attached'});
 assert.equal(await provider.inputValue(),'openai');
 await page.getByRole('button',{name:'Skip for now',exact:true}).click();await page.getByRole('heading',{name:'Project ready',exact:true}).waitFor();
 assert.equal(calls.filter(call=>call.path.includes('/ai/configuration')&&call.method!=='GET').length,0);
});


test('setup Back reuses project and Application can be skipped without import', async t => {
 const {page,calls}=await fixture(t,{pending:true});await page.goto(base+'/onboarding');
 await page.getByLabel('Customer / account name').fill('Customer One');
 await page.getByLabel('Project name',{exact:true}).fill('Module One');
 await page.getByRole('button',{name:'Create project & continue',exact:true}).click();
 await page.getByRole('heading',{name:'Application & environment (optional)',exact:true}).waitFor();
 await page.getByRole('button',{name:'Back',exact:true}).click();
 await page.getByText('Your project is already created.',{exact:false}).waitFor();
 await page.getByRole('button',{name:'Continue',exact:true}).click();
 await page.getByRole('button',{name:'Skip for now',exact:true}).click();
 await page.getByRole('heading',{name:'Build your project team',exact:true}).waitFor();
 await page.getByRole('button',{name:'Continue',exact:true}).click();
 await page.getByRole('heading',{name:'AI Setup',exact:true}).waitFor();
 assert.equal(await page.getByText('Optional import',{exact:true}).count(),0);
 assert.equal(calls.filter(c=>c.path==='/projects'&&c.method==='POST').length,1);
 assert.equal(calls.filter(c=>c.path==='/environments'&&c.method==='POST').length,0);
});

test('team capacity includes owner without reducing two additional seats', async t => {
 const {page}=await fixture(t);await page.goto(base+'/settings/account');
 const team=page.getByRole('progressbar',{name:'Team Members usage',exact:true});await team.waitFor();
 assert.equal(await team.getAttribute('value'),'2');assert.equal(await team.getAttribute('max'),'3');
});

test('completed onboarding stays closed when all projects have been deleted', async t => {
 const {page}=await fixture(t);
 await page.route('**/projects',route=>route.fulfill({json:[],headers:{'access-control-allow-origin':base,'access-control-allow-credentials':'true'}}));
 await page.goto(base+'/dashboard');await page.getByText('No projects created yet.',{exact:true}).waitFor();
 assert.equal(await page.getByRole('dialog',{name:'Set up your QA workspace'}).count(),0);
});
