const {test,before,after}=require('node:test');const assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH||'playwright');
const {fixture,teach,confirmAll,saveApprove,base}=require('./qa-agent-fixture.cjs');let browser;
before(async()=>{browser=await chromium.launch({headless:true,channel:process.env.PLAYWRIGHT_CHANNEL||'msedge'});});after(async()=>browser?.close());
test('admin creates project, teaches three rules, adds fourth, resumes clarification and corrects one',async t=>{
 const {page,calls,versions,reviews}=await fixture(browser,t,{empty:true});
 await page.goto(base+'/dashboard');await page.getByRole('button',{name:'+ Create Project',exact:true}).click();
 await page.getByLabel('Project Name',{exact:true}).fill('Synthetic project');await page.getByRole('button',{name:'Create Project',exact:true}).click();
 await page.getByText('Synthetic project',{exact:true}).first().waitFor();
 await page.goto(base+'/projects/P1/knowledge');await page.getByRole('link',{name:'QA Agent',exact:true}).waitFor();
 await teach(page,'Three rules','Rule one.\nRule two.\nRule three.');await confirmAll(page);await saveApprove(page);
 assert.equal(await page.getByRole('article',{name:'Approved rule',exact:true}).count(),3);
 await page.reload();await page.getByRole('article',{name:'Approved rule',exact:true}).first().waitFor();assert.equal(await page.getByRole('article',{name:'Approved rule',exact:true}).count(),3);
 await teach(page,'Fourth rule','Rule four.');await confirmAll(page);
 assert.equal(await page.getByRole('button',{name:'Save for approval',exact:true}).isDisabled(),true);
 const extracts=()=>calls.filter(c=>c.path.endsWith('/extract')).length;assert.equal(extracts(),2);
 await page.goto(base+'/projects');await page.goBack();await page.getByLabel('When does rule four apply?',{exact:true}).waitFor();assert.equal(await page.getByLabel('When does rule four apply?',{exact:true}).inputValue(),'');assert.equal(extracts(),2);
 const answerSaved=page.waitForResponse(response=>response.url().endsWith('/review')&&response.request().method()==='POST');await page.getByLabel('When does rule four apply?',{exact:true}).fill('After saving.');await answerSaved;
 await page.getByRole('status').filter({hasText:/^Review progress saved$/}).waitFor();
 await page.goto(base+'/projects');await page.goBack();
 await page.getByLabel('When does rule four apply?',{exact:true}).waitFor();assert.equal(await page.getByLabel('When does rule four apply?',{exact:true}).inputValue(),'After saving.');assert.equal(extracts(),2);
 await saveApprove(page);assert.equal(await page.getByRole('article',{name:'Approved rule',exact:true}).count(),4);
 const before=structuredClone(versions[0].claims);await page.getByRole('article',{name:'Approved rule',exact:true}).first().getByRole('button',{name:'Correct rule',exact:true}).click();
 const card=page.getByRole('article',{name:'Proposal 1',exact:true});await card.getByRole('button',{name:'Edit',exact:true}).click();const correctionSaved=page.waitForResponse(response=>response.url().endsWith('/review')&&response.request().method()==='POST');await page.getByLabel('Rule statement',{exact:true}).fill('Rule one, clarified.');await correctionSaved;
 await page.getByRole('status').filter({hasText:/^Review progress saved$/}).waitFor();await card.getByRole('button',{name:'Confirm',exact:true}).click();await page.getByRole('status').filter({hasText:/^Review progress saved$/}).waitFor();await saveApprove(page);
 assert.equal(versions[0].claims[0].statement,'Rule one, clarified.');assert.deepEqual(versions[0].claims.slice(1),before.slice(1));assert.equal(extracts(),2);
 await page.getByRole('article',{name:'Approved rule',exact:true}).first().getByRole('button',{name:'Inspect source',exact:true}).click();await page.getByRole('dialog',{name:'Source evidence',exact:true}).waitFor();await page.getByRole('button',{name:'Close evidence',exact:true}).click();
 if(process.env.QA_AGENT_SCREENSHOT){await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:process.env.QA_AGENT_SCREENSHOT,fullPage:true});}
 await page.setViewportSize({width:390,height:844});assert.ok(await page.locator('main').evaluate(node=>node.scrollWidth<=node.clientWidth+1));
});
test('member can save review, cannot approve, and admin can resume it',async t=>{
 const f=await fixture(browser,t,{role:'TESTER'});const {page}=f;await page.goto(base+'/projects/P1/knowledge');
 await teach(page,'Member training','Rule one.');await confirmAll(page);await page.getByRole('button',{name:'Save for approval',exact:true}).click();
 await page.getByText('A project administrator must approve this saved knowledge.',{exact:false}).waitFor();assert.equal(await page.getByRole('button',{name:'Approve knowledge',exact:true}).count(),0);
 await page.reload();await page.getByText('A project administrator must approve this saved knowledge.',{exact:false}).waitFor();assert.equal(f.calls.filter(c=>c.path.endsWith('/extract')).length,1);
 f.setRole('ADMIN');await page.reload();await page.getByRole('button',{name:'Approve knowledge',exact:true}).click();await page.getByRole('status').filter({hasText:'Knowledge approved and saved.'}).waitFor();
});
test('rejecting proposals preserves knowledge and removal requires explicit confirmation',async t=>{
 const {page}=await fixture(browser,t);await page.goto(base+'/projects/P1/knowledge');await teach(page,'Original','Rule one.');await confirmAll(page);await saveApprove(page);
 await teach(page,'Rejected addition','Unwanted rule.');await page.getByRole('article',{name:'Proposal 1',exact:true}).getByRole('button',{name:'Reject',exact:true}).click();await page.getByRole('status').filter({hasText:/^Review progress saved$/}).waitFor();
 assert.equal(await page.getByRole('article',{name:'Approved rule',exact:true}).count(),1);assert.equal(await page.getByRole('button',{name:'Save for approval',exact:true}).isDisabled(),true);
 page.once('dialog',dialog=>dialog.dismiss());await page.getByRole('button',{name:'Remove rule',exact:true}).click();assert.equal(await page.getByRole('article',{name:'Approved rule',exact:true}).count(),1);
 page.once('dialog',dialog=>dialog.accept());await page.getByRole('button',{name:'Remove rule',exact:true}).click();await page.getByRole('button',{name:'Save for approval',exact:true}).click();await page.getByText('Removal',{exact:true}).waitFor();assert.equal(await page.getByRole('article',{name:'Approved rule',exact:true}).count(),1);
 await page.getByRole('button',{name:'Approve knowledge',exact:true}).click();await page.getByRole('status').filter({hasText:'Knowledge approved and saved.'}).waitFor();assert.equal(await page.getByRole('article',{name:'Approved rule',exact:true}).count(),0);
});


test('uncertain extraction is not repeated on reload and retry requires confirmation',async t=>{
 const f=await fixture(browser,t);const {page,context,reviews}=f;let attempts=0;
 await context.route('**/knowledge/training/*/extract',async route=>{
  attempts++;if(attempts===1){reviews[0].extraction_state='uncertain';reviews[0].attempt=1;return route.fulfill({status:500,headers:{'access-control-allow-origin':base,'access-control-allow-credentials':'true'},json:{detail:'Extraction outcome uncertain.'}});}return route.fallback();
 });
 await page.goto(base+'/projects/P1/knowledge');await page.getByLabel('Training title',{exact:true}).fill('Interrupted');await page.getByLabel('What should your QA Agent know?',{exact:true}).fill('Rule one.');await page.getByRole('button',{name:'Teach agent',exact:true}).click();
 await page.getByRole('alert').filter({hasText:'Extraction outcome uncertain.'}).waitFor();
 await page.reload();const retry=page.getByRole('button',{name:'Retry extraction explicitly',exact:true});await retry.waitFor();assert.equal(attempts,1);
 page.once('dialog',dialog=>dialog.dismiss());await retry.click();assert.equal(attempts,1);
 page.once('dialog',dialog=>dialog.accept());await retry.click();await page.getByRole('article',{name:'Proposal 1',exact:true}).waitFor();assert.equal(attempts,2);
});


test('Clarify persists a reviewer question and answer across refresh before approval',async t=>{
 const {page,versions,calls}=await fixture(browser,t);await page.goto(base+'/projects/P1/knowledge');await teach(page,'Clarify rule','Rule one.');
 await page.getByRole('article',{name:'Proposal 1',exact:true}).getByRole('button',{name:'Clarify',exact:true}).click();
 await page.getByRole('status').filter({hasText:/^Review progress saved$/}).waitFor();
 const questionSaved=page.waitForResponse(response=>response.url().endsWith('/review')&&response.request().method()==='POST');await page.getByLabel('Clarification question',{exact:true}).fill('Who saves?');await questionSaved;await page.getByRole('status').filter({hasText:/^Review progress saved$/}).waitFor();
 await page.reload();await page.getByLabel('Clarification question',{exact:true}).waitFor();assert.equal(await page.getByLabel('Clarification question',{exact:true}).inputValue(),'Who saves?');
 const answerSaved=page.waitForResponse(response=>response.url().endsWith('/review')&&response.request().method()==='POST');await page.getByLabel('Clarification answer',{exact:true}).fill('The reviewer.');await answerSaved;await page.getByRole('status').filter({hasText:/^Review progress saved$/}).waitFor();
 await confirmAll(page);await saveApprove(page);assert.equal(versions[0].clarification_answers['Who saves?'],'The reviewer.');assert.equal(calls.filter(c=>c.path.endsWith('/extract')).length,1);
});
