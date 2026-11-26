// Browser UX with synthetic API/auth; never real billing or AI calls.
const {test,before,after}=require('node:test');
const assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH||'playwright');
const base=process.env.FEATURE_UI_URL||'http://127.0.0.1:3128';let browser;
before(async()=>{browser=await chromium.launch({headless:true,channel:'msedge'});});
after(async()=>browser?.close());
async function fixture(t,{role='OWNER',pending=false,unauthorizedCheckout=false,unsafeRedirect=false}={}){
 const context=await browser.newContext();t.after(()=>context.close());
 await context.addCookies([{name:'access_token',value:'synthetic-billing-fixture',url:base}]);
 const user={_id:'fixture',email:'fixture@example.com',name:'Fixture',account_id:'ACC_fixture',account_role:role,onboarding:{onboarding_status:'completed'}};
 const calls=[],dismissed=new Set();let threshold=80;
 const subscription={plan:'free',status:'active',entitlement_version:2,ai_allowance_version:1,usage:{managed_ai_credits_used:40,byok_ai_requests_used:0,projects_used:1,stories_used:2,scenarios_used:3,testcases_used:1,team_members_used:0},limits:{managed_ai_credits_limit:50,byok_ai_requests_limit:50,projects_limit:1,stories_limit:5,scenarios_limit:10,testcases_limit:10,team_members_limit:2,testcases_basic_limit:null,testcases_medium_limit:null,testcases_advanced_limit:null}};
 const status={checkout_available:true,portal_available:false,test_mode:true,state:'unconfigured',hosted_domains:{checkout:'checkout.stripe.com',portal:'billing.stripe.com'},pending:pending?{request_id:'a'.repeat(32),plan:'team',state:'UNKNOWN'}:null};
 await context.route('http://feature-api.test/**',async route=>{
  const req=route.request(),path=new URL(req.url()).pathname,method=req.method();
  const headers={'access-control-allow-origin':base,'access-control-allow-credentials':'true','access-control-allow-headers':'content-type','access-control-allow-methods':'GET,POST,OPTIONS'};
  if(method==='OPTIONS')return route.fulfill({status:204,headers});
  const body=req.postData()?req.postDataJSON():null;calls.push({path,method,body});let json=[];
  if(path==='/auth/me')json={user};
  if(path==='/features')json={customer_accounts:true,account_subscriptions:true,separate_ai_allowances:true};
  if(path==='/auth/pricing')json=require('./pricing-catalog-fixture.cjs')();
  if(path==='/account')json={account_id:'ACC_fixture',name:'Fixture',current_user_role:role,setup_status:'COMPLETE'};
  if(path==='/account/subscription')json={billing_scope:'ACCOUNT',subscription:{...subscription,usage:{...subscription.usage,managed_ai_credits_used:threshold===80?40:50,scenarios_basic_used:1,scenarios_medium_used:2,scenarios_advanced_used:0,testcases_basic_used:1,testcases_medium_used:0,testcases_advanced_used:0}},experience:{period:{start:'2026-11-01T00:00:00Z',end:'2026-12-01T00:00:00Z',timezone:'UTC',projected:false},seats:{included:3,extra:0,purchasable:false},notices:dismissed.has('notice'+threshold)?[]:[{id:'notice'+threshold,metric:'managed_ai_credits',threshold,message:threshold===80?'Managed AI: at least 80% used.':'Managed AI limit reached. Manual work stays available.',used:threshold===80?40:50,limit:50}]}};
  if(path.startsWith('/account/usage/notices/')){dismissed.add(path.split('/')[4]);json={dismissed:true};}
  if(path==='/account/billing')json=status;
  if(path==='/account/billing/checkout')return route.fulfill({headers,status:unsafeRedirect?200:unauthorizedCheckout?401:502,json:unsafeRedirect?{url:'https://untrusted.example/checkout'}:{detail:'Synthetic uncertain checkout. Resume the saved request.'}});
  await route.fulfill({headers,json});
 });
 const page=await context.newPage();page.setDefaultTimeout(30000);page.setDefaultNavigationTimeout(90000);
 const errors=[];page.on('pageerror',error=>errors.push(error.message));t.after(()=>assert.deepEqual(errors,[]));
 return {page,calls,setThreshold:value=>{threshold=value;}};
}
test('usage notices persist on refresh and higher threshold remains visible',async t=>{
 const {page,calls,setThreshold}=await fixture(t);await page.goto(base+'/settings/account');
 await page.getByRole('button',{name:'Dismiss managed_ai_credits 80% notice'}).waitFor();
 await page.getByText(/Resets Dec 1, 2026 \(UTC\)/).waitFor();
 assert.equal(calls.filter(c=>c.method==='POST').length,0);
 await page.getByRole('button',{name:'Dismiss managed_ai_credits 80% notice'}).click();
 await page.reload();await page.getByRole('heading',{name:'Subscription & usage'}).waitFor();
 assert.equal(await page.getByRole('button',{name:/Dismiss managed_ai_credits/}).count(),0);
 setThreshold(100);await page.reload();await page.getByRole('button',{name:'Dismiss managed_ai_credits 100% notice'}).waitFor();
 await page.setViewportSize({width:390,height:844});
 assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
 if(process.env.PRICING_USAGE_SCREENSHOT)await page.screenshot({path:process.env.PRICING_USAGE_SCREENSHOT,fullPage:true});
});
test('checkout is explicit and an uncertain retry keeps the same request identity',async t=>{
 const {page,calls}=await fixture(t);await page.goto(base+'/settings/account/plans?checkout=returned');
 const choose=page.getByRole('button',{name:'Test Team checkout',exact:true});await choose.waitFor();
 assert.equal(calls.filter(c=>c.method==='POST').length,0);
 await choose.click();await page.getByRole('alert').filter({hasText:/Synthetic uncertain/}).waitFor();
 await choose.click();await page.getByRole('alert').filter({hasText:/Synthetic uncertain/}).waitFor();
 const attempts=calls.filter(c=>c.path==='/account/billing/checkout');assert.equal(attempts.length,2);
 assert.match(attempts[0].body.request_id,/^[a-f0-9]{32}$/);assert.deepEqual(attempts[0].body,attempts[1].body);
 assert.equal(calls.filter(c=>c.method==='POST'&&c.path!=='/account/billing/checkout').length,0);
});
test('saved pending checkout resumes its original identity',async t=>{
 const {page,calls}=await fixture(t,{pending:true});await page.goto(base+'/settings/account/plans');
 await page.getByRole('button',{name:'Resume saved checkout'}).click();
 await page.getByRole('alert').filter({hasText:/Synthetic uncertain/}).waitFor();
 assert.equal(calls.find(c=>c.path==='/account/billing/checkout').body.request_id,'a'.repeat(32));
 assert.equal(await page.getByRole('button',{name:'Test Team checkout'}).count(),0);
});
test('ordinary account members have no purchasing controls',async t=>{
 const {page,calls}=await fixture(t,{role:'MEMBER'});await page.goto(base+'/settings/account/plans');
 await page.getByRole('heading',{name:'Team',exact:true}).waitFor();
  await page.waitForFunction(()=>document.querySelector('h2')!==null);
 assert.equal(await page.getByRole('button',{name:/checkout|Manage billing/}).count(),0);
 assert.equal(calls.filter(c=>c.method==='POST').length,0);
});
test('checkout authentication failure is not automatically replayed',async t=>{
 const {page,calls}=await fixture(t,{unauthorizedCheckout:true});await page.goto(base+'/settings/account/plans');
 await page.getByRole('button',{name:'Test Team checkout',exact:true}).click();
 await page.getByRole('alert').filter({hasText:/Synthetic uncertain/}).waitFor();
 assert.equal(calls.filter(c=>c.path==='/account/billing/checkout').length,1);
 assert.equal(calls.filter(c=>c.path==='/auth/refresh').length,0);
});
test('an unexpected hosted-page domain never receives the user',async t=>{
 const {page}=await fixture(t,{unsafeRedirect:true});await page.goto(base+'/settings/account/plans');
 await page.getByRole('button',{name:'Test Team checkout',exact:true}).click();
 await page.getByRole('alert').filter({hasText:'Billing returned an invalid page.'}).waitFor();
 assert.equal(new URL(page.url()).origin,base);
});
