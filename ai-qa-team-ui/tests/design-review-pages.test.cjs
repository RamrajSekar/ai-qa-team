// Intercepted UI regression only. No real authentication, database, AI or browser-provider calls.
const {test,before,after}=require('node:test');
const assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH||'playwright');
const {mkdirSync}=require('node:fs');
const base=process.env.FEATURE_UI_URL||'http://127.0.0.1:3123';let browser;
before(async()=>{browser=await chromium.launch({headless:true,channel:'msedge'});});
after(async()=>browser?.close());
async function fixture(t,{execution=false}={}){
 const context=await browser.newContext();t.after(()=>context.close());
 await context.addCookies([{name:'access_token',value:'synthetic-only',url:base}]);
 const story={id:'ST1',story_id:'ST1',project_id:'P1',title:'Save an order',acceptance_criteria:'Order saved appears',created_at:'2026-11-12'};
 const project={project_id:'P1',name:'Design workspace',current_user_role:'ADMIN'};
 const scenarios=[{scenario_id:'SC1',story_id:'ST1',project_id:'P1',title:'Save a valid order',approved:true,steps:[],created_by:'fixture@example.test'},{scenario_id:'SC2',story_id:'ST1',project_id:'P1',title:'Reject empty order',approved:false,steps:[]}];
 const cases=[{testcase_id:'TC1',scenario_id:'SC1',project_id:'P1',title:'Save order with required data',status:'draft',steps:[{action:'Click Save order',expected:'Order saved'}],created_by:'fixture@example.test'}];
 const calls=[];let historyFails=false;
 await context.route('http://feature-api.test/**',async route=>{
  const request=route.request(),url=new URL(request.url());calls.push({path:url.pathname,method:request.method()});
  const headers={'access-control-allow-origin':base,'access-control-allow-credentials':'true','access-control-allow-headers':'content-type','access-control-allow-methods':'GET,POST,PATCH,DELETE,OPTIONS'};
  if(request.method()==='OPTIONS')return route.fulfill({status:204,headers});let json=[];
  if(url.pathname==='/features')json={story_management:true,scenario_generation:true,test_generation:true,test_execution_ui:execution,approved_visual_run_admission:true};
  if(url.pathname==='/auth/me')json={user:{email:'fixture@example.test',name:'Fixture',onboarding:{onboarding_status:'completed'},subscription:{usage:{},limits:{}}}};
  if(url.pathname==='/projects')json=[project];if(url.pathname==='/projects/P1')json=project;
  if(url.pathname==='/stories')json=[story,{...story,story_id:'ST2',title:'Cancel an order',acceptance_criteria:''}];
  if(url.pathname==='/stories/ST1'){
   if(request.method()==='DELETE')return route.fulfill({status:409,headers,json:{detail:'Dependent records protect this story.'}});json=story;
  }
  if(url.pathname==='/scenarios/project-list'||url.pathname==='/scenarios')json=scenarios;
  if(url.pathname==='/testcases/project-list'||url.pathname==='/testcases/testcases')json=cases;
  if(url.pathname==='/environments')json=[{env_id:'E1',project_id:'P1',name:'Synthetic environment',credentials:[]}];
  if(url.pathname==='/execute'){
   if(historyFails)return route.fulfill({status:503,headers,json:{detail:'Unavailable'}});
   json=[{execution_id:'EX1',project_id:'P1',testcase_id:'TC1',status:'failed',started_at:'2026-11-12T12:00:00Z'},{execution_id:'EX2',project_id:'P2',status:'passed'}];
  }
  return route.fulfill({headers,json});
 });
 const page=await context.newPage();page.setDefaultTimeout(30000);page.setDefaultNavigationTimeout(90000);
 const errors=[];page.on('pageerror',e=>errors.push(e.message));t.after(()=>assert.deepEqual(errors,[]));
 return{page,calls,setHistoryFails:value=>historyFails=value};
}
async function capture(page,name){if(!process.env.DESIGN_REVIEW_EVIDENCE)return;mkdirSync(process.env.DESIGN_REVIEW_EVIDENCE,{recursive:true});await page.screenshot({path:`${process.env.DESIGN_REVIEW_EVIDENCE}/${name}.png`,fullPage:true});}

test('stories search, protected deletion feedback and accessible cancellation',async t=>{
 const{page}=await fixture(t);await page.goto(base+'/projects/P1/stories');await page.getByRole('link',{name:'Save an order',exact:true}).waitFor();
 await page.getByRole('searchbox',{name:'Search stories'}).fill('Save');assert.equal(await page.getByRole('link',{name:'Cancel an order',exact:true}).count(),0);
 await page.getByRole('button',{name:'Delete',exact:true}).click();const dialog=page.getByRole('dialog');await dialog.getByRole('button',{name:'Delete',exact:true}).click();await dialog.getByRole('alert').filter({hasText:'Dependent records'}).waitFor();
 await dialog.getByRole('button',{name:'Cancel',exact:true}).click();await dialog.waitFor({state:'hidden'});
 await page.getByRole('searchbox').fill('unmatched');await page.getByText('No matching stories',{exact:true}).waitFor();
 await page.getByRole('searchbox').fill('');await capture(page,'stories');
 await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));await capture(page,'stories-mobile');
});
test('scenario review separates approval and coverage with page-local filters',async t=>{
 const{page,calls}=await fixture(t);await page.goto(base+'/projects/P1/scenarios');await page.getByRole('heading',{name:'Save a valid order'}).waitFor();
 await page.getByLabel('Status',{exact:true}).selectOption('pending');await page.getByRole('heading',{name:'Save a valid order'}).waitFor({state:'hidden'});assert.equal(await page.getByRole('heading',{name:'Save a valid order'}).count(),0);await page.getByRole('heading',{name:'Reject empty order'}).waitFor();
 await page.getByLabel('Status',{exact:true}).selectOption('all');await page.getByRole('searchbox').fill('SC1');await page.getByRole('heading',{name:'Save a valid order'}).waitFor();assert.equal(calls.filter(x=>x.method==='POST').length,0);await capture(page,'scenarios');await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));await capture(page,'scenarios-mobile');
});
test('test cases retain expected results and hide execution entry when disabled',async t=>{
 const{page}=await fixture(t);await page.goto(base+'/projects/P1/testcases');await page.getByRole('heading',{name:'Save order with required data'}).waitFor();
 await page.getByText('Steps and expected results',{exact:true}).click();await page.getByText('Expected result — Order saved',{exact:true}).waitFor();assert.equal(await page.getByRole('link',{name:'Review execution setup'}).count(),0);
 await page.getByRole('button',{name:'Add or generate test case'}).click();await page.getByLabel('Approved source scenario').selectOption('SC1');assert.equal(await page.getByRole('option',{name:/SC2/}).count(),0);await capture(page,'testcases');await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));await capture(page,'testcases-mobile');
});
test('history filters project records, retries read failures and never submits execution',async t=>{
 const{page,calls,setHistoryFails}=await fixture(t);await page.goto(base+'/projects/P1/execution-history');await page.getByRole('cell',{name:'EX1',exact:true}).waitFor();assert.equal(await page.getByRole('cell',{name:'EX2',exact:true}).count(),0);
 await page.getByRole('searchbox').fill('TC1');await page.getByRole('cell',{name:'EX1',exact:true}).waitFor();await capture(page,'history');
 setHistoryFails(true);await page.getByRole('button',{name:'Refresh history'}).click();await page.getByRole('alert').filter({hasText:'Execution history unavailable'}).waitFor();setHistoryFails(false);await page.getByRole('button',{name:'Try again'}).click();await page.getByRole('cell',{name:'EX1',exact:true}).waitFor();assert.equal(calls.filter(x=>x.method!=='GET'&&x.method!=='OPTIONS').length,0);
 await page.getByRole('button',{name:'Account and appearance'}).click();await page.getByRole('menuitemradio',{name:'Dark',exact:true}).click();await capture(page,'history-dark');await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));await capture(page,'history-mobile');
});
test('execution remains gated and enabled view does not start a browser on navigation',async t=>{
 const disabled=await fixture(t);await disabled.page.goto(base+'/projects/P1/test-execution');await disabled.page.getByText('This feature is disabled.',{exact:true}).waitFor();assert.equal(disabled.calls.filter(x=>x.path.includes('approved-visual-runs')).length,0);
 const{page,calls}=await fixture(t,{execution:true});await page.goto(base+'/projects/P1/test-execution');await page.getByRole('heading',{name:'Approved visual run'}).waitFor();await page.getByText('Development controls · controlled sample only',{exact:true}).waitFor();assert.equal(calls.filter(x=>x.method==='POST').length,0);await capture(page,'execution');await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));await capture(page,'execution-mobile');
});

test('story detail preserves acceptance criteria and coverage actions on mobile',async t=>{
 const{page}=await fixture(t);await page.goto(base+'/projects/P1/stories/ST1');await page.getByRole('heading',{name:'Save an order',exact:true}).waitFor();await page.getByRole('heading',{name:'Acceptance criteria',exact:true}).waitFor();await page.getByRole('button',{name:'Generate scenarios with AI'}).waitFor();await capture(page,'story-detail');await page.setViewportSize({width:390,height:844});await capture(page,'story-detail-mobile');assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),JSON.stringify(await page.evaluate(()=>[...document.querySelectorAll('main *')].filter(el=>el.getBoundingClientRect().right>innerWidth+1).slice(0,8).map(el=>({tag:el.tagName,class:el.className})))));
});
