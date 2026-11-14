// Intercepted UI regression: no real login, MongoDB, AI or BrowserStack traffic.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright');

test('existing story analysis, stale findings and scenario count controls', async t => {
  const base = process.env.FEATURE_UI_URL || 'http://127.0.0.1:3123';
  const browser = await chromium.launch({ headless: true, channel: process.env.PLAYWRIGHT_CHANNEL || 'msedge' });
  t.after(() => browser.close());
  const context = await browser.newContext();
  await context.addCookies([{ name: 'access_token', value: 'intercepted-fixture', url: base }]);
  const sources = [], versions = [];
  let active = null, analysis = null, requested = null;
  await context.route('http://feature-api.test/**', async route => {
    const request = route.request(); const url = new URL(request.url());
    const headers = { 'access-control-allow-origin': base, 'access-control-allow-credentials': 'true',
      'access-control-allow-headers': 'content-type', 'access-control-allow-methods': 'GET,POST,OPTIONS' };
    if (request.method() === 'OPTIONS') return route.fulfill({ status: 204, headers });
    const body = request.method() === 'POST' ? request.postDataJSON() : null;
    let json = [];
    if (url.pathname === '/features') json = { product_knowledge: true, story_analysis: true, story_management: true, scenario_generation: true, test_generation: true };
    if (url.pathname === '/auth/me') json = { user: { email: 'fixture@example.test', name: 'Fixture', onboarding: { onboarding_status: 'completed' }, subscription: { usage: {}, limits: {} } } };
    if (url.pathname === '/projects/P1') json = { project_id: 'P1', name: 'Fixture', current_user_role: 'ADMIN' };
    if (url.pathname === '/projects') json = [{ project_id: 'P1', name: 'Fixture', current_user_role: 'ADMIN' }];
    if (url.pathname === '/stories') json = [{ story_id:'ST1',project_id:'P1',title:'Save draft',acceptance_criteria:'Show Draft saved.',created_at:'2026-11-13' }];
    if (url.pathname === '/stories/ST1') json = { story_id: 'ST1', project_id: 'P1', title: 'Save draft', acceptance_criteria: 'Show Draft saved.' };
    const root = '/projects/P1/knowledge';
    if (url.pathname === root) json = { sources, versions, active_version_id: active };
    if (url.pathname === root + '/analysis-summaries') json = {ST1:{state:!analysis?'not_analyzed':analysis.stale?'stale':analysis.status==='reviewed'?'reviewed':'needs_review',finding_count:analysis?.findings.length||0,blocker_count:analysis?.findings.length||0}};
    if (url.pathname === root + '/stories/ST1/suggest-knowledge') {const source={source_id:'c'.repeat(32),title:'Story: Save draft',kind:'document',text:'Show Draft saved.',segments:[],origin:{kind:'story',story_id:'ST1',story_digest:'d'.repeat(64)}};sources.push(source);json={source,requires_review:true,claims:[{claim_id:'K_story',category:'business_rule',statement:'Proposed save rule',epistemic_status:'inferred',source_id:source.source_id,segment_index:null,quote:'Show Draft saved.'}],clarification_questions:['When does saving occur?']};}
    if (url.pathname === root + '/sources') { json = { ...body, source_id: 'a'.repeat(32) }; sources.push(json); }
    if (url.pathname === root + '/versions') { json = { ...body, version_id: 'b'.repeat(32), status: 'draft', content_digest: 'c'.repeat(64) }; versions.push(json); }
    if (url.pathname.endsWith('/versions/' + 'b'.repeat(32) + '/approve')) { versions[0].status = 'approved'; active = versions[0].version_id; json = versions[0]; }
    if (url.pathname === root + '/stories/ST1/analysis') json = analysis;
    if (url.pathname === root + '/stories/ST1/analyze') json = analysis = { analysis_id: 'd'.repeat(32), status: 'needs_review', summary: 'Clarify timing', knowledge_version_id: active,
      findings: [{ finding_id: 'F1', category: 'missing_detail', severity: 'blocker', description: 'Missing timing', question: 'When should confirmation appear?' }] };
    if (url.pathname.endsWith('/analysis/' + 'd'.repeat(32) + '/review')) { assert.equal(body.resolutions[0].rationale, 'After Save is clicked.'); json = analysis = { ...analysis, status: 'reviewed', resolutions: body.resolutions }; }
    if (url.pathname === '/scenarios/generate-from-story') { requested = url.searchParams.get('count'); json = { scenarios: [{ scenario_id: 'SC1' }], summary: { message: '1 of 4 requested scenarios generated (allowed 4).' } }; }
    return route.fulfill({ headers, json });
  });
  const page = await context.newPage(); page.setDefaultTimeout(45000); page.setDefaultNavigationTimeout(90000);
  versions.push({version_id:'b'.repeat(32),title:'Existing approved rules',status:'approved',claims:[{claim_id:'K1',statement:'Show Draft saved.',quote:'Draft saved',epistemic_status:'expected'}]});
  active=versions[0].version_id;
  await page.goto(base + '/projects/P1/stories/ST1');
  await page.getByRole('button', { name: 'Analyze with AI' }).click().catch(async error => { console.log('Fixture-only page text:', await page.locator('body').innerText()); throw error; });
  const approve = page.getByRole('button', { name: 'Approve analysis review (project admin)' });
  await approve.waitFor(); assert.equal(await approve.isDisabled(), true);
  await page.getByLabel('Clarification or rationale').fill('After Save is clicked.');
  await approve.click();
  await page.getByRole('status').filter({ hasText: /^Reviewed$/ }).waitFor();
  await page.getByLabel('Requested scenarios').fill('4');
  await page.getByRole('button', { name: 'Generate scenarios with AI' }).click();
  await page.getByRole('status').filter({ hasText: '1 of 4 requested scenarios generated' }).waitFor();
  assert.equal(requested, '4');
  await page.goto(base+'/projects/P1/stories');await page.getByRole('link',{name:'Reviewed',exact:true}).waitFor();
  analysis.stale=true;await page.reload();await page.getByRole('link',{name:'Stale',exact:true}).waitFor();
  // QA Agent training browser coverage lives in qa-agent-training.test.cjs.
});
