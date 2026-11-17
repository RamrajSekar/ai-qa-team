"use client";
import {useCallback,useEffect,useRef,useState} from "react";
import {useProjects} from "@/hooks/useProjects";
import {knowledgeRequest} from "./knowledgeApi";
import RequirementContextsPanel from "./RequirementContextsPanel";

interface Context {context_id:string;basis:string;target_release:string;status:string;stale:boolean;approver?:{approved_by_name:string}}
interface Analysis {analysis_id:string;status:string;stale?:boolean}
export default function GenerationRequirements({projectId,storyId,selected,onSelect,onActivated}:{
 projectId:string;storyId:string;selected:string|null;onSelect:(value:string|null)=>void;onActivated:()=>Promise<void>;
}){
 const {projects}=useProjects();const admin=projects.find(p=>p.project_id===projectId)?.current_user_role==="ADMIN";
 const root=`/projects/${encodeURIComponent(projectId)}/knowledge/stories/${encodeURIComponent(storyId)}`;
 const [mode,setMode]=useState("");const [analysis,setAnalysis]=useState<Analysis|null>(null);
 const [loaded,setLoaded]=useState(false);
 const [rows,setRows]=useState<Context[]>([]);const [busy,setBusy]=useState(false);const [error,setError]=useState("");
 const [reviewOpen,setReviewOpen]=useState(false);
 const [optionalOpen,setOptionalOpen]=useState(false);
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
    {!analysis||analysis.stale||analysis.status!=="reviewed"?<p>Complete the current story review above first.</p>:admin?<button type="button" className="workspace-button" disabled={busy} onClick={()=>setReviewOpen(true)}>Review and approve for generation</button>:<p>A Project Admin must approve these story requirements for generation.</p>}
    {reviewOpen&&analysis&&<section className="border rounded p-3 space-y-2" aria-label="Story generation approval"><p>Approve the story description and acceptance criteria shown above as the basis for provisional scenario drafts. This does not update product knowledge.</p>
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
  <details onToggle={event=>setOptionalOpen(event.currentTarget.open)}><summary className="cursor-pointer text-sm">Optional release settings</summary>
   {optionalOpen&&<RequirementContextsPanel projectId={projectId} storyId={storyId} selected={selected} onSelect={value=>{setMode("");onSelect(value);}} onActivated={onActivated}/>}
  </details>
  {error&&<p role="alert">{error}</p>}
 </div>;
}
