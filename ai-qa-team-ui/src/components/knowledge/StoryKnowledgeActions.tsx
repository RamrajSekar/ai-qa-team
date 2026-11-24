"use client";
import {useEffect,useState} from "react";
import {useRouter} from "next/navigation";
import {knowledgeRequest,type TrainingSession} from "./knowledgeApi";

interface Options {version_id:string|null;pending_review_id:string|null;rules:{claim_id:string;statement:string}[]}
export default function StoryKnowledgeActions({projectId,storyId}:{projectId:string;storyId:string}){
 const router=useRouter();const [busy,setBusy]=useState(false);const [error,setError]=useState("");
 const [options,setOptions]=useState<Options|null>(null);const [selected,setSelected]=useState("");const [updating,setUpdating]=useState(false);const [reload,setReload]=useState(0);
 const root=`/projects/${encodeURIComponent(projectId)}/knowledge/stories/${encodeURIComponent(storyId)}/knowledge-proposals`;
 useEffect(()=>{
  let cancelled=false;setOptions(null);setError("");setUpdating(false);setSelected("");
  void knowledgeRequest<Options>(root).then(value=>{if(!cancelled)setOptions(value);}).catch(e=>{if(!cancelled)setError(e instanceof Error?e.message:"Could not load knowledge actions.");});
  return ()=>{cancelled=true;};
 },[root,reload]);
 async function create(update=false){
  setBusy(true);setError("");
  try{
   const review=await knowledgeRequest<TrainingSession>(root,update?{change_type:"update",claim_id:selected,base_version_id:options?.version_id}:{change_type:"add"});
   router.push(`/projects/${encodeURIComponent(projectId)}/knowledge?review=${encodeURIComponent(review.review_id)}`);
  }catch(e){setError(e instanceof Error?e.message:"Could not confirm the draft. Retry to resume the same proposal.");}
  finally{setBusy(false);}
 }
 return <section className="space-y-3 border-t pt-4" aria-label="Knowledge from approved story">
  <h3 className="font-semibold">Knowledge</h3><p className="text-sm">Create a draft in QA Agent Review. No AI request is used.</p>
  {!options&&!error&&<p role="status">Loading knowledge actions...</p>}
  <div className="flex flex-wrap gap-2">
   {options?.pending_review_id ? <button className="workspace-button" disabled={busy} onClick={()=>router.push(`/projects/${encodeURIComponent(projectId)}/knowledge?review=${encodeURIComponent(options.pending_review_id!)}`)}>Review knowledge</button> : options && (options.rules.length ?
    <button className="workspace-button" disabled={busy} onClick={()=>setUpdating(true)}>Update knowledge</button> :
    <button className="workspace-button" disabled={busy} onClick={()=>void create()}>Add knowledge</button>)}
  </div>
  {options&&updating&&<div className="space-y-2">
   {options.rules.length?<><label className="block">Approved knowledge<select aria-label="Approved knowledge" disabled={busy} className="block w-full border rounded p-2" value={selected} onChange={event=>setSelected(event.target.value)}><option value="">Select knowledge to update</option>{options.rules.map(rule=><option key={rule.claim_id} value={rule.claim_id}>{rule.statement}</option>)}</select></label>
    <button className="workspace-button workspace-primary" disabled={busy||!selected} onClick={()=>void create(true)}>Create update draft</button></>:<p>No approved knowledge to update. Use Add knowledge.</p>}
  </div>}
  {error&&<div><p role="alert">{error}</p><button className="workspace-button" disabled={busy} onClick={()=>setReload(value=>value+1)}>Retry</button></div>}
 </section>;
}
