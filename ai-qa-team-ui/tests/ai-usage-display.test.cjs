const {test,before,after}=require('node:test');const assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH||'playwright');
const {fixture,base}=require('./qa-agent-fixture.cjs');let browser;
before(async()=>{browser=await chromium.launch({headless:true,channel:'msedge'});});after(async()=>browser?.close());
async function setup(t,unavailable=false){
 const f=await fixture(browser,t);const calls=[];
 const subscription={plan:'free',status:'active',ai_allowance_version:1,usage:{managed_ai_credits_used:3,byok_ai_requests_used:1},limits:{managed_ai_credits_limit:25,byok_ai_requests_limit:25}};
 await f.context.route('http://feature-api.test/**',async route=>{
  const request=route.request(),path=new URL(request.url()).pathname;
  const headers={'access-control-allow-origin':base,'access-control-allow-credentials':'true'};
  if(request.method()==='OPTIONS')return route.fallback();calls.push({path,method:request.method()});
  let json;
  if(path==='/features')json={customer_accounts:true,account_subscriptions:true,product_knowledge:true,story_management:true,scenario_generation:true,test_generation:true};
  else if(path==='/account')json={name:'Synthetic account',current_user_role:'MEMBER'};
  else if(path==='/account/members')json=[];
  else if(path==='/account/subscription')json={billing_scope:'ACCOUNT',subscription};
  else if(path==='/projects')json=[{project_id:'P1',name:'Managed project',current_user_role:'TESTER'},{project_id:'P2',name:'BYOK project',current_user_role:'TESTER'}];
  else if(path.endsWith('/ai/configuration')){
   if(unavailable)return route.fulfill({status:503,headers,json:{detail:'Unavailable'}});
   json=path.includes('/P1/')?null:{mode:'BYOK',provider_id:'openai'};
  }else return route.fallback();
  return route.fulfill({headers,json});
 });
 return {...f,calls,subscription};
}
test('saved project mode highlights its pool and switching display preserves both balances',async t=>{
 const {page,calls,subscription}=await setup(t);await page.goto(base+'/settings/account');
 const managed=page.getByRole('region',{name:'Managed AI Requests',exact:true});
 await managed.waitFor();assert.match(await managed.innerText(),/3 \/ 25/);
 assert.equal(await page.getByRole('region',{name:'BYOK AI Requests',exact:true}).count(),0);
 await page.getByText('Other AI usage',{exact:true}).click();
 assert.match(await page.getByRole('region',{name:'BYOK AI Requests',exact:true}).innerText(),/1 \/ 25/);
 await page.getByLabel('AI mode for project',{exact:true}).selectOption('P2');
 await page.getByText('BYOK selected for BYOK project.',{exact:false}).waitFor();
 assert.equal(await page.getByRole('region',{name:'Managed AI Requests',exact:true}).count(),0);
 await page.getByText('Other AI usage',{exact:true}).click();
 assert.match(await page.getByRole('region',{name:'Managed AI Requests',exact:true}).innerText(),/3 \/ 25/);
 assert.deepEqual(subscription.usage,{managed_ai_credits_used:3,byok_ai_requests_used:1});
 assert.equal(calls.filter(call=>!['GET','OPTIONS'].includes(call.method)).length,0);
 await page.reload();await page.getByRole('region',{name:'Managed AI Requests',exact:true}).waitFor();
 assert.match(await page.getByRole('region',{name:'Managed AI Requests',exact:true}).innerText(),/3 \/ 25/);
});
test('unavailable saved mode keeps both balances visible instead of guessing',async t=>{
 const {page}=await setup(t,true);await page.goto(base+'/settings/account');
 await page.getByText('Saved AI mode unavailable. Both balances are shown.',{exact:true}).waitFor();
 await page.getByRole('region',{name:'Managed AI Requests',exact:true}).waitFor();await page.getByRole('region',{name:'BYOK AI Requests',exact:true}).waitFor();
});
test('legal pages and footer links remain unpublished',async t=>{
 const {page}=await fixture(browser,t);await page.goto(base+'/');
 assert.equal(await page.getByRole('link',{name:'Privacy',exact:true}).count(),0);
 for(const path of ['/privacy','/terms','/support']){
  const response=await page.goto(base+path);assert.equal(response.status(),404);
  assert.equal(await page.getByText('support@aiqa.com',{exact:true}).count(),0);
 }
});
