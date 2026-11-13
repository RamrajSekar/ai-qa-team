const {test,before,after}=require('node:test');const assert=require('node:assert/strict');
const{chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH||'playwright');const{mkdirSync}=require('node:fs');
const base=process.env.FEATURE_UI_URL||'http://127.0.0.1:3123';let browser;
before(async()=>{browser=await chromium.launch({channel:'msedge',headless:true});});after(async()=>browser?.close());
async function fixture(t,{admin=true,missingExpected=false,adminOnly=false}={}){
 const context=await browser.newContext();t.after(()=>context.close());await context.addCookies([{name:'access_token',value:'synthetic-only',url:base}]);
 const testcase={testcase_id:'TC1',project_id:'P1',scenario_id:'SC1',title:'Open login page',status:'draft',steps:[{action:'Open the login page',expected:missingExpected?'':'Login page is visible'}]};
 const state={approval_policy:{admin_only:adminOnly,can_approve:admin||!adminOnly},active_version_id:null,review_required:true,context_ready:true,context_error:null,current_context:{story_snapshot:{acceptance_criteria:'The login page is visible.'},knowledge_version_id:null,story_analysis_id:null,source_context_changed:false},approved_expected_rules:[],versions:[]};let saves=0,approvals=0,saved;
 await context.route('http://feature-api.test/**',async route=>{
  const request=route.request(),url=new URL(request.url());const headers={'access-control-allow-origin':base,'access-control-allow-credentials':'true','access-control-allow-headers':'content-type','access-control-allow-methods':'GET,POST,OPTIONS'};
  if(request.method()==='OPTIONS')return route.fulfill({status:204,headers});let json=[];
  if(url.pathname==='/features')json={manual_test_results:true,test_generation:true,automation_execution_ui:false};
  if(url.pathname==='/auth/me')json={user:{name:'Fixture',email:'fixture@example.test',onboarding:{onboarding_status:'completed'},subscription:{usage:{},limits:{}}}};
  if(url.pathname==='/projects')json=[{project_id:'P1',name:'Synthetic',current_user_role:admin?'ADMIN':'TESTER'}];
  if(url.pathname==='/testcases/project-list')json=[testcase];
  if(url.pathname==='/projects/P1/test-results')json={TC1:{approved_version_id:state.active_version_id,manual:null,automated:null}};
  const root='/projects/P1/test-design/cases/TC1';
  if(url.pathname===root){
   if(request.method()==='POST'){saves++;const body=request.postDataJSON();saved=body;assert.deepEqual(body.case.assertions,[]);assert.deepEqual(body.case.cleanup,[]);assert.deepEqual(body.case.acceptance_criteria_refs,[]);assert.deepEqual(body.case.rule_references,[]);const content={...body.case,public_data:Object.fromEntries(body.case.public_data.map(item=>[item.name,item.value]))};json={version_id:'a'.repeat(32),status:'draft',stale:false,case:content,content_digest:'b'.repeat(64)};state.versions=[json];}
   else json=state;
  }
  if(url.pathname===root+'/'+'a'.repeat(32)+'/approve'){approvals++;assert.equal(admin||!adminOnly,true);Object.assign(state.versions[0],{status:'approved',approved_by:'reviewer',approved_by_display_name:'Reviewer Fixture',approved_by_project_role:admin?'ADMIN':'TESTER',approved_at:'2026-11-13T12:00:00Z',approval_policy:adminOnly?'admin_required':'project_member_allowed'});state.active_version_id='a'.repeat(32);state.review_required=false;json=state.versions[0];}
  return route.fulfill({headers,json});
 });
 const page=await context.newPage();page.setDefaultTimeout(30000);page.setDefaultNavigationTimeout(90000);const errors=[];page.on('pageerror',e=>errors.push(e.message));t.after(()=>assert.deepEqual(errors,[]));await page.goto(base+'/projects/P1/testcases');await page.getByRole('button',{name:'Review test case',exact:true}).click();await page.getByText('Review & approve test case',{exact:true}).click();await page.getByRole('status').filter({hasText:'Test case needs review'}).waitFor();return{page,state,get saved(){return saved;},get saves(){return saves;},get approvals(){return approvals;}};
}
async function shot(page,name){if(process.env.APPROVAL_UI_EVIDENCE){mkdirSync(process.env.APPROVAL_UI_EVIDENCE,{recursive:true});await page.screenshot({path:`${process.env.APPROVAL_UI_EVIDENCE}/${name}.png`});}}
test('optional review fields do not block saving; approval requires review of saved version',async t=>{
 const f=await fixture(t);const p=f.page;await p.getByRole('button',{name:'Add Test Step',exact:true}).waitFor();assert.equal(await p.getByLabel('Approved rule IDs (one per line)',{exact:true}).count(),0);const approve=p.getByRole('button',{name:'Approve Test Case',exact:true});assert.equal(await approve.isDisabled(),true);assert.equal(await p.getByRole('button',{name:'Save test case draft'}).isEnabled(),true);
 await p.getByRole('button',{name:'Save test case draft'}).click();await p.getByRole('status').filter({hasText:'Draft saved.'}).waitFor();assert.equal(f.saves,1);assert.equal(await approve.isDisabled(),true);
 await p.getByLabel('I reviewed the saved test steps, expected results and source links.',{exact:true}).check();await p.getByLabel('Expected result 1',{exact:true}).fill('Changed unsaved expectation');assert.equal(await approve.isDisabled(),true);await p.getByRole('button',{name:'Review saved draft',exact:true}).click();assert.equal(await p.getByLabel('Expected result 1',{exact:true}).inputValue(),'Login page is visible');await p.getByLabel('I reviewed the saved test steps, expected results and source links.',{exact:true}).check();await shot(p,'saved-draft-review');await approve.click();await p.getByRole('status').filter({hasText:'Test case approved.'}).waitFor();assert.equal(f.approvals,1);await p.getByText(/Approved by Reviewer Fixture/).first().waitFor();assert.equal(f.saved.case.procedure[0].expected,'Login page is visible');
});
test('missing per-step expected result explains disabled save',async t=>{
 const{page}=await fixture(t,{missingExpected:true});await page.getByText('Each test step needs an action and an expected result.',{exact:true}).waitFor();assert.equal(await page.getByRole('button',{name:'Save test case draft'}).isDisabled(),true);await page.getByLabel('Expected result 1',{exact:true}).fill('Login page is visible');assert.equal(await page.getByRole('button',{name:'Save test case draft'}).isEnabled(),true);
});
test('project member can prepare draft but cannot see approval action',async t=>{
 const{page}=await fixture(t,{admin:false,adminOnly:true});await page.getByText('A project administrator must approve the saved draft. You can prepare it for review.',{exact:true}).waitFor();assert.equal(await page.getByRole('button',{name:'Approve Test Case',exact:true}).count(),0);await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));await shot(page,'review-mobile');
});

test('project-admin signoff can be disabled while explicit member approval remains',async t=>{
 const f=await fixture(t,{admin:false,adminOnly:false});const p=f.page;await p.getByText('Project-admin sign-off is not required. Any authorized project member can review and approve the saved version.',{exact:true}).waitFor();await p.getByRole('button',{name:'Save test case draft'}).click();await p.getByLabel('I reviewed the saved test steps, expected results and source links.',{exact:true}).check();await p.getByRole('button',{name:'Approve Test Case',exact:true}).click();await p.getByRole('status').filter({hasText:'Test case approved.'}).waitFor();assert.equal(f.approvals,1);
});
