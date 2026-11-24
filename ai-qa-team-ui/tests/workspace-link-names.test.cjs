// Isolated browser/API doubles; no live accounts, secrets or model calls.
const {test,before,after}=require('node:test');
const assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH||'playwright');
const {fixture,base}=require('./qa-agent-fixture.cjs');
let browser;
before(async()=>{browser=await chromium.launch({headless:true,channel:'msedge'});});
after(async()=>browser?.close());
async function setup(t,{member=false}={}){
 const f=await fixture(browser,t);const writes=[];
 const headers={'access-control-allow-origin':base,'access-control-allow-credentials':'true','access-control-allow-headers':'content-type','access-control-allow-methods':'GET,PATCH,OPTIONS'};
 const user={email:'fixture@example.com',name:'Fixture',platform_role:'ADMIN',account_role:member?'MEMBER':'OWNER',account_id:'ACC_one',onboarding:{onboarding_status:'completed'},subscription:{usage:{},limits:{}}};
 const project={project_id:'P1',name:'Customer portal',description:'Project details',created_at:'2026-11-01',current_user_role:member?'TESTER':'ADMIN',agent_identities:{}};
 const account={account_id:'ACC_one',name:'Customer One',current_user_role:member?'MEMBER':'OWNER',setup_status:'COMPLETE'};
 await f.context.route(url=>url.origin==='http://feature-api.test'&&url.pathname==='/auth/me',r=>r.fulfill({headers,json:{user}}));
 await f.context.route(url=>url.origin==='http://feature-api.test'&&url.pathname==='/features',r=>r.fulfill({headers,json:{customer_accounts:true}}));
 await f.context.route(url=>url.origin==='http://feature-api.test'&&url.pathname==='/projects/P1',r=>{
  if(r.request().method()==='OPTIONS')return r.fulfill({headers,status:204});
  if(r.request().method()==='PATCH'){const body=r.request().postDataJSON();writes.push(body);Object.assign(project,body);}
  return r.fulfill({headers,json:project});
 });
 await f.context.route(url=>url.origin==='http://feature-api.test'&&url.pathname==='/account',r=>{
  if(r.request().method()==='OPTIONS')return r.fulfill({headers,status:204});
  if(r.request().method()==='PATCH'){const body=r.request().postDataJSON();writes.push(body);Object.assign(account,body);}
  return r.fulfill({headers,json:account});
 });
 await f.context.route(url=>url.origin==='http://feature-api.test'&&url.pathname==='/account/subscription',r=>r.fulfill({headers,json:{billing_scope:'ACCOUNT',subscription:{plan:'free',status:'active',usage:{},limits:{}}}}));
 await f.context.route(url=>url.origin==='http://feature-api.test'&&url.pathname==='/environments',r=>r.fulfill({headers,json:[{env_id:'ENV1',name:'QA',env_type:'qa',base_url:'https://qa.example.com'}]}));
 await f.context.route(url=>url.origin==='http://feature-api.test'&&url.pathname==='/platform-admin/prompts',r=>r.fulfill({headers,json:[{prompt_key:'KNOWLEDGE_ASK_V1',name:'Ask Your QA Agent',description:'Answer from approved knowledge.',output_contract:'KnowledgeAnswer',source:'CODE_FALLBACK',resolved_version:'CODE_DEFAULT_V1'}]}));
 return {...f,writes,headers};
}
for(const width of [1280,390])test(`summary links have clean title/description styling at ${width}px`,async t=>{
 const {page}=await setup(t);await page.setViewportSize({width,height:900});
 for(const path of ['/platform-admin/prompts','/projects/P1']){
  await page.goto(base+path);const link=page.locator('a.workspace-summary-link').first();await link.waitFor();
  await page.waitForFunction(()=>getComputedStyle(document.querySelector('a.workspace-summary-link')).textDecorationLine==='none');
  const styles=await link.evaluate(el=>({title:getComputedStyle(el.querySelector('.workspace-row-title')).color,description:getComputedStyle(el.querySelector('.workspace-row-subtitle')).color}));
  assert.notEqual(styles.title,styles.description);
  const row=link.locator('..');assert.equal(await row.locator('.workspace-badge').evaluate(el=>el.closest('a')===null),true);
  await link.hover();assert.equal(await link.locator('.workspace-row-title').evaluate(el=>getComputedStyle(el).textDecorationLine),'underline');
  assert.equal(await link.locator('.workspace-row-subtitle').evaluate(el=>getComputedStyle(el).textDecorationLine),'none');
  await page.screenshot({path:`../tmp/summary-${path.includes('prompts')?'prompts':'environment'}-${width}.png`,fullPage:true});
 }
});
test('project rename is inline, saves only name, cancels on Escape and hides Agent Settings',async t=>{
 const {page,writes}=await setup(t);await page.goto(base+'/projects/P1');
 await page.getByRole('button',{name:'Edit project name',exact:true}).click();
 const input=page.getByRole('textbox',{name:'Project name',exact:true});await input.fill('Renamed project');await input.press('Enter');
 await page.getByRole('heading',{name:'Renamed project',exact:true}).waitFor();assert.deepEqual(writes,[{name:'Renamed project'}]);
 assert.equal(await page.getByRole('dialog').count(),0);
 await page.getByRole('button',{name:'Edit project name',exact:true}).click();await input.fill('Discard this');await input.press('Escape');
 await page.getByRole('heading',{name:'Renamed project',exact:true}).waitFor();assert.equal(writes.length,1);
 await page.getByRole('button',{name:'Project actions',exact:true}).click();
 assert.equal(await page.getByRole('menuitem',{name:'Agent Settings',exact:true}).count(),0);
 await page.getByRole('menuitem',{name:'Edit project details',exact:true}).waitFor();
});
test('account name is borderless with pencil next to text and retains inline save',async t=>{
 const {page,writes}=await setup(t);await page.goto(base+'/settings/account');
 const edit=page.getByRole('button',{name:'Edit account name',exact:true});await edit.waitFor();
 assert.equal(await edit.evaluate(el=>getComputedStyle(el).borderTopWidth),'0px');
 const gap=await edit.evaluate(el=>el.querySelector('svg').getBoundingClientRect().left-el.querySelector('span').getBoundingClientRect().right);assert.ok(gap<=12);
 await edit.click();const input=page.getByLabel('Customer / account name',{exact:true});await input.fill('Short name');await input.press('Enter');
 await page.getByRole('status').filter({hasText:'Account name saved.'}).waitFor();assert.deepEqual(writes,[{name:'Short name'}]);
 assert.equal(await page.getByRole('dialog').count(),0);
});
test('members cannot edit either name',async t=>{
 const {page,writes}=await setup(t,{member:true});
 await page.goto(base+'/projects/P1');await page.getByRole('heading',{name:'Customer portal',exact:true}).waitFor();
 assert.equal(await page.getByRole('button',{name:'Edit project name',exact:true}).count(),0);
 await page.goto(base+'/settings/account');await page.getByText('Customer One',{exact:true}).waitFor();
 assert.equal(await page.getByRole('button',{name:'Edit account name',exact:true}).count(),0);assert.deepEqual(writes,[]);
});
test('Admin Dashboard links only the prompt title and description',async t=>{
 const {page}=await setup(t);await page.goto(base+'/platform-admin');
 const link=page.locator('a.workspace-summary-link');await link.waitFor();
 assert.equal(await link.getAttribute('href'),'/platform-admin/prompts');
 assert.equal(await link.evaluate(el=>getComputedStyle(el).textDecorationLine),'none');
 assert.equal(await link.locator('.workspace-row-subtitle').evaluate(el=>getComputedStyle(el).textDecorationLine),'none');
 assert.equal(await link.locator('..').locator('span[aria-hidden="true"]').evaluate(el=>el.closest('a')===null),true);
});
