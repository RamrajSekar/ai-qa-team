// Explicit task-owned development stack only. No routing interception or forged sessions.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE_PATH);
const base = process.env.M1A_REAL_URL;
const work = process.env.M1A_REAL_WORK;
if (base !== 'http://127.0.0.1:3317' || !work) throw new Error('Task-owned stack required');
const rows = [];
let stage = 'launch';
let browser;
function persist() { fs.writeFileSync(path.join(work, 'report.json'), JSON.stringify({ environment: 'real UI/login/API/TLS Mongo; synthetic accounts; existing local auth-cache fallback', checks: rows }, null, 2)); }
function assert(value, label) { if (!value) throw new Error(label); }
async function check(name, action) {
  stage = name;
  const started = Date.now();
  try {
  const evidence = await action();
  rows.push({ check: name, result: 'PASS', seconds: (Date.now()-started)/1000, ...evidence }); persist();
  } catch(error) {
    rows.push({check:name,result:'FAIL',error_type:error.name,seconds:(Date.now()-started)/1000});persist();process.exitCode=1;
    if(name==='normal_signup_real_UI_login_project_access')throw error;
  }
}
async function command(action) {
  const id = crypto.randomUUID();
  fs.writeFileSync(path.join(work,'command.json'), JSON.stringify({ action, id }));
  const deadline = Date.now()+90000;
  while (Date.now()<deadline) {
    try { if (JSON.parse(fs.readFileSync(path.join(work,'ack.json'),'utf8')).id === id) return; } catch {}
    await new Promise(r=>setTimeout(r,250));
  }
  throw new Error('Fixture control timeout');
}
async function account(label) {
  const context = await browser.newContext();
  const email = `m1a-${label}-${Date.now()}@example.com`;
  const password = crypto.randomBytes(20).toString('hex');
  const signup = await context.request.post(base+'/api/auth/signup', { data: { name: 'M1A '+label, email, password } });
  assert(signup.status() === 200, 'Normal development signup unavailable');
  await context.clearCookies(); // Require normal UI login, not the signup-issued session.
  const page = await context.newPage();
  page.setDefaultTimeout(30000); page.setDefaultNavigationTimeout(90000);
  await page.goto(base+'/auth?mode=login');
  await page.locator('#login-email').fill(email);
  await page.locator('#login-password').fill(password);
  const responsePromise = page.waitForResponse(r=>r.url().endsWith('/api/auth/login') && r.request().method()==='POST');
  await page.getByRole('button',{name:'Sign in',exact:true}).click();
  assert((await responsePromise).status()===200, 'UI login rejected');
  await page.waitForURL('**/dashboard');
  assert((await context.request.get(base+'/api/auth/me')).status()===200,'Authenticated profile unavailable');
  return { context, page, email };
}
async function main() {
  browser = await chromium.launch({headless:true,channel:'msedge'});
  let owner, outsider, project, runsBase, headlessId, currentId;
  async function request(suffix, method='GET', data) {
    return owner.context.request.fetch(base+'/api'+runsBase+suffix,{method,...(data===undefined?{}:{data})});
  }
  async function waitRun(id, predicate) {
    const deadline = Date.now()+70000;
    while(Date.now()<deadline) {
      const response = await request('/'+id);
      assert(response.status()===200,'Run status unavailable');
      const run = await response.json();
      if(predicate(run)) return run;
      if(['failed','cancelled','interrupted','timed_out'].includes(run.state)) {
        rows.push({check:'runner_failure_evidence',result:'FAIL',run_id:id,state:run.state,stage:run.startup_stage,code:run.diagnostic_code,reason:run.startup_reason});persist();
        throw new Error('Run stopped before requested observation');
      }
      await new Promise(r=>setTimeout(r,250));
    }
    throw new Error('Run lifecycle timeout');
  }
  async function startUI(headed=false) {
    const checkbox = owner.page.getByRole('checkbox');
    await checkbox.setChecked(headed);
    const pending=owner.page.waitForResponse(r=>r.url().endsWith(runsBase) && r.request().method()==='POST');
    await owner.page.getByRole('button',{name:'Start browser smoke check',exact:true}).click();
    const response=await pending;
    assert(response.status()===202,'UI start rejected');
    return (await response.json()).run_id;
  }
  await check('normal_signup_real_UI_login_project_access',async()=>{
    owner=await account('owner');
    const response=await owner.context.request.post(base+'/api/projects',{data:{name:'M1A dedicated development fixture',created_by:owner.email}});
    assert(response.status()===200,'Project creation rejected'); project=(await response.json()).project_id;
    runsBase=`/projects/${project}/visual-lab/runs`;
    await owner.page.goto(base+`/projects/${project}/visual-lab`);
    await owner.page.getByRole('heading',{name:'Visual Runner Lab',exact:true}).waitFor();
    return {project_id:project};
  });
  await check('headless_UI_completion_three_private_screenshots',async()=>{
    headlessId=await startUI();
    const run=await waitRun(headlessId,r=>r.state==='completed'); assert(run.screenshots.length===3,'Missing screenshot');
    for(const artifact of run.screenshots) {
      const response=await request(`/${headlessId}/artifacts/${artifact}`);
      assert(response.status()===200 && (await response.body()).subarray(0,4).equals(Buffer.from([137,80,78,71])),'PNG unavailable');
      assert(response.headers()['cache-control']==='no-store','Private cache policy absent');
    }
    await owner.page.getByRole('heading',{name:'Browser smoke check completed',exact:true}).waitFor();
    await owner.page.waitForFunction(()=>document.querySelectorAll('img[alt^="Controlled sample:"]').length===3 && [...document.querySelectorAll('img[alt^="Controlled sample:"]')].every(i=>i.naturalWidth>0));
    await owner.page.screenshot({path:path.join(work,'real-lab.png'),fullPage:true});
    return {run_id:headlessId,screenshots:3};
  });
  await check('separate_headed_UI_completion',async()=>{
    currentId=await startUI(true); const run=await waitRun(currentId,r=>r.state==='completed');
    assert(run.headed && run.screenshots.length===3,'Visible session incomplete');return {run_id:currentId};
  });
  await check('page_refresh_retains_history',async()=>{
    await owner.page.reload(); await owner.page.getByText(headlessId,{exact:true}).waitFor();
    const list=await (await request('')).json();assert(list.some(r=>r.run_id===headlessId),'Lost history');
    return {retained_state:list.find(r=>r.run_id===headlessId).state};
  });
  await check('UI_cancel_terminal_cleanup',async()=>{
    currentId=await startUI(false);await waitRun(currentId,r=>r.state==='running');
    await owner.page.getByRole('button',{name:'Cancel smoke check',exact:true}).click();
    const run=await waitRun(currentId,r=>r.state==='cancelled');return {run_id:run.run_id,state:run.state};
  });
  await check('API_restart_preserves_metadata_and_artifacts',async()=>{
    if(!rows.some(r=>r.check==='headless_UI_completion_three_private_screenshots'&&r.result==='PASS')){
      rows.push({check:'completed_metadata_artifact_restart',result:'NOT RUN',blocker:'No completed run with screenshots'});persist();
      await command('restart');assert((await request('/'+headlessId)).status()===200,'Failed-run metadata lost');
      return {scope:'failed-run metadata only; completed artifact check NOT RUN'};
    }
    await command('restart');const run=await (await request('/'+headlessId)).json();assert(run.state==='completed','Metadata lost');
    assert((await request(`/${headlessId}/artifacts/03-confirmed`)).status()===200,'Artifact lost');
    await owner.page.reload();await owner.page.getByText(headlessId,{exact:true}).waitFor();
  });
  await check('real_Mongo_concurrent_starts_single_lease',async()=>{
    const before=(await (await request('')).json()).length;
    const responses=await Promise.all([request('','POST',{headed:false}),request('','POST',{headed:false})]);
    assert(responses.map(r=>r.status()).sort().join(',')==='202,409','Concurrent lease contention failed');
    currentId=(await responses.find(r=>r.status()===202).json()).run_id;
    const list=await(await request('')).json();assert(list.length===before+1,'Duplicate created extra run');
    await request('/'+currentId+'/cancel','POST');await waitRun(currentId,r=>r.state==='cancelled');return {accepted:1,rejected:1};
  });
  await check('active_API_interruption_cleanup_reconciliation_no_replay_lease_recovery',async()=>{
    // Wait until monitor has released the terminal run lease, rather than retrying a failed workflow.
    await new Promise(r=>setTimeout(r,600));
    currentId=await startUI(false);await waitRun(currentId,r=>r.state==='running');
    await command('interrupt');
    const run=await waitRun(currentId,r=>['interrupted','cancelled'].includes(r.state));
    assert(run.state==='interrupted','Hard API loss must not replay or report completion');
    const response=await request('','POST',{headed:false});assert(response.status()===202,'Lease did not recover');
    const later=(await response.json()).run_id;
    await request('/'+later+'/cancel','POST');await waitRun(later,r=>r.state==='cancelled');
    return {interrupted_run:currentId,later_run:later};
  });
  await check('real_nonmember_denied_read_cancel_artifact',async()=>{
    outsider=await account('nonmember');
    for(const [suffix,method] of [['/'+headlessId,'GET'],['/'+headlessId+'/cancel','POST'],['/'+headlessId+'/artifacts/03-confirmed','GET'],['','GET']]) {
      const response=await outsider.context.request.fetch(base+'/api'+runsBase+suffix,{method});assert(response.status()===404,'Nonmember access allowed');
    }
    return {denied_operations:4};
  });
  await check('feature_disabled_new_operations_active_run_cleanup',async()=>{
    await new Promise(r=>setTimeout(r,600));
    currentId=await startUI(false);await waitRun(currentId,r=>r.state==='running');
    await command('disable');
    for(const [suffix,method,data] of [['','POST',{}],['/'+currentId,'GET'],['/'+currentId+'/cancel','POST'],['/'+headlessId+'/artifacts/03-confirmed','GET']]) {
      assert((await request(suffix,method,data)).status()===403,'Disabled feature accepted operation');
    }
    await command('enable');
    const run=await waitRun(currentId,r=>['interrupted','cancelled'].includes(r.state));
    return {state_after_configuration_restart:run.state};
  });
  await owner.context.close();if(outsider)await outsider.context.close();
}
main().catch(error=>{
  rows.push({check:stage,result:'FAIL',error_type:error.name});persist();process.exitCode=1;
}).finally(async()=>{await browser?.close();persist();});
