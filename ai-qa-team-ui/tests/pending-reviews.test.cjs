const {test,before,after}=require('node:test');const assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH||'playwright');const {fixture,base}=require('./qa-agent-fixture.cjs');let browser;
before(async()=>{browser=await chromium.launch({headless:true,channel:'msedge'});});after(async()=>browser?.close());

test('Overview lists reviewers and opens original scenario approval; refresh removes approved item',async t=>{
 const f=await fixture(browser,t);const headers={'access-control-allow-origin':base,'access-control-allow-credentials':'true','access-control-allow-headers':'content-type','access-control-allow-methods':'GET,PUT,OPTIONS'};
 let approved=false;const writes=[];
 const scenario={scenario_id:'SC1',story_id:'ST1',project_id:'P1',title:'Save draft coverage',approved:false,created_by:'fixture@example.com',steps:[{action:'Save draft',expected:'Draft saved'}]};
 const items=[{type:'Story',id:'ST1',title:'Save draft',status:'In review',href:'/projects/P1/stories/ST1#story-analysis',detail:'Review story',pending_with:['Alice']},{type:'Scenario',id:'SC1',title:'Save draft coverage',status:'In review',href:'/projects/P1/scenarios?review=SC1',detail:'',pending_with:['Alice']},{type:'Test Case',id:'TC1',title:'Save draft details',status:'In review',href:'/projects/P1/testcases?review=TC1',detail:'',pending_with:['Alice','Carol']},{type:'Knowledge',id:'R1',title:'Draft behavior',status:'Awaiting approval',href:'/projects/P1/knowledge?review=R1',detail:'Training review',pending_with:['Alice']}];
 await f.context.route(url=>url.pathname==='/projects/P1/pending-reviews',route=>route.fulfill({headers,json:{items:items.filter(i=>!approved||i.id!=='SC1'),has_more:false,unavailable_types:[]}}));
 await f.context.route(url=>url.pathname==='/scenarios/project-list',route=>route.fulfill({headers,json:[{...scenario,approved}]}));
 await f.context.route(url=>url.pathname==='/scenarios/SC1/approve',route=>{
  if(route.request().method()==='OPTIONS')return route.fulfill({headers,status:204});writes.push(route.request().method());approved=true;return route.fulfill({headers,json:{...scenario,approved:true}});
 });
 await f.page.goto(base+'/projects/P1');
 const table=f.page.getByRole('table',{name:'Pending reviews',exact:true});await table.waitFor();
 await table.getByRole('columnheader',{name:'Pending with',exact:true}).waitFor();
 const row=table.getByRole('row').filter({hasText:'Save draft coverage'});await row.getByText('Alice',{exact:true}).waitFor();
 assert.equal(writes.length,0);
 await row.getByRole('link',{name:'Review',exact:true}).click();
 await f.page.getByRole('button',{name:'Approve scenario',exact:true}).click();
 assert.deepEqual(writes,['PUT']);
 await f.page.goto(base+'/projects/P1');await f.page.getByRole('table',{name:'Pending reviews',exact:true}).waitFor();
 assert.equal(await f.page.getByRole('table',{name:'Pending reviews',exact:true}).getByText('Save draft coverage',{exact:true}).count(),0);
 assert.equal(f.calls.filter(c=>c.path.endsWith('/analyze')||c.path.endsWith('/generate')).length,0);
});

test('held queue does not delay Overview fields; failure is distinct from empty',async t=>{
 const f=await fixture(browser,t);let release;const held=new Promise(r=>release=r);t.after(()=>release());
 const headers={'access-control-allow-origin':base,'access-control-allow-credentials':'true'};
 await f.context.route(url=>url.pathname==='/projects/P1/pending-reviews',async route=>{await held;return route.fulfill({headers,status:503,json:{detail:'Unavailable'}});});
 await f.page.goto(base+'/projects/P1');await f.page.getByRole('heading',{name:'Synthetic project',exact:true}).waitFor();
 await f.page.getByText('Loading pending reviews…',{exact:true}).waitFor();await f.page.getByText('Save draft',{exact:true}).waitFor();
 release();await f.page.getByText('Pending reviews are unavailable.',{exact:true}).waitFor();
 assert.equal(await f.page.getByText('No pending reviews on this page.',{exact:true}).count(),0);
});


for(const foreign of [false,true])test(`case review deep link checks the project when item is outside the catalog page: foreign=${foreign}`,async t=>{
 const f=await fixture(browser,t);const headers={'access-control-allow-origin':base,'access-control-allow-credentials':'true'};
 await f.context.route(url=>url.pathname==='/testcases/project-list',route=>route.fulfill({headers,json:[]}));
 await f.context.route(url=>url.pathname==='/testcases/testcases/TC_OTHER',route=>route.fulfill({headers,json:{project_id:foreign?'P2':'P1',testcase_id:'TC_OTHER',scenario_id:'SC1',title:'Off-page case',status:'draft',steps:[]}}));
 await f.context.route(url=>url.pathname==='/projects/P1/test-design/cases/TC_OTHER',route=>route.fulfill({headers,json:{review_required:true,context_ready:false,context_error:'Review the source scenario.',current_context:null,approved_expected_rules:[],versions:[],active_version_id:null,approval_policy:{admin_only:false,can_approve:true}}}));
 await f.page.goto(base+'/projects/P1/testcases?review=TC_OTHER');
 if(foreign){await f.page.getByText('Review item is unavailable in this project.',{exact:true}).waitFor();assert.equal(await f.page.getByRole('dialog').count(),0);}
 else await f.page.getByRole('dialog',{name:'Review test case: Off-page case',exact:true}).waitFor();
 assert.equal(f.calls.filter(c=>c.method==='POST'||c.method==='PUT').length,0);
});


test('partial queue failure is not presented as no pending reviews',async t=>{
 const f=await fixture(browser,t);const headers={'access-control-allow-origin':base,'access-control-allow-credentials':'true'};
 await f.context.route(url=>url.pathname==='/projects/P1/pending-reviews',route=>route.fulfill({headers,json:{items:[],has_more:false,unavailable_types:['Knowledge training']}}));
 await f.page.goto(base+'/projects/P1');
 await f.page.getByText('Review results are incomplete. Refresh to try again.',{exact:true}).waitFor();
 assert.equal(await f.page.getByText('No pending reviews on this page.',{exact:true}).count(),0);
});
