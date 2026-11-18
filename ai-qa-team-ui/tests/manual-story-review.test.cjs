const {test,before,after}=require('node:test');const assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH||'playwright');const {fixture,base}=require('./qa-agent-fixture.cjs');let browser;
before(async()=>{browser=await chromium.launch({headless:true,channel:'msedge'});});after(async()=>browser?.close());
for(const role of ['ADMIN','TESTER'])test(`manual story approval is explicit and project-role protected for ${role}`,async t=>{
 const f=await fixture(browser,t,{role});let approval=null;const posts=[];
 const headers={'access-control-allow-origin':base,'access-control-allow-credentials':'true','access-control-allow-headers':'content-type','access-control-allow-methods':'GET,POST,OPTIONS'};
 await f.context.route(url=>url.origin==='http://feature-api.test'&&url.pathname.endsWith('/stories/ST1/analysis'),route=>route.fulfill({headers,json:null}));
 await f.context.route(url=>url.pathname.endsWith('/manual-approval'),route=>{
  if(route.request().method()==='OPTIONS')return route.fulfill({headers,status:204});
  if(route.request().method()==='POST'){posts.push(route.request().postDataJSON());approval={state:'approved',basis:'manual_review',approved_by_name:'Alice'};return route.fulfill({headers,json:approval});}
  return route.fulfill({headers,json:{story:{title:'Save draft',description:'Users save a draft.',acceptance_criteria:'Draft is saved.',out_of_scope:null},snapshot_digest:'a'.repeat(64),blocked:false,approval}});
 });
 await f.page.goto(base+'/projects/P1/stories/ST1');
 await f.page.getByRole('heading',{name:'Review story clarity'}).waitFor();
 if(role==='TESTER'){assert.equal(await f.page.getByRole('button',{name:'Approve manually',exact:true}).count(),0);return;}
 await f.page.getByRole('button',{name:'Approve manually',exact:true}).click();
 const confirm=f.page.getByRole('button',{name:'Confirm approval',exact:true});assert.equal(await confirm.isDisabled(),true);
 await f.page.getByLabel('Review note (optional)',{exact:true}).fill('Reviewed scope and expected behavior.');
 await f.page.getByRole('checkbox',{name:'I reviewed this story and it is clear enough for test design.'}).check();
 await confirm.click();await f.page.getByRole('dialog').waitFor({state:'hidden'});
 await f.page.getByText('Approved · Manual review',{exact:true}).waitFor();
 await f.page.getByText('Not analyzed. Approved through manual review.',{exact:true}).waitFor();
 assert.equal(posts.length,1);assert.equal(posts[0].confirmed,true);assert.equal(posts[0].snapshot_digest,'a'.repeat(64));
 assert.equal(f.calls.filter(c=>c.path.endsWith('/analyze')).length,0);
 await f.page.reload();await f.page.getByText('Approved · Manual review',{exact:true}).waitFor();assert.equal(posts.length,1);
});
