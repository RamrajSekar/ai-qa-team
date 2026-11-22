const {test,before,after}=require('node:test');const assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH||'playwright');
const {fixture,base}=require('./qa-agent-fixture.cjs');let browser;
before(async()=>{browser=await chromium.launch({headless:true,channel:'msedge'});});after(async()=>browser?.close());
test('Gemini and Claude use BYOK fields and explicit connection testing',async t=>{
 const {page,context}=await fixture(browser,t);const submitted=[];
 await context.route('http://feature-api.test/projects/P1/ai/**',async route=>{
  const request=route.request(),path=new URL(request.url()).pathname;
  const headers={'access-control-allow-origin':base,'access-control-allow-credentials':'true','access-control-allow-headers':'content-type','access-control-allow-methods':'GET,POST,PUT,OPTIONS'};
  if(request.method()==='OPTIONS')return route.fulfill({status:204,headers});
  let json=null;
  if(path.endsWith('/providers'))json=[{provider_id:'managed',label:'Managed',fields:[{name:'model',label:'Model'}]},...['gemini','anthropic'].map(provider_id=>({provider_id,label:provider_id==='gemini'?'Google Gemini':'Anthropic Claude',fields:[{name:'model',label:'Model'},{name:'api_key',label:'API Key',secret:true}]}))];
  else if(request.method()==='POST'){submitted.push(request.postDataJSON());json={success:true};}
  return route.fulfill({headers,json});
 });
 await page.goto(base+'/settings/ai');const provider=page.getByLabel('Provider',{exact:true});
 await provider.locator('option[value=gemini]').waitFor({state:'attached'});
 for(const name of ['gemini','anthropic']){
  await provider.selectOption(name);await page.getByLabel('Model',{exact:true}).selectOption('__other');await page.getByLabel('Custom model',{exact:true}).fill('customer-selected-model');
  const key=page.getByLabel('API Key',{exact:true});assert.equal(await key.getAttribute('type'),'password');await key.fill('synthetic-key');
  await page.getByRole('button',{name:'Test Connection',exact:true}).click();await page.getByText('Connection successful.',{exact:true}).waitFor();
  assert.equal(submitted.at(-1).provider_id,name);assert.equal(submitted.at(-1).mode,'BYOK');assert.equal(submitted.at(-1).model,'customer-selected-model');
 }
 assert.equal(submitted.length,2);
});

test('saved custom model survives loading and preset selection is explicit',async t=>{
 const {page,context,calls}=await fixture(browser,t);
 await context.route('http://feature-api.test/projects/P1/ai/**',async route=>{
  const path=new URL(route.request().url()).pathname;
  const json=path.endsWith('/providers')?[{provider_id:'gemini',label:'Google Gemini',fields:[{name:'model',label:'Model'},{name:'api_key',label:'API Key',secret:true}]}]:{provider_id:'gemini',mode:'BYOK',model:'saved-custom-model',configuration:{},status:'ACTIVE',credential_configured:true};
  return route.fulfill({headers:{'access-control-allow-origin':base,'access-control-allow-credentials':'true'},json});
 });
 await page.goto(base+'/settings/ai');await page.getByLabel('Custom model',{exact:true}).waitFor();
 assert.equal(await page.getByLabel('Custom model',{exact:true}).inputValue(),'saved-custom-model');
 await page.getByLabel('Model',{exact:true}).selectOption('gemini-3.8-flash');
 assert.equal(await page.getByLabel('Custom model',{exact:true}).count(),0);
 assert.equal(calls.filter(call=>call.method!=='GET').length,0);
});
