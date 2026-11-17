const {test,before,after}=require('node:test');const assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH||'playwright');const {fixture,base}=require('./qa-agent-fixture.cjs');let browser;
before(async()=>{browser=await chromium.launch({headless:true,channel:'msedge'});});after(async()=>browser?.close());
const headers={'access-control-allow-origin':base,'access-control-allow-credentials':'true','access-control-allow-headers':'content-type','access-control-allow-methods':'GET,POST,OPTIONS'};
test('Account displays loading then account details before a held subscription, without an unnecessary member request',async t=>{
 const f=await fixture(browser,t);let releaseAccount,releaseBilling;
 const account=new Promise(resolve=>releaseAccount=resolve),billing=new Promise(resolve=>releaseBilling=resolve);
 t.after(()=>{releaseAccount();releaseBilling();});
 await f.context.route(url=>url.pathname==='/features',route=>route.fulfill({headers,json:{customer_accounts:true}}));
 await f.context.route(url=>url.pathname==='/account',async route=>{await account;return route.fulfill({headers,json:{name:'Acme',current_user_role:'OWNER',setup_status:'completed'}});});
 await f.context.route(url=>url.pathname==='/account/subscription',async route=>{await billing;return route.fulfill({headers,json:{billing_scope:'ACCOUNT',subscription:null}});});
 await f.page.goto(base+'/settings/account');await f.page.getByText('Loading account…',{exact:true}).waitFor();
 assert.equal(await f.page.getByRole('button',{name:'Reload account',exact:true}).count(),0);
 releaseAccount();await f.page.getByText('Customer details',{exact:true}).waitFor();await f.page.getByText('Loading subscription…',{exact:true}).waitFor();
 assert.equal(f.calls.filter(c=>c.path==='/account/members').length,0);releaseBilling();
});
test('Overview renders project while summary responses are held',async t=>{
 const f=await fixture(browser,t);let release;
 const held=new Promise(resolve=>release=resolve);t.after(()=>release());
 await f.context.route(url=>['/environments','/testcases/testcases'].includes(url.pathname),async route=>{await held;return route.fulfill({headers,json:[]});});
 await f.page.goto(base+'/projects/P1');await f.page.getByRole('heading',{name:'Synthetic project',exact:true}).waitFor();
 await f.page.getByText('Loading environments…',{exact:true}).waitFor();
 await f.page.getByRole('link',{name:'QA Agent',exact:true}).click();await f.page.getByRole('heading',{name:'Your QA Agent',exact:true}).waitFor();
 release();assert.equal(f.calls.filter(c=>c.path==='/projects').length,1);
});
