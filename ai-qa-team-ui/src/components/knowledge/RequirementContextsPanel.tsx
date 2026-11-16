"use client";
import {useCallback,useEffect,useRef,useState} from "react";
import {useProjects} from "@/hooks/useProjects";
import {knowledgeRequest} from "./knowledgeApi";

interface Decision{finding_id:string|null;decision:"intentional_change"|"correct_story"|"needs_clarification";rationale:string;action:"add"|"replace"|"remove";rule_id:string;expected_result:string}
interface Context{context_id:string;status:string;stale:boolean;basis:string;target_release:string;decisions:Decision[];effective_decisions?:Decision[];approver?:{approved_by_name:string;approved_at:string};impact?:Record<string,{id:string;title:string}[]>}
interface Analysis{analysis_id:string;status:string;stale?:boolean;analysis_mode?:string;findings:{finding_id:string;description:string}[]}
const blank=():Decision=>({finding_id:null,decision:"intentional_change",rationale:"",action:"replace",rule_id:"",expected_result:""});
export default function RequirementContextsPanel({projectId,storyId,selected,onSelect,onActivated}:{projectId:string;storyId:string;selected:string|null;onSelect:(value:string)=>void;onActivated?:()=>Promise<void>}){
 const {projects}=useProjects();const admin=projects.find(p=>p.project_id===projectId)?.current_user_role==="ADMIN";
 const root=`/projects/${encodeURIComponent(projectId)}/knowledge/stories/${encodeURIComponent(storyId)}`;
 const [knowledgeVersion,setKnowledgeVersion]=useState<string|null>(null);
 const [rows,setRows]=useState<Context[]>([]);const [rules,setRules]=useState<{claim_id:string;statement:string}[]>([]);
 const [analysis,setAnalysis]=useState<Analysis|null>(null);const [detail,setDetail]=useState<Context|null>(null);
 const [basis,setBasis]=useState("approved_change");const [release,setRelease]=useState("");const [decisions,setDecisions]=useState<Decision[]>([blank()]);
 const [error,setError]=useState("");const [busy,setBusy]=useState(false);const [message,setMessage]=useState("");
 const saveKey=useRef<{body:string;id:string}|null>(null);
 const load=useCallback(async()=>{
  const [data,current]=await Promise.all([knowledgeRequest<{contexts:Context[];rules:{claim_id:string;statement:string}[];current_knowledge_version_id?:string|null}>(root+"/requirements"),knowledgeRequest<Analysis|null>(root+"/analysis")]);
  if(!Array.isArray(data.contexts)||!Array.isArray(data.rules))throw new Error("Release contexts unavailable. Current approved knowledge remains a separate explicit choice.");
  setRows(data.contexts);setRules(data.rules);setKnowledgeVersion(data.current_knowledge_version_id||null);setAnalysis(current);
 },[root]);
 useEffect(()=>{let active=true;const refresh=()=>{if(active)void load().catch(e=>setError(e instanceof Error?e.message:"Could not load requirements."));};refresh();window.addEventListener("story-analysis-updated",refresh);return()=>{active=false;window.removeEventListener("story-analysis-updated",refresh);};},[load]);
 async function act(work:()=>Promise<void>){setBusy(true);setError("");setMessage("");try{await work();await load();}catch(e){setError(e instanceof Error?e.message:"Request failed; reload to reconcile before retrying.");}finally{setBusy(false);}}
 function edit(index:number,change:Partial<Decision>){setDecisions(values=>values.map((value,i)=>i===index?{...value,...change}:value));}
 return <section aria-label="Release requirements" className="workspace-card p-5 space-y-4"><h2>Release requirements &amp; generation context</h2>
  <p>Current approved knowledge stays intact. An intentional change requires its own approval. Activation applies to the named release and flags affected designs; execution history is preserved.</p>
  <label className="block">Generation context<select aria-label="Generation context" value={selected??""} disabled={busy} onChange={event=>onSelect(event.target.value)}><option value="" disabled>Choose the requirements to use</option><option value="current">Current approved product knowledge</option>{rows.map(row=><option key={row.context_id} value={row.context_id} disabled={row.stale||!["approved","active"].includes(row.status)}>{row.target_release} · {row.basis==="story_only_provisional"?"Provisional story-only":"Approved requirement change"} · {row.stale?"Stale":row.status}</option>)}</select></label>
  <p>Story-only designs remain provisional and never claim validation against product knowledge. Selecting a context does not generate anything.</p>
  <details><summary>Record a requirement decision or prepare provisional designs</summary><fieldset disabled={busy} className="space-y-3">
   <label className="block">Design basis<select aria-label="Design basis" value={basis} onChange={e=>setBasis(e.target.value)}><option value="approved_change">Intentional product change</option><option value="story_only_provisional">Provisional story-only designs</option></select></label>
   <label className="block">Target release / cycle<input aria-label="Target release / cycle" value={release} maxLength={100} onChange={e=>setRelease(e.target.value)} /></label>
   {basis==="approved_change"&&decisions.map((decision,index)=><article key={index} className="border rounded p-3 space-y-2" aria-label={`Requirement decision ${index+1}`}>
    <label className="block">Finding<select aria-label={`Finding ${index+1}`} value={decision.finding_id||""} onChange={e=>edit(index,{finding_id:e.target.value||null})}><option value="">Additional explicit requirement</option>{analysis?.findings.map(f=><option key={f.finding_id} value={f.finding_id}>{f.description}</option>)}</select></label>
    <label className="block">Decision<select aria-label={`Decision ${index+1}`} value={decision.decision} onChange={e=>edit(index,{decision:e.target.value as Decision["decision"]})}><option value="intentional_change">Intentional product change</option><option value="correct_story">Story needs correction</option><option value="needs_clarification">Needs clarification</option></select></label>
    {decision.decision==="intentional_change"&&<><label className="block">Change<select aria-label={`Change ${index+1}`} value={decision.action} onChange={e=>edit(index,{action:e.target.value as Decision["action"]})}><option value="add">Add requirement</option><option value="replace">Correct requirement</option><option value="remove">Remove requirement</option></select></label>
     {decision.action!=="add"&&<label className="block">Affected approved rule<select aria-label={`Affected rule ${index+1}`} value={decision.rule_id} onChange={e=>edit(index,{rule_id:e.target.value})}><option value="">Choose an approved rule</option>{rules.map(rule=><option key={rule.claim_id} value={rule.claim_id}>{rule.statement}</option>)}</select></label>}
     <label className="block">Expected behavior<textarea aria-label={`Expected behavior ${index+1}`} value={decision.expected_result} maxLength={1500} onChange={e=>edit(index,{expected_result:e.target.value})} /></label><p>State the final release behavior, including unaffected behavior that must still be tested. For removal, explicitly state the absence to verify. Original conflicting story criteria are not used as release expectations.</p></>}
    <label className="block">Reason<textarea aria-label={`Reason ${index+1}`} value={decision.rationale} maxLength={2000} onChange={e=>edit(index,{rationale:e.target.value})} /></label>
    {decisions.length>1&&<button className="workspace-button" onClick={()=>setDecisions(values=>values.filter((_,i)=>i!==index))}>Remove decision</button>}
   </article>)}
   {basis==="approved_change"&&<button className="workspace-button" disabled={decisions.length>=40} onClick={()=>setDecisions(values=>[...values,blank()])}>Add decision</button>}
   <p>Review the current story analysis before approval. Correct-story and clarification decisions are saved for follow-up and cannot approve a product change. Changed content requires a new saved draft.</p>
   <button className="workspace-button" disabled={!analysis||analysis.stale||!release.trim()} onClick={()=>void act(async()=>{
    const body={analysis_id:analysis!.analysis_id,basis,target_release:release,decisions:basis==="story_only_provisional"?[]:decisions.map(d=>({finding_id:d.finding_id,decision:d.decision,rationale:d.rationale,...(d.decision==="intentional_change"?{action:d.action,rule_id:d.action==="add"?null:d.rule_id,expected_result:d.expected_result}:{})}))};
    const serialized=JSON.stringify([body,analysis!.status,knowledgeVersion,rows.filter(row=>row.status==="active").map(row=>row.context_id)]);if(saveKey.current?.body!==serialized)saveKey.current={body:serialized,id:crypto.randomUUID().replaceAll("-","")};
    setDetail(await knowledgeRequest<Context>(root+"/requirements",{...body,request_id:saveKey.current!.id}));setMessage("Requirements draft saved. Nothing was activated or generated.");
   })}>Save requirements draft</button>
  </fieldset></details>
  <div className="space-y-2">{rows.map(row=><div key={row.context_id} className="workspace-row"><span>{row.target_release} · {row.basis==="story_only_provisional"?"Provisional story-only":"Product change"} · {row.stale?"Stale":row.status}</span><button className="workspace-button" disabled={busy} onClick={()=>void act(async()=>{const saved=await knowledgeRequest<Context>(root+"/requirements/"+row.context_id);setDetail(saved);setBasis(saved.basis);setRelease(saved.target_release);setDecisions(saved.decisions.length?saved.decisions.map(d=>({...blank(),...d})):[blank()]);saveKey.current=null;})}>Review</button></div>)}</div>
  {detail&&<section aria-label="Requirements approval review" className="space-y-3 border rounded p-3"><h3>{detail.target_release} · {detail.status}</h3>{detail.decisions.map((d,i)=><p key={i}>{d.decision.replaceAll("_"," ")} · {d.action} · {d.expected_result} · Reason: {d.rationale}</p>)}
   {!!detail.effective_decisions?.length&&<details><summary>All effective release expectations (including retained changes)</summary><ul>{detail.effective_decisions.map((d,i)=><li key={i}>{d.expected_result} · Reason: {d.rationale}</li>)}</ul></details>}
   {detail.basis==="story_only_provisional"&&<p>This review permits provisional drafts only. It does not approve product knowledge or authorize automated execution.</p>}
   <h4>Affected existing designs</h4>{Object.entries(detail.impact||{}).map(([kind,items])=><div key={kind}><strong>{kind}</strong>{items.length?<ul>{items.map(item=><li key={item.id}>{item.title} ({item.id})</li>)}</ul>:<p>None found.</p>}</div>)}
   {detail.approver&&<p>Approved by {detail.approver.approved_by_name} · {detail.approver.approved_at}</p>}
   {admin&&detail.status==="draft"&&<button className="workspace-button workspace-primary" disabled={busy||detail.stale||analysis?.status!=="reviewed"||detail.decisions.some(d=>d.decision!=="intentional_change")} onClick={()=>void act(async()=>{setDetail(await knowledgeRequest<Context>(root+"/requirements/"+detail.context_id+"/approve",{}));setMessage("Requirements context approved. Select it explicitly for generation.");})}>Approve requirements context</button>}
   {admin&&["approved","activating"].includes(detail.status)&&detail.basis==="approved_change"&&<button className="workspace-button" disabled={busy||(detail.stale&&detail.status!=="activating")} onClick={()=>{if(!window.confirm(`Activate requirements for ${detail.target_release}? Affected designs will need review; execution history stays intact.`))return;void act(async()=>{setDetail(await knowledgeRequest<Context>(root+"/requirements/"+detail.context_id+"/activate",{}));await onActivated?.();setMessage("Release requirements activated; affected designs marked for review.");});}}>Activate release requirements</button>}
  </section>}
  {error&&<p role="alert">{error}</p>}{message&&<p role="status">{message}</p>}
 </section>;
}
