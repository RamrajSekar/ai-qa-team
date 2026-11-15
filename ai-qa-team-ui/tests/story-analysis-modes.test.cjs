// Actual browser UX with intercepted auth/API; not a live Mongo/model check.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH||'playwright');
const {fixture,base}=require('./qa-agent-fixture.cjs');

test('story-only review without acceptance criteria is labelled and survives refresh',async t=>{
 const browser=await chromium.launch({headless:true,channel:process.env.PLAYWRIGHT_CHANNEL||'msedge'});t.after(()=>browser.close());
 const f=await fixture(browser,t,{withoutCriteria:true});
 await f.page.goto(base+'/projects/P1/stories/ST1');
 await f.page.getByRole('heading',{name:'Review story clarity'}).waitFor();
 assert.equal(f.calls.filter(c=>c.path.endsWith('/analyze')).length,0);
 await f.page.getByRole('button',{name:'Analyze with AI'}).click();
 await f.page.getByText('Story-only analysis — not validated',{exact:false}).waitFor();
 assert.equal(await f.page.getByRole('link',{name:'Inspect approved knowledge version'}).count(),0);
 await f.page.getByLabel('Clarification or rationale').fill('Confirm after the user saves.');
 await f.page.getByRole('button',{name:'Approve analysis review (project admin)'}).click();
 await f.page.getByRole('status').filter({hasText:/^Reviewed$/}).waitFor();
 await f.page.reload();
 await f.page.getByRole('status').filter({hasText:/^Reviewed$/}).waitFor();
 assert.equal(f.calls.filter(c=>c.path.endsWith('/analyze')).length,1);
 await f.page.getByText('Reviewed: Confirm after the user saves.',{exact:true}).waitFor();
});
