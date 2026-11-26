// Public pricing UI, intercepted catalog only; no checkout/model/provider requests.
const {test,before,after}=require('node:test');
const assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH||'playwright');
const base=process.env.FEATURE_UI_URL||'http://127.0.0.1:3123'; let browser;
before(async()=>{browser=await chromium.launch({headless:true,channel:'msedge'});});
after(async()=>browser?.close());
async function fixture(t,fail=false,override){
 const context=await browser.newContext();t.after(()=>context.close());let failed=fail;const calls=[];
 const catalog=require('./pricing-catalog-fixture.cjs')();if(override)override(catalog);
 await context.route('http://feature-api.test/**',async route=>{calls.push(route.request().method());const headers={'access-control-allow-origin':base,'access-control-allow-credentials':'true'};if(failed){failed=false;return route.fulfill({status:503,json:{detail:'Synthetic unavailable'},headers});}return route.fulfill({json:catalog,headers});});
 const page=await context.newPage();page.setDefaultTimeout(30000);page.setDefaultNavigationTimeout(90000);return{page,calls};
}
test('anonymous pricing compares four account plans without checkout',async t=>{
 const{page,calls}=await fixture(t);await page.goto(base+'/pricing');
 for(const name of ['Free','Team','Business','Enterprise'])await page.getByRole('heading',{name,exact:true}).waitFor();
 assert.match(await page.getByRole('article',{name:'Team plan'}).innerText(),/\$49/);
 assert.match(await page.getByRole('article',{name:'Business plan'}).innerText(),/\$149/);
 assert.equal(await page.getByRole('button',{name:'Team coming soon'}).isDisabled(),true);
 await page.getByText(/Paid plans and add-ons are planned/).waitFor();
 await page.getByText(/Requests are not tokens/).waitFor();
 const comparison=page.getByRole('table');assert.match(await comparison.innerText(),/Users, including owner/);
 assert.match(await comparison.getByRole('row',{name:/Test cases/}).innerText(),/10\s+3,000\s+15,000/);
 assert.equal(calls.filter(method=>method!=='GET'&&method!=='OPTIONS').length,0);
 if(process.env.PRICING_SCREENSHOT)await page.screenshot({path:process.env.PRICING_SCREENSHOT,fullPage:true});
 await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
 if(process.env.PRICING_MOBILE_SCREENSHOT)await page.screenshot({path:process.env.PRICING_MOBILE_SCREENSHOT,fullPage:true});
});
test('pricing catalog failure offers a bounded user-initiated retry',async t=>{
 const{page}=await fixture(t,true);await page.goto(base+'/pricing');await page.getByRole('alert').filter({hasText:'Pricing details are temporarily unavailable.'}).waitFor();
 await page.getByRole('button',{name:'Try again'}).click();await page.getByRole('heading',{name:'Team',exact:true}).waitFor();
});

test('landing page explains Test Design in three steps without future execution claims',async t=>{
 const{page}=await fixture(t);await page.goto(base+'/');
 await page.getByRole('heading',{name:'Clearer stories. Better test cases.'}).waitFor();
 assert.equal(await page.getByRole('article').count(),3);
 await page.getByRole('link',{name:'View pricing',exact:true}).waitFor();
 await page.getByText('Test Design beta. Recording uploads and general automated browser execution are not included.',{exact:true}).waitFor();
 if(process.env.MARKETING_SCREENSHOT)await page.screenshot({path:process.env.MARKETING_SCREENSHOT,fullPage:true});
 await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
});

test('configured offers and contact links render without purchase actions',async t=>{
 const{page,calls}=await fixture(t,false,c=>{c.offers.team.monthly_usd=59;c.contact_url='https://example.com/contact';});
 await page.goto(base+'/pricing');const team=page.getByRole('article',{name:'Team plan'});
 await team.getByRole('heading',{name:'Team',exact:true}).waitFor();assert.match(await team.innerText(),/\$59/);
 assert.equal(await page.getByRole('link',{name:'Contact us about Team'}).getAttribute('href'),'https://example.com/contact');
 assert.equal(calls.filter(m=>m!=='GET'&&m!=='OPTIONS').length,0);
});
test('unsafe catalogue contact fails closed',async t=>{
 const{page}=await fixture(t,false,c=>{c.contact_url='javascript:alert(1)';});await page.goto(base+'/pricing');
 await page.getByRole('alert').waitFor();assert.equal(await page.getByRole('link',{name:/Contact us about/}).count(),0);
});
