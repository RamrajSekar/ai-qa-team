const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');
function client(fetch) {
 const code = ts.transpileModule(fs.readFileSync('src/utils/api.ts', 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
 const context = { exports: {}, process: { env: { NEXT_PUBLIC_API_URL: 'https://api.example.test' } }, fetch, Headers, AbortSignal, DOMException, setTimeout, clearTimeout, console: { log() {} } };
 vm.runInNewContext(code, context);
 return context.exports.apiFetch;
}
const json = (data, status=200) => new Response(JSON.stringify(data), { status, headers: {'content-type':'application/json'} });
test('navigation reads avoid an unnecessary JSON preflight header', async () => {
 const api = client(async (_, options) => { assert.equal(new Headers(options.headers).has('content-type'), false); return json([]); });
 assert.equal((await api('/stories')).ok, true);
});
test('JSON writes retain content type and caller Headers survive', async () => {
 const api = client(async (_, options) => { const headers = new Headers(options.headers); assert.equal(headers.get('content-type'), 'application/json'); assert.equal(headers.get('x-fixture'), 'yes'); return json({data: {saved:true}}); });
 assert.equal((await api('/stories', {method:'POST',body:'{}',headers:new Headers({'x-fixture':'yes'})})).data.saved,true);
});
test('expired-session navigation reads share one refresh and retry once', async () => {
 let refreshed=false, refreshes=0; const attempts={};
 const api=client(async url => {
  if(url.endsWith('/auth/refresh')) { refreshes++; await new Promise(resolve=>setTimeout(resolve,15)); refreshed=true; return json({}); }
  attempts[url]=(attempts[url]||0)+1; return json([],refreshed?200:401);
 });
 const results=await Promise.all(['/stories','/scenarios','/testcases','/environments'].map(path=>api(path)));
 assert.equal(refreshes,1); assert.ok(results.every(result=>result.ok)); assert.ok(Object.values(attempts).every(value=>value===2));
});
test('rejected sign-in does not trigger another authentication round trip', async () => {
 let calls=0; const api=client(async ()=>{calls++;return json({detail:'Invalid credentials'},401);});
 assert.equal((await api('/auth/login',{method:'POST',body:'{}'})).status,401); assert.equal(calls,1);
});
test('aborted navigation is not replayed after refresh', async () => {
 let calls=0; const controller=new AbortController();
 const api=client(async url=>{calls++; if(url.endsWith('/auth/refresh')){controller.abort();return json({});} return json({},401);});
 await assert.rejects(api('/stories',{signal:controller.signal}),{name:'AbortError'}); assert.equal(calls,2);
});
test('failed refresh leaves original response and permits a later fresh attempt', async () => {
 let refreshes=0;const api=client(async url=>{if(url.endsWith('/auth/refresh')){refreshes++;return json({},401);}return json({detail:'Expired'},401);});
 assert.equal((await api('/stories')).status,401);assert.equal((await api('/stories')).status,401);assert.equal(refreshes,2);
});
test('a retried 401 cannot create an authentication loop',async()=>{
 let calls=0;const api=client(async url=>{calls++;return json({},url.endsWith('/auth/refresh')?200:401);});
 assert.equal((await api('/stories')).status,401);assert.equal(calls,3);
});
test('multipart bodies keep browser-controlled content type',async()=>{
 const body=new FormData();body.append('text','synthetic');
 const api=client(async(_,options)=>{assert.equal(new Headers(options.headers).has('content-type'),false);return json({});});
 assert.equal((await api('/knowledge',{method:'POST',body})).ok,true);
});
