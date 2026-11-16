"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { knowledgeRequest } from "./knowledgeApi";
import { useProjects } from "@/hooks/useProjects";
import { DesignBadge } from "@/components/projects/DesignWorkspace";
import StoryKnowledgeReview from "./StoryKnowledgeReview";

interface Analysis {
  analysis_id: string; status: string; stale?: boolean; summary: string; knowledge_version_id: string | null;
  analysis_mode?: "story_only" | "knowledge_aware";
  excluded_knowledge_claims?: {claim_id:string;statement:string;source_id:string;reason:string}[];
  findings: { finding_id: string; category: string; severity: string; description: string; question: string;
    criterion_quote?: string; knowledge_claim_id?: string }[];
  resolutions?: { finding_id: string; decision: "clarified" | "dismissed"; rationale: string }[];
}
export default function StoryAnalysisPanel({ projectId, storyId }: { projectId: string; storyId: string }) {
  const { projects } = useProjects();
  const canReview = projects.find(item => item.project_id === projectId)?.current_user_role === "ADMIN";
  const [mode,setMode]=useState<"story_only"|"knowledge_aware">("story_only");
  const [category, setCategory] = useState("all");
  const [loaded, setLoaded] = useState(false);
  const categories: Record<string,string> = {gap:"Coverage gap",ambiguity:"Ambiguity",missing_detail:"Missing detail",knowledge_conflict:"Knowledge conflict"};
  const base = `/projects/${encodeURIComponent(projectId)}/knowledge/stories/${encodeURIComponent(storyId)}`;
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [resolutions, setResolutions] = useState<Record<string, { decision: "clarified" | "dismissed"; rationale: string }>>({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const load = useCallback(async () => {
    try {
      setError("");
      const data = await knowledgeRequest<Analysis | null>(base + "/analysis");
      setAnalysis(data);
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
  return <section id="story-analysis" className="workspace-card p-5 space-y-3" aria-label="Story analysis">
    <h2 className="text-xl font-semibold">Review story clarity</h2>
    <p>Story clarity finds ambiguity and missing details without using product knowledge. Knowledge comparison uses only independently sourced approved rules. Each analysis uses an AI request; choosing a mode does not start one.</p>
    <Link className="underline" href={`/projects/${projectId}/knowledge`}>Teach your QA Agent</Link>
    <label className="block">Analysis mode<select aria-label="Analysis mode" value={mode} disabled={busy} onChange={event=>setMode(event.target.value as "story_only"|"knowledge_aware")}><option value="story_only">Story clarity (story-only)</option><option value="knowledge_aware">Check against product knowledge</option></select></label>
    <div><button className="workspace-button" disabled={busy} onClick={() => void perform(false)}>Analyze with AI</button></div>
    <p role="status"><DesignBadge>{!loaded ? "Loading" : error && !analysis ? "Unavailable" : !analysis ? "Not analyzed" : analysis.stale ? "Stale" : analysis.status === "reviewed" ? "Reviewed" : "Findings need review"}</DesignBadge></p>
    {analysis && <>
      <p>{analysis.analysis_mode === "story_only" ? "Story-only analysis — not validated against approved product knowledge. Review does not authorize knowledge-aware generation." : "Knowledge-aware analysis"}</p>
      <p>{analysis.stale ? "Inputs changed. Analyze again and review the new findings." : "Review findings and clarify missing expectations."} {analysis.knowledge_version_id && <Link className="underline" href={`/projects/${projectId}/knowledge#knowledge-version-${analysis.knowledge_version_id}`}>Inspect approved knowledge version</Link>}</p>
      {!!analysis.excluded_knowledge_claims?.length&&<section aria-label="Excluded knowledge rules"><h3>Rules excluded from this comparison</h3><p>These rules cannot validate their own source story. This comparison does not authorize generation against the full knowledge snapshot.</p><ul>{analysis.excluded_knowledge_claims.map(claim=><li key={claim.claim_id}><strong>{claim.statement}</strong> — {claim.reason}</li>)}</ul></section>}
      <p>{analysis.summary}</p>
      <label>Finding category<select aria-label="Finding category" value={category} onChange={event => setCategory(event.target.value)}><option value="all">All findings</option>{Object.entries(categories).map(([value,label]) => <option key={value} value={value}>{label}</option>)}</select></label>
      {!analysis.findings.length && <p>No findings proposed. Explicit review is still required.</p>}
      {analysis.findings.filter(finding => (analysis.stale || finding.category !== "knowledge_conflict") && (category === "all" || finding.category === category)).map(finding => <div className="border rounded p-3 space-y-2" key={finding.finding_id}>
        <p><strong>{finding.severity === "blocker" ? "Blocker" : "Warning"} · {categories[finding.category] || finding.category}</strong>: {finding.description}</p><p>{finding.question}</p>
        {finding.criterion_quote && <blockquote>Acceptance criterion: {finding.criterion_quote}</blockquote>}
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
      <StoryKnowledgeReview key={analysis.analysis_id} projectId={projectId} storyId={storyId} analysis={analysis} admin={canReview}
        onComplete={async () => { await load(); window.dispatchEvent(new Event("story-analysis-updated")); }} />
    </>}
    {error && <p role="alert">{error}</p>}
  </section>;
}
