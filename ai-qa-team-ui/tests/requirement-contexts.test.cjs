// Legacy release contexts remain selectable; their authoring is no longer a generation control.
const {test,before,after}=require('node:test');const assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH||'playwright');const {fixture,base}=require('./qa-agent-fixture.cjs');let browser;
before(async()=>{browser=await chromium.launch({headless:true,channel:'msedge'});});after(async()=>browser?.close());
async function setup(t,release=true){
 const f=await fixture(browser,t);const root='/projects/P1/knowledge/stories/ST1';const calls=[];
 const headers={'access-control-allow-origin':base,'access-control-allow-credentials':'true','access-control-allow-headers':'content-type','access-control-allow-methods':'GET,POST,OPTIONS'};
 const contexts=release?[{context_id:'b'.repeat(32),basis:'approved_change',target_release:'Release 2',status:'active',stale:false}]:[];
 await f.context.route(url=>url.pathname===root+'/requirements',route=>route.fulfill({headers,json:{contexts,rules:[]}}));
 await f.context.route(url=>url.pathname===root+'/analysis',route=>route.fulfill({headers,json:{analysis_id:'a'.repeat(32),status:'reviewed',analysis_mode:'knowledge_aware',findings:[],stale:false}}));
 await f.context.route(url=>url.pathname==='/scenarios/generate-from-story',route=>{
  const url=new URL(route.request().url());calls.push(url.searchParams.get('requirements_context_id'));
  return route.fulfill({headers,json:{scenarios:[{scenario_id:'SC1'}],summary:{message:'Release scenario generated.'}}});
 });
 await f.page.goto(base+'/projects/P1/scenarios?story_id=ST1');await f.page.getByLabel('Requirements for generation',{exact:true}).selectOption('knowledge');
 return {...f,calls};
}
test('one generation selector retains approved legacy release selection without duplicate forms',async t=>{
 const {page,calls}=await setup(t);
 assert.equal(await page.getByLabel('Generation context',{exact:true}).count(),0);
 assert.equal(await page.getByText('Manage release requirements',{exact:true}).count(),0);
 await page.getByLabel('Target release',{exact:true}).selectOption('b'.repeat(32));
 await page.getByRole('button',{name:'Generate scenarios with AI',exact:true}).click();await page.getByText('Release scenario generated.',{exact:true}).waitFor();
 assert.deepEqual(calls,['b'.repeat(32)]);await page.reload();assert.equal(calls.length,1);
});
test('no release chooser appears when no approved releases exist',async t=>{
 const {page}=await setup(t,false);assert.equal(await page.getByLabel('Target release',{exact:true}).count(),0);
 assert.equal(await page.getByLabel('Requirements for generation',{exact:true}).locator('option:not([disabled])').count(),2);
});
