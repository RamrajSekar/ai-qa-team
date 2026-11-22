const {test,before,after}=require('node:test');const assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH||'playwright');
const {fixture,base}=require('./qa-agent-fixture.cjs');let browser;
before(async()=>{browser=await chromium.launch({headless:true,channel:'msedge'});});after(async()=>browser?.close());
async function setup(t,guest=false){
 const f=await fixture(browser,t);
 await f.context.route("http://feature-api.test/features",route=>route.fulfill({headers:{"access-control-allow-origin":base,"access-control-allow-credentials":"true"},json:{customer_accounts:true,account_subscriptions:true,story_management:true,scenario_generation:true,test_generation:true}}));
 await f.context.route('http://feature-api.test/auth/pricing',route=>route.fulfill({headers:{'access-control-allow-origin':base,'access-control-allow-credentials':'true'},json:{stage:'EXPERIMENTAL',free:{monthly_usd:0,managed_ai_credits_limit:25,byok_ai_requests_limit:25,additional_members_limit:2},managed:{monthly_usd:499,managed_ai_credits_limit:500},byok:{monthly_usd:349,byok_ai_requests_limit:500},pilot:{fixed_usd:1000}}}));
 if(guest){await f.context.clearCookies();await f.context.route('http://feature-api.test/auth/me**',route=>route.fulfill({headers:{'access-control-allow-origin':base,'access-control-allow-credentials':'true'},json:{user:null}}));}
 return f;
}
test('account plans retain workspace and return to account without auth links',async t=>{
 const {page}=await setup(t);await page.goto(base+'/settings/account/plans');
 await page.getByRole('heading',{name:'Managed AI',exact:true}).waitFor();
 await page.getByRole('link',{name:'Dashboard',exact:true}).waitFor();
 assert.equal(await page.locator('a[href^="/auth"]').count(),0);
 const back=page.getByRole('link',{name:'Back to account',exact:true});assert.equal(await back.getAttribute('href'),'/settings/account');
 await back.click();await page.waitForURL('**/settings/account');
});
test('signed-in public pricing shows workspace instead of sign in',async t=>{
 const {page}=await setup(t);await page.goto(base+'/pricing');
 const link=page.getByRole('link',{name:'Open workspace',exact:true});await link.waitFor();
 assert.equal(await page.getByRole('link',{name:/sign in/i}).count(),0);
 assert.equal(await page.locator('a[href^="/auth"]').count(),0);
 await link.click();await page.waitForURL('**/dashboard');
});
test('anonymous pricing retains sign in and signup navigation',async t=>{
 const {page}=await setup(t,true);await page.goto(base+'/pricing');
 await page.getByRole('heading',{name:'Managed AI',exact:true}).waitFor();
 assert.equal(await page.getByRole('link',{name:'Sign in',exact:true}).getAttribute('href'),'/auth?mode=login');
 assert.equal(await page.getByRole('link',{name:'Get started',exact:true}).getAttribute('href'),'/auth?mode=signup');
 assert.equal(await page.getByRole('link',{name:'Open workspace',exact:true}).count(),0);
});
