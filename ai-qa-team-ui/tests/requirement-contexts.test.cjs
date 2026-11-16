// Real browser, synthetic auth/API: no live model, database or execution.
const {test,before,after}=require('node:test');const assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH||'playwright');
const {fixture,base}=require('./qa-agent-fixture.cjs');let browser;
before(async()=>{browser=await chromium.launch({headless:true,channel:'msedge'});});after(async()=>browser?.close());
async function setup(t,{role='ADMIN',withoutCriteria=false}={}){
 const f=await fixture(browser,t,{role,withoutCriteria});const rows=[],calls=[];let generated=[{scenario_id:'SC_OLD',story_id:'ST1',project_id:'P1',title:'Existing coverage',steps:[],approved:true,status:'approved'}];
 const root='/projects/P1/knowledge/stories/ST1';const analysis={analysis_id:'a'.repeat(32),analysis_mode:'story_only',status:'reviewed',summary:'Reviewed story',knowledge_version_id:null,findings:[],stale:false};
 const headers={'access-control-allow-origin':base,'access-control-allow-credentials':'true','access-control-allow-headers':'content-type','access-control-allow-methods':'GET,POST,OPTIONS'};
 await f.context.route(url=>url.pathname===root+'/analysis',route=>route.fulfill({headers,json:analysis}));
 await f.context.route(url=>url.pathname.startsWith(root+'/requirements'),route=>{
  const request=route.request(),path=new URL(request.url()).pathname;
  if(request.method()==='OPTIONS')return route.fulfill({status:204,headers});
  calls.push({path,method:request.method(),body:request.postData()?request.postDataJSON():null});
  let json;
  if(path===root+'/requirements'&&request.method()==='GET')json={contexts:rows,rules:[{claim_id:'K1',statement:'Signup is visible.'}]};
  else if(path===root+'/requirements'){
   const body=request.postDataJSON();json={...body,context_id:body.request_id,status:'draft',stale:false,effective_decisions:body.decisions,impact:{scenarios:[{id:'SC_OLD',title:'Existing coverage'}],testcases:[]}};rows.push(json);
  }else{
   const parts=path.slice((root+'/requirements/').length).split('/');json=rows.find(row=>row.context_id===parts[0]);assert.ok(json);
   if(parts[1]==='approve'){assert.equal(role,'ADMIN');json.status='approved';json.approver={approved_by_name:'Reviewer',approved_at:'2026-11-16'};}
   if(parts[1]==='activate'){assert.equal(role,'ADMIN');json.status='active';generated.forEach(s=>{s.requirements_review_required=true;s.requirements_review_release=json.target_release;});}
  }
  return route.fulfill({headers,json});
 });
 await f.context.route(url=>url.pathname==='/scenarios',route=>route.fulfill({headers,json:generated}));
 await f.context.route(url=>url.pathname==='/scenarios/generate-from-story',route=>{
  const url=new URL(route.request().url());calls.push({path:url.pathname,context:url.searchParams.get('requirements_context_id'),method:route.request().method()});
  const row=rows.find(row=>row.context_id===url.searchParams.get('requirements_context_id'));assert.ok(row);assert.ok(['approved','active'].includes(row.status));
  generated.push({scenario_id:'SC_NEW',story_id:'ST1',project_id:'P1',title:'Release coverage',steps:[],approved:false,status:'pending',requirements_context_id:row.context_id,design_basis:row.basis,target_release:row.target_release});
  return route.fulfill({headers,json:{scenarios:generated,summary:{message:'1 scenario draft generated.'}}});
 });
 return {...f,rows,calls};
}
test('intentional removal is reviewed, approved, activated and selected explicitly for generation',async t=>{
 const {page,rows,calls}=await setup(t);await page.goto(base+'/projects/P1/stories/ST1');
 await page.getByLabel('Generation context',{exact:true}).waitFor();assert.equal(await page.getByRole('button',{name:'Generate scenarios with AI'}).isDisabled(),true);
 await page.getByText('Record a requirement decision or prepare provisional designs',{exact:true}).click();
 await page.getByLabel('Target release / cycle',{exact:true}).fill('Release 2');
 await page.getByLabel('Change 1',{exact:true}).selectOption('remove');await page.getByLabel('Affected rule 1',{exact:true}).selectOption('K1');
 await page.getByLabel('Expected behavior 1',{exact:true}).fill('Signup is absent; Home remains visible.');await page.getByLabel('Reason 1',{exact:true}).fill('Intentional approved redesign.');
 await page.getByRole('button',{name:'Save requirements draft'}).click();await page.getByRole('region',{name:'Requirements approval review'}).waitFor();
 await page.getByText('Existing coverage (SC_OLD)',{exact:true}).waitFor();
 await page.getByRole('button',{name:'Approve requirements context'}).click();await page.getByText('Approved by Reviewer',{exact:false}).waitFor();
 assert.equal(calls.filter(call=>call.path==='/scenarios/generate-from-story').length,0);
 page.once('dialog',dialog=>dialog.accept());await page.getByRole('button',{name:'Activate release requirements'}).click();
 await page.getByText('Release requirements activated; affected designs marked for review.',{exact:true}).waitFor();
 await page.getByLabel('Generation context',{exact:true}).selectOption(rows[0].context_id);
 assert.equal(calls.filter(call=>call.path==='/scenarios/generate-from-story').length,0);
 await page.getByRole('button',{name:'Generate scenarios with AI'}).click();await page.getByText('1 scenario draft generated.',{exact:true}).waitFor();
 assert.equal(calls.find(call=>call.path==='/scenarios/generate-from-story').context,rows[0].context_id);
 await page.reload();await page.getByRole('button',{name:'Review',exact:true}).waitFor();
 assert.equal(calls.filter(call=>call.path==='/scenarios/generate-from-story').length,1);
});
test('provisional story-only context works without criteria and remains labelled',async t=>{
 const {page,rows}=await setup(t,{withoutCriteria:true});await page.goto(base+'/projects/P1/stories/ST1');
 await page.getByText('Record a requirement decision or prepare provisional designs',{exact:true}).click();
 await page.getByLabel('Design basis',{exact:true}).selectOption('story_only_provisional');await page.getByLabel('Target release / cycle',{exact:true}).fill('Discovery cycle');
 await page.getByRole('button',{name:'Save requirements draft'}).click();await page.getByRole('button',{name:'Approve requirements context'}).click();
 await page.getByText('Requirements context approved. Select it explicitly for generation.',{exact:true}).waitFor();
 await page.getByLabel('Generation context',{exact:true}).selectOption(rows[0].context_id);
 await page.getByRole('button',{name:'Generate scenarios with AI'}).click();await page.getByText('Provisional · story-only',{exact:true}).waitFor();
 assert.equal(rows[0].decisions.length,0);
});
test('clarification decisions persist but cannot be approved as intentional changes',async t=>{
 const {page}=await setup(t);await page.goto(base+'/projects/P1/stories/ST1');
 await page.getByText('Record a requirement decision or prepare provisional designs',{exact:true}).click();
 await page.getByLabel('Target release / cycle',{exact:true}).fill('Release pending');await page.getByLabel('Decision 1',{exact:true}).selectOption('needs_clarification');
 await page.getByLabel('Reason 1',{exact:true}).fill('Product owner must clarify.');await page.getByRole('button',{name:'Save requirements draft'}).click();
 await page.getByRole('region',{name:'Requirements approval review'}).waitFor();assert.equal(await page.getByRole('button',{name:'Approve requirements context'}).isDisabled(),true);
 await page.reload();await page.getByRole('button',{name:'Review',exact:true}).click();await page.getByRole('region',{name:'Requirements approval review'}).locator('p').filter({hasText:'Product owner must clarify.'}).first().waitFor();
 assert.equal(await page.getByRole('button',{name:'Activate release requirements'}).count(),0);
});
