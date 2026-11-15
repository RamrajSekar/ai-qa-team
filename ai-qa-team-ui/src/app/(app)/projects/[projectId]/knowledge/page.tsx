"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { useFeatures } from "@/components/providers/FeatureFlagsProvider";
import { useProjects } from "@/hooks/useProjects";
import { WorkspaceDialog } from "@/components/ui/workspace-dialog";
import { DesignStats } from "@/components/projects/DesignWorkspace";
import TrainingReview from "@/components/knowledge/TrainingReview";
import { knowledgeRequest, type Source, type KnowledgeVersion, type TrainingSession } from "@/components/knowledge/knowledgeApi";

interface Overview { sources: Source[]; versions: KnowledgeVersion[]; active_version_id: string | null }
export default function KnowledgePage() {
  const { projectId } = useParams<{projectId:string}>();
  return <QAAgentWorkspace key={projectId} projectId={projectId} />;
}

function QAAgentWorkspace({projectId}:{projectId:string}) {
  const { projects } = useProjects();
  const { enabled } = useFeatures();
  const storiesEnabled = enabled("story_management");
  const [stories,setStories] = useState<{story_id:string;title:string}[]>([]);
  const [storyId,setStoryId] = useState("");
  const canApprove = projects.find(item => item.project_id === projectId)?.current_user_role === "ADMIN";
  const base = `/projects/${encodeURIComponent(projectId)}/knowledge`;
  const [data, setData] = useState<Overview>({sources:[],versions:[],active_version_id:null});
  const [ready,setReady] = useState(false);
  const [sessions,setSessions] = useState<TrainingSession[]>([]);
  const [selected,setSelected] = useState<TrainingSession | null>(null);
  const [tab,setTab] = useState<"teach"|"review"|"approved">("teach");
  const [epoch,setEpoch] = useState(0);
  const [title,setTitle] = useState(""); const [text,setText] = useState("");
  const [kind,setKind] = useState<Source["kind"]>("document");
  const [start,setStart] = useState(0); const [end,setEnd] = useState(60);
  const [reviewPending,setReviewPending] = useState(false);
  const [busy,setBusy] = useState(false); const [error,setError] = useState("");
  const [evidence,setEvidence] = useState<Source | null>(null);
  const requestKey = useRef<string | null>(null);
  const load = useCallback(async () => {
    const [overview, reviews] = await Promise.all([knowledgeRequest<Overview>(base),knowledgeRequest<TrainingSession[]>(base+"/training")]);
    if (overview.active_version_id && !overview.versions.some(item=>item.version_id===overview.active_version_id)) {
      overview.versions.unshift(await knowledgeRequest<KnowledgeVersion>(base+"/versions/"+overview.active_version_id));
    }
    setData(overview);setSessions(reviews);setReady(true);return reviews;
  },[base]);
  useEffect(()=>{
    if(!storiesEnabled)return;
    let active=true;void knowledgeRequest<{story_id:string;title:string}[]>(`/stories?project_id=${encodeURIComponent(projectId)}&skip=0&limit=100`).then(rows=>{if(active&&Array.isArray(rows))setStories(rows);}).catch(()=>{});
    return()=>{active=false;};
  },[projectId,storiesEnabled]);
  const onSession = useCallback((review:TrainingSession) => {
    setSelected(review);setSessions(items=>[review,...items.filter(item=>item.review_id!==review.review_id)]);
    if(review.state === "rejected")setTab("teach");
    if(review.saved_version?.status === "approved")setTab("approved");
  },[]);
  function choose(review:TrainingSession) {
    setTab("review");setReviewPending(false);onSession(review);setEpoch(value=>value+1);
    const url=new URL(window.location.href);url.searchParams.set("review",review.review_id);window.history.replaceState(window.history.state,"",url);
  }
  useEffect(()=>{
    let active=true;
    void load().then(async()=>{
      const identity=new URL(window.location.href).searchParams.get("review");
      const review=identity ? await knowledgeRequest<TrainingSession>(base+"/training/"+encodeURIComponent(identity)) : undefined;
      if(active && review && review.state!=="rejected"){setSelected(review);setTab(review.saved_version?.status === "approved" ? "approved" : "review");}
      if(active && window.location.hash)setTab("approved");
    }).catch(()=>{if(active)setError("Could not load QA Agent reviews. Reload to try again.");});
    return()=>{active=false;};
  },[base,load]);
  async function act(work:()=>Promise<void>) {
    setBusy(true);setError("");try{await work();}catch(failure){setError(failure instanceof Error?failure.message:"Request failed. Refresh status before retrying.");}finally{setBusy(false);}
  }
  const current=data.versions.find(version=>version.version_id===data.active_version_id);
  async function inspect(id:string) {
    await act(async()=>setEvidence(data.sources.find(item=>item.source_id===id) || await knowledgeRequest<Source>(base+"/sources/"+id)));
  }
  async function revise(claimId:string,mode:"correction"|"removal") {
    if(mode==="removal"&&!window.confirm("Remove this approved rule? A removal draft will be created. The rule stays approved until a project administrator reviews and approves that removal."))return;
    await act(async()=>{
      const review=await knowledgeRequest<TrainingSession>(base+"/training",{request_id:crypto.randomUUID().replaceAll("-",""),title:mode==="correction"?"Correct an approved rule":"Remove an approved rule",mode,claim_id:claimId});
      choose(review);await load();
    });
  }
  if(!ready)return <div className="design-state" role={error?"alert":"status"}>{error||"Loading your QA Agent…"}</div>;
  return <div className="design-page">
    <header><p className="workspace-eyebrow">QA Agent</p><h1>Your QA Agent</h1><p className="workspace-description">Teach product knowledge, review what the agent learned, and save approved project memory. This does not train the underlying model.</p></header>
    <div className="workspace-actions" role="tablist" aria-label="QA Agent workflow">{(["teach","review","approved"] as const).map(value=><button key={value} id={`tab-${value}`} role="tab" aria-selected={tab===value} aria-controls={`panel-${value}`} className={`workspace-button ${tab===value ? "workspace-primary" : ""}`} disabled={reviewPending || busy} onClick={()=>setTab(value)}>{value === "teach" ? "Teach" : value === "review" ? `Review (${sessions.filter(item=>item.state!=="rejected"&&item.saved_version?.status!=="approved").length})` : "Approved"}</button>)}</div>
    <DesignStats items={[{label:"Approved rules",value:current?.claims.length||0},{label:"Pending reviews",value:sessions.filter(item=>item.state!=="rejected"&&item.saved_version?.status!=="approved").length}]} />
    <div id="panel-teach" role="tabpanel" aria-labelledby="tab-teach" hidden={tab!=="teach"}><section id="teach-agent" className="workspace-card p-5 space-y-4"><h2>Teach Agent</h2><p>Additional training retains existing knowledge automatically. Use non-sensitive product notes; do not enter credentials or personal data. Document, image and media uploads remain disabled.</p>
      <fieldset disabled={busy||reviewPending} className="space-y-3 border-0 p-0 m-0">
        <label className="block">Training title<input className="border rounded w-full" value={title} maxLength={200} onChange={event=>{setTitle(event.target.value);requestKey.current=null;}} /></label>
        <label className="block">Training source<select value={kind} onChange={event=>{setKind(event.target.value as Source["kind"]);requestKey.current=null;}}><option value="document">Product notes</option><option value="recording_transcript">Pasted timestamped transcript</option></select></label>
        {kind==="recording_transcript"&&<div className="workspace-actions"><label>Start seconds<input type="number" min={0} max={1800} value={start} onChange={event=>{setStart(Number(event.target.value));requestKey.current=null;}} /></label><label>End seconds<input type="number" min={start} max={1800} value={end} onChange={event=>{setEnd(Number(event.target.value));requestKey.current=null;}} /></label></div>}
        <label className="block">What should your QA Agent know?<textarea className="border rounded w-full" rows={6} maxLength={kind==="document"?60000:12000} value={text} onChange={event=>{setText(event.target.value);requestKey.current=null;}} /></label>
        <button className="workspace-button workspace-primary" disabled={!title.trim()||!text.trim()} onClick={()=>void act(async()=>{
          requestKey.current ||=crypto.randomUUID().replaceAll("-","");
          const review=await knowledgeRequest<TrainingSession>(base+"/training",{request_id:requestKey.current,title,mode:"training",source:{title,kind,text:kind==="document"?text:"",segments:kind==="document"?[]:[{start_seconds:start,end_seconds:end,text}]}});
          choose(review);
          // Only this intentional submission starts extraction. Mount/refresh never does.
          try{choose(await knowledgeRequest<TrainingSession>(base+"/training/"+review.review_id+"/extract",{}));setText("");setTitle("");requestKey.current=null;}
          finally{await load();}
        })}>{busy?"Working…":"Teach agent"}</button>
      </fieldset><p>Submission uses your configured AI provider and allowance. Pending reviews and completed extraction results are saved for resuming later.</p>
    </section>
    {storiesEnabled&&<details className="workspace-card p-5"><summary>Suggest knowledge from a story</summary><p>Story suggestions are inferred proposals. They cannot independently validate their own originating story.</p><label>Source story<select value={storyId} onChange={event=>setStoryId(event.target.value)}><option value="">Select a story</option>{stories.map(story=><option key={story.story_id} value={story.story_id}>{story.title}</option>)}</select></label><button className="workspace-button" disabled={busy||reviewPending||!storyId} onClick={()=>void act(async()=>{
      const review=await knowledgeRequest<TrainingSession>(base+"/training",{request_id:crypto.randomUUID().replaceAll("-",""),title:"Knowledge from story",mode:"training",story_id:storyId});choose(review);
      try{choose(await knowledgeRequest(base+"/training/"+review.review_id+"/extract",{}));}finally{await load();}
    })}>Suggest knowledge from story</button></details>}
    </div><div id="panel-review" role="tabpanel" aria-labelledby="tab-review" hidden={tab!=="review"}><section className="workspace-card p-5 space-y-3" aria-label="Saved training reviews"><h2>Continue a training review</h2>
      {!sessions.some(review=>review.state!=="rejected"&&review.saved_version?.status!=="approved")&&<p>No pending training reviews.</p>}
      {sessions.filter(review=>review.state!=="rejected"&&review.saved_version?.status!=="approved").map(review=><div className="flex flex-wrap justify-between gap-3 border-b py-3" key={review.review_id}><div><strong>{review.title}</strong><p>{review.state==="saved"?"Awaiting approval":review.extraction_state==="completed"?"Review in progress":review.extraction_state==="uncertain"?"Extraction needs attention":review.extraction_state==="running"?"Extracting knowledge":"Training saved"}</p></div><button className="workspace-button" disabled={busy||reviewPending} onClick={()=>void act(async()=>choose(await knowledgeRequest(base+"/training/"+review.review_id)))}>Resume review</button></div>)}
    </section>
    <section id="review-training" className="workspace-card p-5 space-y-3">
      {selected&&<><button className="workspace-button" disabled={busy} onClick={()=>{if(reviewPending&&!window.confirm("Reload saved review? Changes not yet saved may be lost."))return;void act(async()=>{choose(await knowledgeRequest(base+"/training/"+selected.review_id));await load();});}}>Refresh status</button><TrainingReview key={`${selected.review_id}:${epoch}`} initial={selected} base={base} canApprove={canApprove} onSession={onSession} onRefresh={async()=>{await load();}} onInspect={id=>void inspect(id)} onPendingChange={setReviewPending} currentVersionId={data.active_version_id} sources={data.sources} /></>}
      {!selected&&<p>Teach your agent or select a saved review to continue.</p>}
    </section>
    </div><div id="panel-approved" role="tabpanel" aria-labelledby="tab-approved" hidden={tab!=="approved"}><section id="approved-knowledge" className="workspace-card p-5 space-y-4" aria-label="Approved knowledge"><h2>Approved knowledge</h2>
      {!current?.claims.length&&<p>No approved knowledge yet.</p>}
      {!!current?.claims.length&&<p>Approved by {current.approved_by_name || "Reviewer name unavailable"}</p>}
      {!!current?.claims.length && <div className="overflow-x-auto"><table className="w-full text-left" aria-label="Current approved knowledge"><thead><tr><th className="p-3">Knowledge</th><th className="p-3">Source / topic</th><th className="p-3">Category</th><th className="p-3">Information type</th><th className="p-3">Actions</th></tr></thead><tbody>{current.claims.map(claim=><tr key={claim.claim_id} id={`claim-${current.version_id}-${claim.claim_id}`} className="border-t" aria-label="Approved rule"><td className="p-3 min-w-48">{claim.statement}</td><td className="p-3">{data.sources.find(source=>source.source_id===claim.source_id)?.title || "Product knowledge"}</td><td className="p-3">{claim.category.replaceAll("_"," ")}</td><td className="p-3">{claim.epistemic_status}</td><td className="p-3"><div className="workspace-actions"><button className="workspace-button" onClick={()=>void inspect(claim.source_id)}>Review</button><button className="workspace-button" disabled={busy||reviewPending} onClick={()=>void revise(claim.claim_id,"correction")}>Edit</button><button className="workspace-button" disabled={busy||reviewPending} onClick={()=>void revise(claim.claim_id,"removal")}>Remove</button></div></td></tr>)}</tbody></table></div>}
    </section>
    </div>{error&&<p role="alert">{error} Completed extraction is retained. Refresh or resume the saved review; do not repeat an uncertain AI request blindly.</p>}
    <WorkspaceDialog open={!!evidence} onClose={()=>setEvidence(null)} title="Source evidence"><h2>{evidence?.title}</h2><p className="whitespace-pre-wrap">{evidence?.kind==="document"?evidence.text:evidence?.segments.map(segment=>`[${segment.start_seconds}–${segment.end_seconds}s] ${segment.text}`).join("\n")}</p><button className="workspace-button" onClick={()=>setEvidence(null)}>Close evidence</button></WorkspaceDialog>
  </div>;
}
