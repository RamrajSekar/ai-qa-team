"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { knowledgeRequest } from "./knowledgeApi";
import { useProjects } from "@/hooks/useProjects";
import { DesignBadge } from "@/components/projects/DesignWorkspace";
import StoryKnowledgeReview from "./StoryKnowledgeReview";
import StoryKnowledgeActions from "./StoryKnowledgeActions";
import {WorkspaceDialog} from "@/components/ui/workspace-dialog";

interface Analysis {
  analysis_id: string; status: string; stale?: boolean; summary: string; knowledge_version_id: string | null;
  story_approval?: {state:string;approved_by_name?:string;basis?:string};
  comparison_state?:string;
  reviewed_by_name?: string;
  analysis_mode?: "story_only" | "knowledge_aware";
  excluded_knowledge_claims?: {claim_id:string;statement:string;source_id:string;reason:string}[];
  findings: { finding_id: string; category: string; severity: string; description: string; question: string;
    criterion_quote?: string; story_quote?: string; story_field?: string; knowledge_claim_id?: string }[];
  resolutions?: { finding_id: string; decision: "clarified" | "dismissed"; rationale: string }[];
}
interface ManualReadiness {story:{title:string;description:string|null;acceptance_criteria:string|null;out_of_scope:string|null};snapshot_digest:string;blocked:boolean;approval:Analysis["story_approval"]|null}
export default function StoryAnalysisPanel({ projectId, storyId }: { projectId: string; storyId: string }) {
  const { projects } = useProjects();
  const canReview = projects.find(item => item.project_id === projectId)?.current_user_role === "ADMIN";
  const [mode,setMode]=useState<"story_only"|"knowledge_aware">("story_only");
  const [category, setCategory] = useState("all");
  const [loaded, setLoaded] = useState(false);
  const categories: Record<string,string> = {gap:"Coverage gap",ambiguity:"Ambiguity",missing_detail:"Missing detail",knowledge_conflict:"Knowledge conflict"};
  const base = `/projects/${encodeURIComponent(projectId)}/knowledge/stories/${encodeURIComponent(storyId)}`;
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [storyApproval,setStoryApproval]=useState<{name:string;reviewId:string}|null>(null);
  const [resolutions, setResolutions] = useState<Record<string, { decision: "clarified" | "dismissed"; rationale: string }>>({});
  const [manual,setManual]=useState<ManualReadiness|null>(null);
  const [manualOpen,setManualOpen]=useState(false);
  const [confirmed,setConfirmed]=useState(false);
  const [note,setNote]=useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const load = useCallback(async () => {
    try {
      setError("");
      const data = await knowledgeRequest<Analysis | null>(base + "/analysis");
      setAnalysis(data);
      if(!data)setManual(await knowledgeRequest<ManualReadiness>(base+"/manual-approval"));
      if(data?.analysis_mode)setMode(data.analysis_mode);
      setResolutions(Object.fromEntries((data?.resolutions || []).map(item => [item.finding_id, item])));
    } catch (failure) { setError(failure instanceof Error ? failure.message : "Could not load analysis."); }
    finally { setLoaded(true); }
  }, [base]);
  useEffect(() => { void load(); }, [load]);
  async function perform(review: boolean) {
    setBusy(true); setError("");
    try {
      await knowledgeRequest(base + (review ? `/analysis/${analysis?.analysis_id}/review` : `/analyze?analysis_mode=${mode}`), review ? {
        resolutions: Object.entries(resolutions).filter(([, value]) => value.rationale.trim()).map(([finding_id, value]) => ({ finding_id, ...value })),
      } : {});
      await load();
      window.dispatchEvent(new Event("story-analysis-updated"));
    } catch (failure) { setError(failure instanceof Error ? failure.message : "Could not analyze or review story."); }
    finally { setBusy(false); }
  }
  const approvalState=analysis?.story_approval?.state || manual?.approval?.state || (storyApproval?"approved":analysis?.status==="reviewed"&&!analysis.stale?"approved":analysis?.stale?"needs_review":"in_review");
  const manualBasis=analysis?.story_approval?.basis==="manual_review"||(!analysis&&manual?.approval?.basis==="manual_review");
  const reviewer=analysis?.story_approval?.approved_by_name||manual?.approval?.approved_by_name||storyApproval?.name||analysis?.reviewed_by_name||"Reviewer name unavailable";
  return <section id="story-analysis" className="workspace-card p-5 space-y-3" aria-label="Story analysis">
    <h2 className="text-xl font-semibold">Review story clarity</h2>
    <p>Find missing details, ambiguity and knowledge conflicts. Analysis uses one AI request.</p>
    <Link className="underline" href={`/projects/${projectId}/knowledge`}>Teach your QA Agent</Link>
    <label className="block">Analysis mode<select aria-label="Analysis mode" value={mode} disabled={busy||!loaded} onChange={event=>setMode(event.target.value as "story_only"|"knowledge_aware")}><option value="story_only">Story clarity (story-only)</option><option value="knowledge_aware">Check against product knowledge</option></select></label>
    <div className="flex flex-wrap gap-2"><button className="workspace-button" disabled={busy} onClick={() => void perform(false)}>Analyze with AI</button>
    {canReview&&approvalState!=="approved"&&<button className="workspace-button" disabled={busy||!loaded} onClick={async()=>{
      setBusy(true);setError("");try{setManual(await knowledgeRequest<ManualReadiness>(base+"/manual-approval"));setConfirmed(false);setNote("");setManualOpen(true);}catch(e){setError(e instanceof Error?e.message:"Could not load story review.");}finally{setBusy(false);}
    }}>Approve manually</button>}</div>
    <p role="status"><DesignBadge>{!loaded?"Loading":error&&!analysis?"Unavailable":approvalState==="approved"?"Approved":approvalState==="needs_review"?"Needs review":"In review"}</DesignBadge></p>
    {approvalState==="approved"&&<p className="text-sm text-emerald-700">Story review completed · {reviewer}</p>}
    {!analysis&&manualBasis&&<p className="text-sm">Not analyzed. Approved through manual review.</p>}
    <WorkspaceDialog open={manualOpen} title="Approve manually" onClose={()=>{if(!busy)setManualOpen(false);}}>
      {manualOpen&&manual?.story&&<div className="space-y-3"><p>Review this story for test design. This does not analyze it or approve product knowledge.</p>
        <h3 className="font-semibold">{manual.story.title}</h3><p className="whitespace-pre-wrap">{manual.story.description}</p><p className="whitespace-pre-wrap">{manual.story.acceptance_criteria||"No acceptance criteria provided."}</p>
        {manual.story.out_of_scope&&<p>Out of scope: {manual.story.out_of_scope}</p>}
        {manual.blocked?<p role="alert">Resolve existing blockers and knowledge conflicts before manual approval.</p>:<>
        <label className="block">Review note (optional)<textarea aria-label="Review note (optional)" maxLength={2000} value={note} onChange={event=>setNote(event.target.value)} className="border rounded w-full" /></label>
        <label className="flex gap-2"><input type="checkbox" checked={confirmed} onChange={event=>setConfirmed(event.target.checked)}/>I reviewed this story and it is clear enough for test design.</label>
        <button className="workspace-button workspace-primary" disabled={busy||!confirmed} onClick={async()=>{
          setBusy(true);setError("");try{await knowledgeRequest(base+"/manual-approval",{snapshot_digest:manual.snapshot_digest,confirmed:true,note});await load();setManualOpen(false);window.dispatchEvent(new Event("story-analysis-updated"));}catch(e){setError(e instanceof Error?e.message:"Approval response uncertain. Refresh before retrying.");}finally{setBusy(false);}
        }}>Confirm approval</button></>}
      </div>}
    </WorkspaceDialog>
    {analysis && <>
      <p className="text-sm">{analysis.comparison_state==="needs_refresh"||(!analysis.comparison_state&&analysis.stale&&analysis.analysis_mode!=="story_only")?"Knowledge comparison: Needs refresh.":analysis.analysis_mode==="story_only"?"Story-only review.":"Knowledge comparison: Current."}</p>
      {analysis.stale&&<p className="text-sm">{approvalState==="approved"?"Approval is retained. Refresh the comparison before knowledge-aware generation.":"Inputs changed. Review the latest story."}</p>}
      <details open={!analysis.stale}><summary>{analysis.stale?"Previous findings":"Findings"} ({analysis.findings.length})</summary>
      {!!analysis.excluded_knowledge_claims?.length&&<section aria-label="Excluded knowledge rules"><h3>Excluded source rules</h3><p>Story-derived rules cannot validate the same story.</p><ul>{analysis.excluded_knowledge_claims.map(claim=><li key={claim.claim_id}><strong>{claim.statement}</strong> — {claim.reason}</li>)}</ul></section>}
      <p>{analysis.summary}</p>
      <label>Finding category<select aria-label="Finding category" value={category} onChange={event => setCategory(event.target.value)}><option value="all">All findings</option>{Object.entries(categories).map(([value,label]) => <option key={value} value={value}>{label}</option>)}</select></label>
      {!analysis.findings.length && <p>No findings proposed. Explicit review is still required.</p>}
      {analysis.findings.filter(finding => (analysis.stale || finding.category !== "knowledge_conflict") && (category === "all" || finding.category === category)).map(finding => <div className="border rounded p-3 space-y-2" key={finding.finding_id}>
        <p><strong>{finding.severity === "blocker" ? "Blocker" : "Warning"} · {categories[finding.category] || finding.category}</strong>: {finding.description}</p><p>{finding.question}</p>
        {finding.criterion_quote && <blockquote>Acceptance criterion: {finding.criterion_quote}</blockquote>}
        {finding.story_quote && <blockquote>Story {finding.story_field?.replaceAll("_"," ") || "excerpt"}: {finding.story_quote}</blockquote>}
        {finding.knowledge_claim_id && analysis.knowledge_version_id && <Link className="underline" href={`/projects/${projectId}/knowledge#claim-${analysis.knowledge_version_id}-${finding.knowledge_claim_id}`}>Inspect linked knowledge rule</Link>}
        {canReview && analysis.status !== "reviewed" && !analysis.stale && !analysis.findings.some(item => item.category === "knowledge_conflict") && <>
          <label className="block">Decision <select value={resolutions[finding.finding_id]?.decision || "clarified"}
            onChange={event => setResolutions(items => ({ ...items, [finding.finding_id]: {
              rationale: items[finding.finding_id]?.rationale || "", decision: event.target.value as "clarified" | "dismissed",
            } }))}><option value="clarified">Clarified</option><option value="dismissed">Dismissed with rationale</option></select></label>
          <label className="block">Clarification or rationale<textarea className="border rounded w-full" maxLength={2000}
            value={resolutions[finding.finding_id]?.rationale || ""} onChange={event => setResolutions(items => ({ ...items,
              [finding.finding_id]: { decision: items[finding.finding_id]?.decision || "clarified", rationale: event.target.value },
            }))} /></label>
        </>}
        {analysis.resolutions?.find(item => item.finding_id === finding.finding_id)?.rationale && <p>Reviewed: {analysis.resolutions.find(item => item.finding_id === finding.finding_id)?.rationale}</p>}
      </div>)}
      {canReview && analysis.status !== "reviewed" && !analysis.stale && !analysis.findings.some(item => item.category === "knowledge_conflict") && <button className="workspace-button" disabled={busy || analysis.findings.some(item => item.severity === "blocker" && !resolutions[item.finding_id]?.rationale.trim())}
        onClick={() => void perform(true)}>Approve analysis review (project admin)</button>}
      </details>
      <StoryKnowledgeReview key={analysis.analysis_id} projectId={projectId} storyId={storyId} analysis={analysis} admin={canReview} storyApproved={approvalState==="approved"}
        onStoryApproved={setStoryApproval}
        onComplete={async () => { await load(); window.dispatchEvent(new Event("story-analysis-updated")); }} />
    </>}
    {approvalState==="approved"&&<StoryKnowledgeActions projectId={projectId} storyId={storyId} />}
    {error && <p role="alert">{error}</p>}
  </section>;
}
