const {test}=require('node:test');const assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH||'playwright');const {fixture,base}=require('./qa-agent-fixture.cjs');
test('story list and detail keep approval separate from an outdated comparison',async t=>{
 const browser=await chromium.launch({headless:true,channel:'msedge'});t.after(()=>browser.close());
 const f=await fixture(browser,t),root='/projects/P1/knowledge';
 const summary={state:'stale',finding_count:1,blocker_count:1,unresolved_finding_count:0,unresolved_blocker_count:0,
  story_approval:{state:'approved',approved_by_name:'Alice Reviewer'},comparison_state:'needs_refresh'};
 const headers={'access-control-allow-origin':base,'access-control-allow-credentials':'true','access-control-allow-headers':'content-type','access-control-allow-methods':'GET,POST,OPTIONS'};
 await f.context.route(url=>url.pathname===root+'/analysis-summaries',route=>route.fulfill({headers,json:{ST1:summary}}));
 await f.context.route(url=>url.pathname===root+'/stories/ST1/analysis',route=>route.fulfill({headers,json:{...summary,analysis_id:'a'.repeat(32),status:'reviewed',analysis_mode:'knowledge_aware',stale:true,summary:'Old comparison',findings:[{finding_id:'F1',category:'missing_detail',severity:'blocker',description:'Old missing detail',question:'Previous question'}]}}));
 await f.page.goto(base+'/projects/P1/stories');await f.page.getByRole('columnheader',{name:'Status',exact:true}).waitFor();
 await f.page.getByRole('link',{name:'Approved',exact:true}).waitFor();await f.page.getByRole('link',{name:'Needs refresh',exact:true}).waitFor();
 await f.page.getByText('0 unresolved findings · 0 blockers',{exact:true}).waitFor();
 await f.page.getByRole('link',{name:'Save draft',exact:true}).click();await f.page.getByRole('status').filter({hasText:/^Approved$/}).waitFor();
 await f.page.getByText('Story review completed · Alice Reviewer',{exact:true}).waitFor();
 assert.equal(await f.page.getByText('Old missing detail',{exact:false}).isVisible(),false);
 const button=f.page.getByRole('link',{name:'Open Scenarios',exact:true});assert.match(await button.getAttribute('class'),/workspace-button/);
 assert.match(await button.getAttribute('href'),/scenarios\?story_id=ST1$/);
 assert.equal(await f.page.getByRole('button',{name:'Generate scenarios with AI',exact:true}).count(),0);
 summary.story_approval.state='needs_review';await f.page.goto(base+'/projects/P1/stories');await f.page.getByRole('link',{name:'Needs review',exact:true}).waitFor();
 assert.equal(await f.page.getByRole('link',{name:'Approved',exact:true}).count(),0);
});
