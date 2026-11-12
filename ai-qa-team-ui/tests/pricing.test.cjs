// Public pricing UI, intercepted catalog only; no checkout/model/provider requests.
const {test,before,after}=require('node:test');
const assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH||'playwright');
const base=process.env.FEATURE_UI_URL||'http://127.0.0.1:3123'; let browser;
before(async()=>{browser=await chromium.launch({headless:true,channel:'msedge'});});
after(async()=>browser?.close());
async function fixture(t,fail=false){
 const context=await browser.newContext();t.after(()=>context.close());let failed=fail;const calls=[];
 const catalog={stage:'EXPERIMENTAL',currency:'USD',billing_enabled:false,free:{monthly_usd:0,managed_ai_credits_limit:25,byok_ai_requests_limit:25,additional_members_limit:2},managed:{monthly_usd:499,managed_ai_credits_limit:500,byok_ai_requests_limit:500},byok:{monthly_usd:349,managed_ai_credits_limit:500,byok_ai_requests_limit:500},enterprise:{monthly_usd:null,managed_ai_credits_limit:5000,byok_ai_requests_limit:5000},pilot:{fixed_usd:1000}};
 await context.route('http://feature-api.test/**',async route=>{calls.push(route.request().method());const headers={'access-control-allow-origin':base,'access-control-allow-credentials':'true'};if(failed){failed=false;return route.fulfill({status:503,json:{detail:'Synthetic unavailable'},headers});}return route.fulfill({json:catalog,headers});});
 const page=await context.newPage();page.setDefaultTimeout(30000);page.setDefaultNavigationTimeout(90000);return{page,calls};
}
test('anonymous pricing distinguishes Managed and BYOK with provisional prices and no checkout',async t=>{
 const{page,calls}=await fixture(t);await page.goto(base+'/pricing');
 await page.getByRole('heading',{name:'Managed AI',exact:true}).waitFor();
 await page.getByRole('heading',{name:'Bring Your Own Key',exact:true}).waitFor();
 await page.getByText('~$499',{exact:false}).waitFor();await page.getByText('~$349',{exact:false}).waitFor();
 await page.getByText(/Prices and allowances are experimental hypotheses/).waitFor();
 await page.getByText(/Credits count supported requests, not model tokens/).waitFor();
 await page.getByRole('definition').filter({hasText:/Managed AI requires no customer key/}).waitFor();
 assert.equal(calls.filter(method=>method!=='GET'&&method!=='OPTIONS').length,0);
 if(process.env.PRICING_SCREENSHOT)await page.screenshot({path:process.env.PRICING_SCREENSHOT,fullPage:true});
 await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
});
test('pricing catalog failure offers a bounded user-initiated retry',async t=>{
 const{page}=await fixture(t,true);await page.goto(base+'/pricing');await page.getByRole('alert').waitFor();
 await page.getByRole('button',{name:'Try again'}).click();await page.getByRole('heading',{name:'Managed AI',exact:true}).waitFor();
});
