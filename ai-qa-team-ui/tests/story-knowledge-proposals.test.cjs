const {test,before,after}=require('node:test');const assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH||'playwright');const {fixture,base}=require('./qa-agent-fixture.cjs');let browser;
before(async()=>{browser=await chromium.launch({headless:true,channel:'msedge'});});after(async()=>browser?.close());
for(const manual of [false,true])for(const update of [false,true])test(`${manual?'Manually':'AI'} approved story ${update?'Update selects rule':'Add needs no further details'} and opens QA Agent Review without AI`,async t=>{
 const f=await fixture(browser,t);const headers={'access-control-allow-origin':base,'access-control-allow-credentials':'true','access-control-allow-headers':'content-type','access-control-allow-methods':'GET,POST,OPTIONS'};const posts=[];const id='d'.repeat(32);
 const session={review_id:id,title:'Knowledge from story',mode:update?'correction':'training',source_id:'b'.repeat(32),base_version_id:null,draft_version_id:'c'.repeat(32),state:'reviewing',extraction_state:'completed',attempt:0,revision:0,proposals:[{claim:{claim_id:update?'K1':'K_NEW',category:'business_rule',statement:'Show Draft saved.',epistemic_status:'expected',source_id:'b'.repeat(32),segment_index:null,quote:'Show Draft saved.'},decision:'pending'}],clarification_questions:[],clarification_answers:{},removed_claim_ids:[]};
 await f.context.route(url=>url.origin==='http://feature-api.test'&&url.pathname.endsWith('/stories/ST1/analysis'),route=>route.fulfill({headers,json:manual?null:{analysis_id:'a'.repeat(32),status:'reviewed',stale:false,summary:'Reviewed',analysis_mode:'story_only',knowledge_version_id:null,findings:[],story_approval:{state:'approved',approved_by_name:'Alice'}}}));
 await f.context.route(url=>url.pathname.endsWith('/manual-approval'),route=>route.fulfill({headers,json:{approval:{state:'approved',basis:'manual_review',approved_by_name:'Alice'}}}));
 await f.context.route(url=>url.pathname.endsWith('/knowledge-proposals'),route=>{
  if(route.request().method()==='OPTIONS')return route.fulfill({headers,status:204});
  if(route.request().method()==='POST'){posts.push(route.request().postDataJSON());return route.fulfill({headers,json:session});}
  return route.fulfill({headers,json:{version_id:'e'.repeat(32),pending_review_id:null,rules:update?[{claim_id:'K1',statement:'Old approved behavior.'}]:[]}});
 });
 await f.context.route(url=>url.pathname==='/projects/P1/knowledge/training/'+id,route=>route.fulfill({headers,json:session}));
 await f.page.goto(base+'/projects/P1/stories/ST1');
 await f.page.getByRole('button',{name:update?'Update knowledge':'Add knowledge',exact:true}).waitFor();
 assert.equal(await f.page.getByRole('button',{name:update?'Add knowledge':'Update knowledge',exact:true}).count(),0);
 if(update){await f.page.getByRole('button',{name:'Update knowledge',exact:true}).click();await f.page.getByLabel('Approved knowledge',{exact:true}).selectOption('K1');await f.page.getByRole('button',{name:'Create update draft',exact:true}).click();}
 else await f.page.getByRole('button',{name:'Add knowledge',exact:true}).click();
 await f.page.getByRole('heading',{name:update?'Review correction':'Review knowledge',exact:true}).waitFor();
 await f.page.getByRole('region',{name:'Training review',exact:true}).getByText('Show Draft saved.',{exact:true}).first().waitFor();
 assert.equal(posts.length,1);assert.equal(posts[0].change_type,update?'update':'add');if(update)assert.equal(posts[0].claim_id,'K1');else assert.deepEqual(Object.keys(posts[0]),['change_type']);
 assert.equal(f.calls.filter(c=>c.path.endsWith('/extract')||c.path.endsWith('/analyze')).length,0);
});

test('pending story proposal offers resume only and does not create another draft',async t=>{
 const f=await fixture(browser,t);let posts=0;const headers={'access-control-allow-origin':base,'access-control-allow-credentials':'true'};
 await f.context.route(url=>url.origin==='http://feature-api.test'&&url.pathname.endsWith('/stories/ST1/analysis'),route=>route.fulfill({headers,json:{analysis_id:'a'.repeat(32),status:'reviewed',stale:false,summary:'Reviewed',analysis_mode:'story_only',findings:[],story_approval:{state:'approved',approved_by_name:'Alice'}}}));
 await f.context.route(url=>url.pathname.endsWith('/knowledge-proposals'),route=>{
  if(route.request().method()==='POST')posts++;
  return route.fulfill({headers,json:{version_id:null,rules:[],pending_review_id:'d'.repeat(32)}});
 });
 await f.page.goto(base+'/projects/P1/stories/ST1');
 await f.page.getByRole('button',{name:'Review knowledge',exact:true}).waitFor();
 assert.equal(await f.page.getByRole('button',{name:'Add knowledge',exact:true}).count(),0);
 assert.equal(await f.page.getByRole('button',{name:'Update knowledge',exact:true}).count(),0);
 assert.equal(posts,0);
});
