// Actual Edge UI; intercepted auth/API, no live account, MongoDB or model traffic.
const {test,before,after}=require('node:test');const assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH||'playwright');
const {fixture,teach,confirmAll,saveApprove,base}=require('./qa-agent-fixture.cjs');let browser;
before(async()=>{browser=await chromium.launch({headless:true,channel:'msedge'});});after(async()=>browser?.close());

test('leaving Ask clears its result and question without repeating the request',async t=>{
 const {page,calls}=await fixture(browser,t,{ask:true});await page.goto(base+'/projects/P1/knowledge');
 await page.getByRole('tab',{name:'Ask',exact:true}).click();
 await page.getByLabel('Your question',{exact:true}).fill('Which rule applies?');
 await page.getByRole('button',{name:'Ask',exact:true}).click();
 await page.getByRole('region',{name:'Knowledge answer'}).waitFor();
 for(const tab of ['Approved','Review (0)']){
  await page.getByRole('tab',{name:tab,exact:true}).click();
  await page.getByRole('tab',{name:'Ask',exact:true}).click();
  assert.equal(await page.getByLabel('Your question',{exact:true}).inputValue(),'');
  assert.equal(await page.getByRole('region',{name:'Knowledge answer'}).count(),0);
 }
 assert.equal(calls.filter(c=>c.path.endsWith('/ask')).length,1);
});

test('a late Ask response cannot repopulate the fresh tab or trigger a retry',async t=>{
 const {page,context}=await fixture(browser,t,{ask:true});let release,started;
 const held=new Promise(resolve=>{release=resolve;});const entered=new Promise(resolve=>{started=resolve;});let attempts=0;
 t.after(()=>release());
 await context.route('**/knowledge/ask',async route=>{
  attempts++;started();await held;await route.fulfill({headers:{'access-control-allow-origin':base,'access-control-allow-credentials':'true'},json:{status:'not_covered',answer:'Late response',citations:[],knowledge_version_id:null}});
 });
 await page.goto(base+'/projects/P1/knowledge');await page.getByRole('tab',{name:'Ask',exact:true}).click();
 await page.getByLabel('Your question',{exact:true}).fill('Which rule applies?');await page.getByRole('button',{name:'Ask',exact:true}).click();await entered;
 await page.getByRole('tab',{name:'Approved',exact:true}).click();await page.getByRole('tab',{name:'Ask',exact:true}).click();
 const received=page.waitForResponse(response=>response.url().endsWith('/ask'));release();await received;
 assert.equal(await page.getByLabel('Your question',{exact:true}).inputValue(),'');
 assert.equal(await page.getByRole('region',{name:'Knowledge answer'}).count(),0);assert.equal(attempts,1);
});

test('Ask is gated and never sends a question on navigation',async t=>{
 const f=await fixture(browser,t);await f.page.goto(base+'/projects/P1/knowledge');
 await f.page.getByRole('tab',{name:'Teach',exact:true}).waitFor();
 assert.equal(await f.page.getByRole('tab',{name:'Teach',exact:true}).getAttribute('aria-selected'),'true');
 assert.equal(await f.page.getByRole('tab',{name:'Ask',exact:true}).count(),0);
 assert.equal(f.calls.filter(c=>c.path.endsWith('/ask')).length,0);
});

test('Teach is first and initially selected even when Ask is enabled',async t=>{
 const {page,calls}=await fixture(browser,t,{ask:true});await page.goto(base+'/projects/P1/knowledge');
 const tab=page.getByRole('tab',{name:'Teach',exact:true});await tab.waitFor();
 assert.equal(await tab.getAttribute('aria-selected'),'true');
 assert.deepEqual(await page.getByRole('tablist',{name:'QA Agent workflow'}).getByRole('tab').allTextContents(),['Teach','Ask','Review (0)','Approved']);
 assert.equal(await page.getByLabel('Your question',{exact:true}).count(),0);
 assert.equal(calls.filter(call=>call.path.endsWith('/ask')).length,0);
});

test('Ask returns cited current knowledge and proposes a reviewed correction',async t=>{
 const f=await fixture(browser,t,{ask:true});const {page,calls,versions}=f;await page.goto(base+'/projects/P1/knowledge');
 await teach(page,'Source rules','Rule one.');await confirmAll(page);await saveApprove(page);
 await page.getByRole('tab',{name:'Ask',exact:true}).click();assert.equal(calls.filter(c=>c.path.endsWith('/ask')).length,0);
 await page.getByLabel('Your question',{exact:true}).fill('Which rule applies?');
 await page.getByRole('button',{name:'Ask',exact:true}).click();await page.getByRole('region',{name:'Knowledge answer'}).waitFor();
 await page.getByText('Rule one applies.',{exact:true}).waitFor();
 await page.getByRole('button',{name:'Review source',exact:true}).click();await page.getByRole('dialog',{name:'Source evidence'}).waitFor();
 await page.getByRole('button',{name:'Close evidence',exact:true}).click();
 await page.getByRole('button',{name:'Propose correction',exact:true}).click();await page.getByRole('heading',{name:'Review correction'}).waitFor();
 assert.equal(versions.length,1);assert.equal(calls.filter(c=>c.path.endsWith('/ask')).length,1);
});

test('uncertain Ask requires an explicit retry and refresh does not repeat it',async t=>{
 const f=await fixture(browser,t,{ask:true});const {page,context}=f;let attempts=0;
 await context.route('**/knowledge/ask',async route=>{attempts++;if(attempts===1)return route.fulfill({status:503,headers:{'access-control-allow-origin':base,'access-control-allow-credentials':'true'},json:{detail:'Synthetic provider unavailable.'}});return route.fallback();});
 await page.goto(base+'/projects/P1/knowledge');await page.getByRole('tab',{name:'Ask',exact:true}).click();
 await page.getByLabel('Your question',{exact:true}).fill('What is known?');await page.getByRole('button',{name:'Ask',exact:true}).click();
 await page.getByRole('alert').filter({hasText:'Synthetic provider unavailable.'}).waitFor();
 page.once('dialog',dialog=>dialog.dismiss());await page.getByRole('button',{name:'Submit new request explicitly'}).click();assert.equal(attempts,1);
 page.once('dialog',dialog=>dialog.accept());await page.getByRole('button',{name:'Submit new request explicitly'}).click();await page.getByText('Not covered',{exact:true}).waitFor();assert.equal(attempts,2);
 await page.reload();await page.getByRole('tab',{name:'Ask',exact:true}).click();assert.equal(attempts,2);
});
