// Real UI with synthetic API/auth; no Jira credentials or external requests.
const {test,before,after}=require('node:test');const assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH||'playwright');
const {fixture,base}=require('./qa-agent-fixture.cjs');let browser;
before(async()=>{browser=await chromium.launch({headless:true,channel:'msedge'});});after(async()=>browser?.close());
test('Jira stays hidden while disabled',async t=>{
 const {page}=await fixture(browser,t);await page.goto(base+'/projects/P1/stories');
 await page.getByRole('heading',{name:'Stories',exact:true}).waitFor();
 assert.equal(await page.getByRole('button',{name:'Import from Jira',exact:true}).count(),0);
});
test('member reviews fields explicitly before importing; navigation never imports',async t=>{
 const f=await fixture(browser,t);const {page,context}=f;const calls=[];
 await context.route('**/features',route=>route.fulfill({json:{story_management:true,jira_story_import:true},headers:{'access-control-allow-origin':base,'access-control-allow-credentials':'true'}}));
 await context.route('**/projects/P1/jira/**',route=>{
  const path=new URL(route.request().url()).pathname;const method=route.request().method();
  const headers={'access-control-allow-origin':base,'access-control-allow-credentials':'true','access-control-allow-headers':'content-type','access-control-allow-methods':'GET,POST,OPTIONS'};
  if(method==='OPTIONS')return route.fulfill({status:204,headers});calls.push(path);
  let json={connected:true,revision:1,site:'sample.atlassian.net',project_key:'APP'};
  if(path.endsWith('/preview'))json={preview_id:'a'.repeat(32),items:[{issue_id:'1',issue_key:'APP-1',story_id:null,current:null,incoming:{title:'Imported story',description:'Description',acceptance_criteria:''},conflicts:[],warnings:[]}]};
  if(path.endsWith('/apply')){assert.equal(route.request().postDataJSON().reviewed,true);json={stories:[{story_id:'S001',action:'created'}]};}
  return route.fulfill({headers,json});
 });
 await page.goto(base+'/projects/P1/stories');await page.getByRole('button',{name:'Import from Jira',exact:true}).click();
 await page.getByText(/Connected to sample/).waitFor();assert.ok(calls.every(path=>path.endsWith("/connection")));
 assert.equal(await page.getByLabel('Read-only API token',{exact:true}).count(),0);
 await page.getByLabel('Issue keys (up to 10)').fill('APP-1');await page.getByRole('button',{name:'Preview import',exact:true}).click();
 await page.getByRole('heading',{name:'Review proposed changes'}).waitFor();
 assert.equal(await page.getByRole('button',{name:'Import selected changes'}).isDisabled(),true);
 await page.getByLabel('I reviewed the selected changes.').check();await page.getByRole('button',{name:'Import selected changes'}).click();
 await page.getByText('1 stories imported. Existing duplicates were not recreated.').waitFor();
 assert.equal(calls.filter(path=>path.endsWith('/apply')).length,1);
});

test('OAuth callback discovers site/project without token entry and exchanges only on explicit continue',async t=>{
 const {page,context}=await fixture(browser,t);let exchanges=0;let saved=0;
 await context.addInitScript(()=>sessionStorage.setItem('jira-oauth-pending',JSON.stringify({state:'s'.repeat(43),projectId:'P1'})));
 await context.route('**/projects/P1/jira/oauth/**',route=>{
  const path=new URL(route.request().url()).pathname;
  const headers={'access-control-allow-origin':base,'access-control-allow-credentials':'true','access-control-allow-headers':'content-type','access-control-allow-methods':'POST,OPTIONS'};
  if(route.request().method()==='OPTIONS')return route.fulfill({status:204,headers});
  let json={};
  if(path.endsWith('/complete')){exchanges++;json={grant_id:'a'.repeat(32),sites:[{cloud_id:'11111111-1111-4111-8111-111111111111',site:'sample.atlassian.net'}]};}
  if(path.endsWith('/projects'))json={projects:[{key:'APP',name:'Application'}],limited:false};
  if(path.endsWith('/select')){saved++;assert.equal(route.request().postDataJSON().project_key,'APP');json={connected:true};}
  return route.fulfill({headers,json});
 });
 await page.goto(base+'/jira/callback?state='+'s'.repeat(43)+'&code=SYNTHETIC_CODE');
 await page.getByRole('button',{name:'Continue Jira connection'}).waitFor();assert.equal(exchanges,0);
 assert.equal(new URL(page.url()).search,'');
 await page.getByRole('button',{name:'Continue Jira connection'}).click();
 await page.getByLabel('Jira site',{exact:true}).selectOption('11111111-1111-4111-8111-111111111111');
 await page.getByRole('button',{name:'Load Jira projects'}).click();
 await page.getByRole('option',{name:'Application (APP)'}).waitFor({state:'attached'});
 await page.getByLabel('Jira project',{exact:true}).selectOption('APP');
 await page.getByRole('button',{name:'Save Jira connection'}).click();
 await page.getByText('Jira connected. Return to Stories to preview an import.').waitFor();
 assert.equal(exchanges,1);assert.equal(saved,1);
 assert.equal(await page.locator('input[type=password]').count(),0);
 await page.reload();assert.equal(exchanges,1);
});
