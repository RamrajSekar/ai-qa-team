const {test,before,after}=require('node:test');const assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH||'playwright');const {fixture,base}=require('./qa-agent-fixture.cjs');let browser;
before(async()=>{browser=await chromium.launch({headless:true,channel:'msedge'});});after(async()=>browser?.close());
for(const role of ['ADMIN','TESTER'])test(`approved story generates in one action for ${role} without repeated approval or metadata reads`,async t=>{
 const f=await fixture(browser,t,{role});let generations=0;
 const headers={'access-control-allow-origin':base,'access-control-allow-credentials':'true','access-control-allow-headers':'content-type','access-control-allow-methods':'GET,POST,OPTIONS'};
 await f.context.route(url=>url.pathname==='/scenarios/generate-from-story',route=>{
  if(route.request().method()==='OPTIONS')return route.fulfill({headers,status:204});
  generations++;assert.equal(new URL(route.request().url()).searchParams.get('approved_story'),'true');
  return route.fulfill({headers,json:{scenarios:[{scenario_id:'SC1'}],summary:{message:'Drafts generated from approved story.'}}});
 });
 await f.page.goto(base+'/projects/P1/scenarios?story_id=ST1');
 await f.page.getByLabel('Source story',{exact:true}).waitFor();
 assert.equal(await f.page.getByLabel('Source story',{exact:true}).inputValue(),'ST1');
 assert.equal(await f.page.getByLabel('Requirements for generation',{exact:true}).count(),0);
 assert.equal(await f.page.getByRole('button',{name:'Review and approve for generation',exact:true}).count(),0);
 await f.page.getByText('Selected Story',{exact:true}).waitFor();
 assert.equal(generations,0);
 const button=f.page.getByRole('button',{name:'Generate scenarios with AI',exact:true});assert.equal(await button.isEnabled(),true);
 await button.click();await f.page.getByText('Drafts generated from approved story.',{exact:true}).waitFor();
 assert.equal(generations,1);
 assert.equal(f.calls.filter(c=>c.path.endsWith('/generation-approval')||c.path.endsWith('/requirements')||c.path.endsWith('/analysis')||c.path.endsWith('/analyze')).length,0);
});
