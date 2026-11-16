// Synthetic API/auth doubles for browser UX checks. Never a live account/session.
const assert = require('node:assert/strict');
const base = process.env.FEATURE_UI_URL || 'http://127.0.0.1:3125';
async function fixture(browser, t, {role='ADMIN',empty=false,withoutCriteria=false,ask=false}={}) {
 const context=await browser.newContext();t.after(()=>context.close());
 await context.addCookies([{name:'access_token',value:'synthetic-ui-fixture',url:base}]);
 const root='/projects/P1/knowledge', sources=[],versions=[],reviews=[],calls=[];let active=null,counter=0,projects=empty?[]:[{project_id:'P1',name:'Synthetic project',current_user_role:role}];
 let analysis=null;
 const id=()=> (++counter).toString(16).padStart(32,'0');
 const user={email:'fixture@example.com',name:'Fixture',onboarding:{onboarding_status:'completed'},subscription:{usage:{},limits:{}}};
 await context.route('http://feature-api.test/**',async route=>{
  const request=route.request(),url=new URL(request.url()),path=url.pathname,method=request.method();
  const headers={'access-control-allow-origin':base,'access-control-allow-credentials':'true','access-control-allow-headers':'content-type','access-control-allow-methods':'GET,POST,PATCH,OPTIONS'};
  if(method==='OPTIONS')return route.fulfill({status:204,headers});
  const body=request.postData()?request.postDataJSON():null;calls.push({path,method,body});let json=[],status=200;
  if(path==='/features')json={knowledge_ask:ask,product_knowledge:true,story_analysis:true,story_management:true,scenario_generation:true,test_generation:true};
  if(path==='/auth/me')json={user};
  if(path==='/projects'){if(method==='POST')projects=[{project_id:'P1',name:body.name,current_user_role:role}];json=method==='POST'?projects[0]:projects;}
  if(path==='/projects/P1')json=projects[0];
  if(path==='/stories')json=[{story_id:'ST1',title:'Save draft',description:'Save',acceptance_criteria:'Show Draft saved.'}];
  if(path==='/stories/ST1')json={story_id:'ST1',title:'Save draft',description:'Users save drafts for later editing.',acceptance_criteria:withoutCriteria?'':'Show Draft saved.'};
  if(path===root)json={sources,versions,active_version_id:active};
  if(path===root+'/training'){
   if(method==='POST'){
    let r=reviews.find(r=>r.review_id===body.request_id);
    if(!r){const parent=versions.find(v=>v.version_id===active);r={review_id:body.request_id,title:body.title,mode:body.mode||'training',source_id:null,base_version_id:active,draft_version_id:id(),state:'reviewing',revision:0,attempt:0,extraction_state:body.mode==='training'?'not_started':'completed',proposals:[],clarification_questions:[],clarification_answers:{},removed_claim_ids:[],source:body.source};
     if(body.mode==='correction')r.proposals=[{claim:structuredClone(parent.claims.find(c=>c.claim_id===body.claim_id)),decision:'pending'}];
     if(body.mode==='removal')r.removed_claim_ids=[body.claim_id];reviews.unshift(r);}
    json=r;
   }else json=reviews;
  }
  if(path.startsWith(root+'/training/')){
   const [identity,operation]=path.slice((root+'/training/').length).split('/');const r=reviews.find(r=>r.review_id===identity);assert.ok(r,'known review');json=r;
   if(operation==='extract'){
    if(r.extraction_state!=='completed'){
     const source={...r.source,source_id:id()};sources.push(source);r.source_id=source.source_id;r.attempt++;r.revision++;
     r.proposals=source.text.split('\n').filter(Boolean).map(text=>({claim:{claim_id:'K_'+id(),category:'business_rule',statement:text,quote:text,source_id:source.source_id,segment_index:null,epistemic_status:'expected'},decision:'pending'}));
     r.clarification_questions=source.text.includes('four')?['When does rule four apply?']:[];r.clarification_answers=Object.fromEntries(r.clarification_questions.map(q=>[q,'']));r.extraction_state='completed';
    }
   }
   if(operation==='discard'){r.state='rejected';r.proposals=[];r.removed_claim_ids=[];r.clarification_questions=[];r.clarification_answers={};}
   if(operation==='review'){
    assert.equal(body.expected_revision,r.revision);r.proposals=body.proposals;r.clarification_answers=body.clarification_answers;r.removal_reason=body.removal_reason;r.revision++;
   }
   if(operation==='save'&&!r.saved_version){
    assert.equal(body.expected_revision,r.revision);assert.ok(r.proposals.every(p=>['confirmed','rejected'].includes(p.decision)));if(!r.removed_claim_ids.length&&r.proposals.every(p=>p.decision==='rejected')){r.state='rejected';return route.fulfill({status,headers,json:r});}assert.ok(Object.values(r.clarification_answers).every(Boolean));
    const previous=versions.find(v=>v.version_id===active)?.claims||[];const merged=new Map(previous.filter(c=>!r.removed_claim_ids.includes(c.claim_id)).map(c=>[c.claim_id,structuredClone(c)]));const changes=[];
    for(const p of r.proposals.filter(p=>p.decision==='confirmed')){const before=merged.get(p.claim.claim_id)||null;changes.push({action:before?'replace':'add',claim_id:p.claim.claim_id,before,after:p.claim});merged.set(p.claim.claim_id,p.claim);}
    for(const key of r.removed_claim_ids)changes.push({action:'remove',claim_id:key,before:previous.find(c=>c.claim_id===key),after:null});
    const version={version_id:r.draft_version_id,title:r.title,claims:[...merged.values()],status:'draft',changes,clarification_answers:{...r.clarification_answers,...Object.fromEntries(r.proposals.filter(p=>p.decision==='confirmed'&&p.clarification_question).map(p=>[p.clarification_question,p.clarification_answer]))},content_digest:'d'.repeat(64)};versions.unshift(version);r.saved_version=version;r.state='saved';
   }
  }
  if(path.startsWith(root+'/versions/')){const identity=path.slice((root+'/versions/').length).split('/')[0];json=versions.find(v=>v.version_id===identity);if(path.endsWith('/approve')){if(role!=='ADMIN'){status=403;json={detail:'Project administrator required.'};}else{json.status='approved';json.approved_by='fixture-id';json.approved_by_name='Fixture';active=json.version_id;}}}
  if(path.startsWith(root+'/sources/'))json=sources.find(s=>s.source_id===path.slice((root+'/sources/').length));
  if(path===root+'/stories/ST1/requirements')json={contexts:[],rules:[]};
  if(path===root+'/stories/ST1/analysis')json=analysis;
  if(path===root+'/stories/ST1/analyze')json=analysis={analysis_id:'a'.repeat(32),status:'needs_review',summary:'Clarify timing',analysis_mode:url.searchParams.get('analysis_mode')||(active?'knowledge_aware':'story_only'),knowledge_version_id:url.searchParams.get('analysis_mode')==='story_only'?null:active,findings:[{finding_id:'F1',category:'missing_detail',severity:'blocker',description:'Missing timing',question:'When should confirmation appear?'}]};
  if(path.endsWith('/analysis/'+'a'.repeat(32)+'/review'))json=analysis={...analysis,status:'reviewed',resolutions:body.resolutions};
  if(path===root+'/ask')json=active?{status:'supported',answer:'Rule one applies.',knowledge_version_id:active,citations:[{claim_id:versions.find(v=>v.version_id===active).claims[0].claim_id,quote:'Rule one.',source_id:sources[0].source_id,source_quote:'Rule one.',information_type:'expected',segment_index:null}]}:{status:'not_covered',answer:'No current approved knowledge covers this question.',knowledge_version_id:null,citations:[]};
  if(path===root+'/analysis-summaries')json={ST1:{state:analysis?.stale?'stale':analysis?.status==='reviewed'?'reviewed':'not_analyzed',finding_count:analysis?.findings.length||0,blocker_count:1}};
  if(path==='/scenarios/generate-from-story')json={scenarios:[{scenario_id:'SC1'}],summary:{message:'1 of 4 requested scenarios generated (allowed 4).'}};
  await route.fulfill({status,headers,json});
 });
 const page=await context.newPage();page.setDefaultTimeout(45000);page.setDefaultNavigationTimeout(120000);
 const errors=[];page.on('pageerror',e=>errors.push(e.message));t.after(()=>assert.deepEqual(errors,[]));
 return {page,calls,versions,reviews,sources,context,setRole:value=>{role=value;projects.forEach(p=>p.current_user_role=value);}};
}
async function teach(page,title,text){await page.getByRole('tab',{name:'Teach',exact:true}).click();await page.getByLabel('Training title',{exact:true}).fill(title);await page.getByLabel('What should your QA Agent know?',{exact:true}).fill(text);await page.getByRole('button',{name:'Teach agent',exact:true}).click();await page.getByRole('region',{name:'Training review',exact:true}).waitFor();await page.getByRole('article',{name:'Proposal 1',exact:true}).waitFor();}
async function confirmAll(page){const cards=page.getByRole('article',{name:/^Proposal /});for(let i=0;i<await cards.count();i++){const saved=page.waitForResponse(response=>response.url().endsWith('/review')&&response.request().method()==='POST');await cards.nth(i).getByRole('button',{name:'Confirm',exact:true}).click();await saved;await page.getByRole('status').filter({hasText:/^Review progress saved$/}).waitFor();}}
async function saveApprove(page){await page.getByRole('button',{name:'Review changes',exact:true}).click();await page.getByRole('button',{name:'Approve changes',exact:true}).click();await page.getByRole('tab',{name:'Approved',exact:true}).click();await page.waitForFunction(()=>!document.querySelector('#teach-agent fieldset').disabled);}
module.exports={fixture,teach,confirmAll,saveApprove,base};
