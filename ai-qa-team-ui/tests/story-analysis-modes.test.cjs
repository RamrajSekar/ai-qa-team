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
 await f.page.getByText('Story-only review.',{exact:false}).waitFor();
 assert.equal(await f.page.getByRole('link',{name:'Inspect approved knowledge version'}).count(),0);
 await f.page.getByLabel('Clarification or rationale').fill('Confirm after the user saves.');
 await f.page.getByRole('button',{name:'Approve analysis review (project admin)'}).click();
 await f.page.getByRole('status').filter({hasText:/^Approved$/}).waitFor();
 await f.page.reload();
 await f.page.getByRole('status').filter({hasText:/^Approved$/}).waitFor();
 assert.equal(f.calls.filter(c=>c.path.endsWith('/analyze')).length,1);
 await f.page.getByText('Reviewed: Confirm after the user saves.',{exact:true}).waitFor();
});


test('explicit comparison shows excluded rules and refresh never repeats analysis',async t=>{
 const browser=await chromium.launch({headless:true,channel:'msedge'});t.after(()=>browser.close());
 const {page,context}=await fixture(browser,t);let latest=null;const modes=[];
 const headers={'access-control-allow-origin':base,'access-control-allow-credentials':'true','access-control-allow-headers':'content-type','access-control-allow-methods':'GET,POST,OPTIONS'};
 await context.route(url=>url.pathname.endsWith('/stories/ST1/analysis'),route=>route.fulfill({headers,json:latest}));
 await context.route(url=>url.pathname.endsWith('/stories/ST1/analyze'),route=>{
  if(route.request().method()==='OPTIONS')return route.fulfill({status:204,headers});
  const mode=new URL(route.request().url()).searchParams.get('analysis_mode');modes.push(mode);
  latest={analysis_id:'a'.repeat(32),status:'needs_review',stale:false,summary:'Review independent rules',analysis_mode:mode,knowledge_version_id:mode==='knowledge_aware'?'b'.repeat(32):null,findings:[],excluded_knowledge_claims:mode==='knowledge_aware'?[{claim_id:'K2',statement:'Show Signup.',source_id:'c'.repeat(32),reason:'Supported only by this story; not independent evidence.'}]:[]};
  return route.fulfill({headers,json:latest});
 });
 await page.goto(base+'/projects/P1/stories/ST1');await page.getByLabel('Analysis mode',{exact:true}).waitFor();
 assert.equal(await page.getByLabel('Analysis mode',{exact:true}).inputValue(),'story_only');
 await page.getByLabel('Analysis mode',{exact:true}).selectOption('knowledge_aware');assert.equal(modes.length,0);
 await page.getByRole('button',{name:'Analyze with AI'}).click();
 await page.getByRole('region',{name:'Excluded knowledge rules'}).waitFor();await page.getByText('Show Signup.',{exact:true}).waitFor();
 await page.reload();await page.getByRole('region',{name:'Excluded knowledge rules'}).waitFor();assert.deepEqual(modes,['knowledge_aware']);
 await page.getByLabel('Analysis mode',{exact:true}).selectOption('story_only');await page.getByRole('button',{name:'Analyze with AI'}).click();
 await page.getByText('Story-only review.',{exact:false}).waitFor();
 assert.equal(await page.getByRole('region',{name:'Excluded knowledge rules'}).count(),0);
 assert.deepEqual(modes,['knowledge_aware','story_only']);
});

test('no eligible rules offers explicit story clarity without a silent retry',async t=>{
 const browser=await chromium.launch({headless:true,channel:'msedge'});t.after(()=>browser.close());
 const {page,context}=await fixture(browser,t);const calls=[];
 await context.route(url=>url.pathname.endsWith('/stories/ST1/analyze'),route=>{
  if(route.request().method()==='OPTIONS')return route.fallback();
  const mode=new URL(route.request().url()).searchParams.get('analysis_mode');calls.push(mode);
  if(mode==='story_only')return route.fallback();
  return route.fulfill({status:409,headers:{'access-control-allow-origin':base,'access-control-allow-credentials':'true'},json:{detail:'No independently sourced approved rules remain. Excluded same-story rules: K2: Show Signup. Choose Story clarity explicitly; no AI request was made.'}});
 });
 await page.goto(base+'/projects/P1/stories/ST1');await page.getByLabel('Analysis mode',{exact:true}).selectOption('knowledge_aware');
 await page.getByRole('button',{name:'Analyze with AI'}).click();await page.getByRole('alert').filter({hasText:'Choose Story clarity explicitly'}).waitFor();
 assert.deepEqual(calls,['knowledge_aware']);
 await page.getByLabel('Analysis mode',{exact:true}).selectOption('story_only');await page.getByRole('button',{name:'Analyze with AI'}).click();
 await page.getByText('Story-only review.',{exact:false}).waitFor();assert.deepEqual(calls,['knowledge_aware','story_only']);
});


test('story description evidence is labelled separately from acceptance criteria',async t=>{
 const browser=await chromium.launch({headless:true,channel:'msedge'});t.after(()=>browser.close());
 const {page,context}=await fixture(browser,t);
 const headers={'access-control-allow-origin':base,'access-control-allow-credentials':'true'};
 const analysis={analysis_id:'a'.repeat(32),status:'needs_review',stale:false,summary:'Clarify record types',analysis_mode:'story_only',knowledge_version_id:null,findings:[{finding_id:'F1',category:'ambiguity',severity:'warning',description:'Default type is missing',question:'Which type is the default?',criterion_quote:null,story_quote:'Employee, Guest, Agent',story_field:'description'}]};
 await context.route(url=>url.origin==='http://feature-api.test'&&url.pathname.endsWith('/stories/ST1/analysis'),route=>route.fulfill({headers,json:analysis}));
 await page.goto(base+'/projects/P1/stories/ST1');
 await page.getByText('Story description: Employee, Guest, Agent',{exact:true}).waitFor();
 assert.equal(await page.getByText('Acceptance criterion: Employee, Guest, Agent',{exact:true}).count(),0);
});
