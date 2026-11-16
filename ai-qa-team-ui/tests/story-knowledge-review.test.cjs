// Real local browser, intercepted auth/API; no model or shared database.
const {test,before,after}=require('node:test');
const assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH||'playwright');
const {fixture,base}=require('./qa-agent-fixture.cjs');
let browser;
before(async()=>{browser=await chromium.launch({headless:true,channel:'msedge'});});
after(async()=>browser?.close());
async function setup(t,role='ADMIN'){
 const f=await fixture(browser,t,{role});
 const root='/projects/P1/knowledge/stories/ST1'; const reviews=[],calls=[];
 const analysis={analysis_id:'e'.repeat(32),status:'needs_review',analysis_mode:'knowledge_aware',stale:false,
  knowledge_version_id:'b'.repeat(32),summary:'Review the intentional change.',findings:[{finding_id:'F1',category:'knowledge_conflict',severity:'blocker',description:'Signup visibility differs.',question:'Intentional?',criterion_quote:'Signup must be hidden.',knowledge_claim_id:'K1'}]};
 const headers={'access-control-allow-origin':base,'access-control-allow-credentials':'true','access-control-allow-headers':'content-type','access-control-allow-methods':'GET,POST,OPTIONS'};
 await f.context.route(url=>url.pathname===root+'/analysis',route=>route.fulfill({headers,json:analysis}));
 await f.context.route(url=>url.pathname.startsWith(root+'/change-reviews'),route=>{
  const request=route.request(),path=new URL(request.url()).pathname;
  if(request.method()==='OPTIONS')return route.fulfill({status:204,headers});
  calls.push({method:request.method(),path});let json;
  if(request.method()==='GET')json={knowledge_version_id:'b'.repeat(32),rules:[{claim_id:'K1',statement:'Signup is visible.'}],reviews};
  else if(path===root+'/change-reviews'){
   const body=request.postDataJSON();json={...body,review_id:body.request_id,status:'submitted',stale:false,changes:body.decisions.filter(d=>d.decision==='intentional_change').map(d=>({action:d.action,before:'Signup is visible.',after:d.action==='remove'?null:d.expected_result,expected_behavior:d.expected_result,reason:d.rationale})),impact:{scenarios:[{id:'SC1',title:'Existing signup coverage'}],testcases:[]}};reviews.push(json);
  }else{
   assert.equal(role,'ADMIN');json=reviews[0];json.approver={approved_by_name:'Alice',approved_at:'2026-11-16'};
   json.status=json.timing==='later'&&path.endsWith('/approve')?'approved_pending':'completed';
   if(json.status==='completed')analysis.stale=true;
  }
  return route.fulfill({headers,json});
 });
 await f.page.goto(base+'/projects/P1/stories/ST1');
 await f.page.getByLabel('Conflict decision 1',{exact:true}).waitFor();
 return {...f,reviews,calls};
}
test('admin compares changes then approves once; refresh does not repeat a write',async t=>{
 const {page,reviews,calls}=await setup(t);
 await page.getByText('Signup is visible.',{exact:true}).waitFor();
 await page.getByLabel('New behavior 1',{exact:true}).fill('Signup must be hidden.');
 await page.getByLabel('Change reason 1',{exact:true}).fill('Intentional release change.');
 await page.getByRole('button',{name:'Review changes',exact:true}).click();
 await page.getByRole('region',{name:'Story change summary'}).waitFor();
 assert.equal(calls.filter(c=>c.path.endsWith('/approve')).length,0);
 await page.getByRole('button',{name:'Approve story and update knowledge',exact:true}).click();
 await page.getByRole('region',{name:'Story change summary'}).getByText('Story change approved and knowledge updated.',{exact:true}).waitFor();
 assert.equal(reviews[0].status,'completed');const writes=calls.filter(c=>c.method==='POST').length;
 await page.reload();assert.equal(calls.filter(c=>c.method==='POST').length,writes);
});
test('member submits and resumes review without approval privileges',async t=>{
 const {page,reviews,calls}=await setup(t,'MEMBER');
 await page.getByLabel('Change reason 1',{exact:true}).fill('Please confirm this enhancement.');
 await page.getByRole('button',{name:'Submit for review',exact:true}).click();
 await page.getByText('Submitted for Project Admin review.',{exact:true}).waitFor();
 assert.equal(await page.getByRole('button',{name:'Approve story and update knowledge'}).count(),0);
 await page.reload();await page.getByRole('button',{name:'Review',exact:true}).click();
 await page.getByRole('region',{name:'Story change summary'}).getByText('Reason: Please confirm this enhancement.',{exact:true}).waitFor();
 assert.equal(reviews.length,1);assert.equal(calls.filter(c=>c.path.endsWith('/approve')).length,0);
});
test('future approval retains an explicit activation step',async t=>{
 const {page,reviews}=await setup(t);
 await page.getByLabel('Change reason 1',{exact:true}).fill('Planned for release five.');
 await page.getByLabel('Knowledge change timing',{exact:true}).selectOption('later');
 await page.getByLabel('Change target release',{exact:true}).fill('Release 5');
 await page.getByRole('button',{name:'Review changes',exact:true}).click();
 await page.getByRole('button',{name:'Approve for future release',exact:true}).click();
 await page.getByText('Approved for the future release. Current knowledge is unchanged.',{exact:true}).waitFor();
 assert.equal(reviews[0].status,'approved_pending');
 await page.getByRole('button',{name:'Activate knowledge update',exact:true}).click();
 await page.getByRole('region',{name:'Story change summary'}).getByText('Story change approved and knowledge updated.',{exact:true}).waitFor();
 assert.equal(reviews[0].status,'completed');
});
