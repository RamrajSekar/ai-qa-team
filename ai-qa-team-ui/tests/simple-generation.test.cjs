const {test,before,after}=require('node:test');const assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH||'playwright');const {fixture,base}=require('./qa-agent-fixture.cjs');let browser;
before(async()=>{browser=await chromium.launch({headless:true,channel:'msedge'});});after(async()=>browser?.close());
test('reviewed story shows reviewer and explicitly approves story-only generation without another analysis',async t=>{
 const f=await fixture(browser,t);const root='/projects/P1/knowledge/stories/ST1',rows=[],writes=[];
 const headers={'access-control-allow-origin':base,'access-control-allow-credentials':'true','access-control-allow-headers':'content-type','access-control-allow-methods':'GET,POST,OPTIONS'};
 const analysis={analysis_id:'a'.repeat(32),analysis_mode:'knowledge_aware',status:'reviewed',reviewed_by_name:'Alice Reviewer',stale:false,summary:'Reviewed scope',knowledge_version_id:'b'.repeat(32),findings:[{finding_id:'F1',category:'missing_detail',severity:'blocker',description:'Navigation is covered separately.',question:'Scope?'}],resolutions:[{finding_id:'F1',decision:'clarified',rationale:'Separate stories cover navigation.'}]};
 await f.context.route(url=>url.pathname===root+'/analysis',route=>route.fulfill({headers,json:analysis}));
 await f.context.route(url=>url.pathname===root+'/requirements',route=>route.fulfill({headers,json:{contexts:rows,rules:[]}}));
 await f.context.route(url=>url.pathname===root+'/generation-approval',route=>{
  if(route.request().method()==='OPTIONS')return route.fulfill({status:204,headers});
  writes.push(route.request().postDataJSON());const row={context_id:writes[0].request_id,target_release:'Story requirements',basis:'story_only_provisional',status:'approved',stale:false,approver:{approved_by_name:'Alice Reviewer'}};rows.push(row);return route.fulfill({headers,json:row});
 });
 let selectedContext;
 await f.context.route(url=>url.pathname==='/scenarios/generate-from-story',route=>{selectedContext=new URL(route.request().url()).searchParams.get('requirements_context_id');return route.fulfill({headers,json:{scenarios:[{scenario_id:'SC1'}],summary:{message:'Story-only drafts generated.'}}});});
 await f.page.goto(base+'/projects/P1/stories/ST1');await f.page.getByText('Story review completed · Alice Reviewer',{exact:true}).waitFor();
 await f.page.getByRole('link',{name:'Open Scenarios',exact:true}).click();
 await f.page.getByLabel('Source story',{exact:true}).waitFor();
 assert.equal(await f.page.getByLabel('Source story',{exact:true}).inputValue(),'ST1');
 if(process.env.UI_LAYOUT_EVIDENCE)await f.page.locator('.story-generation-bar').screenshot({path:process.env.UI_LAYOUT_EVIDENCE});
 assert.equal(await f.page.getByText('Record a requirement decision or prepare provisional designs',{exact:true}).count(),0);
 await f.page.getByLabel('Requirements for generation',{exact:true}).selectOption('story');
 await f.page.getByRole('button',{name:'Review and approve for generation',exact:true}).click();
 assert.equal(writes.length,0);await f.page.getByRole('button',{name:'Approve for generation',exact:true}).click();
 await f.page.getByText('Approved for generation by Alice Reviewer.',{exact:true}).waitFor();
 await f.page.getByRole('button',{name:'Generate scenarios with AI',exact:true}).click();await f.page.getByText('Story-only drafts generated.',{exact:true}).waitFor();
 assert.equal(selectedContext,rows[0].context_id);assert.equal(writes.length,1);
 assert.equal(f.calls.filter(c=>c.path.endsWith('/analyze')).length,0);
});
