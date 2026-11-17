"use client";
import {useCallback,useEffect,useRef,useState} from "react";
import {useProjects} from "@/hooks/useProjects";
import {knowledgeRequest} from "./knowledgeApi";
import Link from "next/link";

interface Context {context_id:string;basis:string;target_release:string;status:string;stale:boolean;approver?:{approved_by_name:string}}
interface Analysis {analysis_id:string;status:string;stale?:boolean}
export default function GenerationRequirements({projectId,storyId,selected,onSelect}:{
 projectId:string;storyId:string;selected:string|null;onSelect:(value:string|null)=>void;
}){
 const {projects}=useProjects();const admin=projects.find(p=>p.project_id===projectId)?.current_user_role==="ADMIN";
 const root=`/projects/${encodeURIComponent(projectId)}/knowledge/stories/${encodeURIComponent(storyId)}`;
 const [mode,setMode]=useState("");const [analysis,setAnalysis]=useState<Analysis|null>(null);
 const [loaded,setLoaded]=useState(false);
 const [rows,setRows]=useState<Context[]>([]);const [busy,setBusy]=useState(false);const [error,setError]=useState("");
 const [reviewOpen,setReviewOpen]=useState(false);

 const request=useRef<{analysis:string;id:string}|null>(null);
 const load=useCallback(async()=>{
  const [contexts,review]=await Promise.all([knowledgeRequest<{contexts:Context[]}>(root+"/requirements"),knowledgeRequest<Analysis|null>(root+"/analysis")]);
  setRows(contexts.contexts||[]);setAnalysis(review);setLoaded(true);
 },[root]);
 useEffect(()=>{const refresh=()=>{void load().catch(e=>setError(e instanceof Error?e.message:"Could not load generation requirements."));};refresh();window.addEventListener("story-analysis-updated",refresh);return()=>window.removeEventListener("story-analysis-updated",refresh);},[load]);
 const approved=rows.find(row=>row.basis==="story_only_provisional"&&row.target_release==="Story requirements"&&!row.stale&&row.status==="approved");
 const selectedRow=rows.find(row=>row.context_id===selected);
 const invalidStory=mode==="story"&&(!approved||selected!==approved.context_id);
 useEffect(()=>{if(invalidStory&&selected)onSelect(null);},[invalidStory,selected,onSelect]);
 return <div className="space-y-3" aria-label="Generation requirements">
  <label className="block text-sm font-medium">Requirements for generation
   <select className="border rounded p-2 block" aria-label="Requirements for generation" value={mode} disabled={busy||!loaded} onChange={e=>{
    const next=e.target.value;setMode(next);setReviewOpen(false);setError("");onSelect(next==="knowledge"?"current":approved?.context_id||null);
   }}><option value="" disabled>Choose requirements</option><option value="story">Story requirements</option><option value="knowledge">Story + approved knowledge</option></select>
  </label>
  {mode==="story"&&<div className="text-sm space-y-2">
   <p>Story-only drafts require review and are not validated against product knowledge.</p>
   {approved&&selected===approved.context_id?<p className="text-emerald-700">Approved for generation{approved.approver?.approved_by_name?` by ${approved.approver.approved_by_name}`:""}.</p>:<>
    {!analysis||analysis.stale||analysis.status!=="reviewed"?<p><Link className="workspace-button" href={`/projects/${projectId}/stories/${storyId}#story-analysis`}>Review story</Link></p>:admin?<button type="button" className="workspace-button" disabled={busy} onClick={()=>setReviewOpen(true)}>Review and approve for generation</button>:<p>A Project Admin must approve these story requirements for generation.</p>}
    {reviewOpen&&analysis&&<section className="border rounded p-3 space-y-2" aria-label="Story generation approval"><p>Approve the selected story as the basis for story-only drafts. Product knowledge stays unchanged.</p>
     <button className="workspace-button workspace-primary" disabled={busy} onClick={async()=>{
      setBusy(true);setError("");try{
       if(request.current?.analysis!==analysis.analysis_id)request.current={analysis:analysis.analysis_id,id:crypto.randomUUID().replaceAll("-","")};
       const saved=await knowledgeRequest<Context>(root+"/generation-approval",{analysis_id:analysis.analysis_id,request_id:request.current.id});
       await load();onSelect(saved.context_id);setReviewOpen(false);
      }catch(e){setError(e instanceof Error?e.message:"Approval response uncertain. Check the saved approval before retrying.");}finally{setBusy(false);}
     }}>Approve for generation</button></section>}
   </>}
  </div>}
  {mode==="knowledge"&&<p className="text-sm">Uses the current approved knowledge and reviewed story. Conflicts and source checks still apply.</p>}
  {selectedRow?.basis==="approved_change"&&<p className="text-sm">Selected release: {selectedRow.target_release}</p>}
  {mode==="knowledge"&&rows.some(row=>row.basis==="approved_change"&&!row.stale&&["approved","active"].includes(row.status))&&<label className="block text-sm">Target release<select aria-label="Target release" value={selected||"current"} onChange={e=>onSelect(e.target.value)}><option value="current">Current knowledge</option>{rows.filter(row=>row.basis==="approved_change"&&!row.stale&&["approved","active"].includes(row.status)).map(row=><option key={row.context_id} value={row.context_id}>{row.target_release}</option>)}</select></label>}
  {error&&<p role="alert">{error}</p>}
 </div>;
}
