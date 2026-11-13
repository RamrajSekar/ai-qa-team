"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { knowledgeRequest } from "./knowledgeApi";
import { useProjects } from "@/hooks/useProjects";
import { DesignBadge } from "@/components/projects/DesignWorkspace";

interface Analysis {
  analysis_id: string; status: string; stale?: boolean; summary: string; knowledge_version_id: string;
  findings: { finding_id: string; category: string; severity: string; description: string; question: string;
    criterion_quote?: string; knowledge_claim_id?: string }[];
  resolutions?: { finding_id: string; decision: "clarified" | "dismissed"; rationale: string }[];
}
export default function StoryAnalysisPanel({ projectId, storyId }: { projectId: string; storyId: string }) {
  const { projects } = useProjects();
  const canReview = projects.find(item => item.project_id === projectId)?.current_user_role === "ADMIN";
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
      await knowledgeRequest(base + (review ? `/analysis/${analysis?.analysis_id}/review` : "/analyze"), review ? {
        resolutions: Object.entries(resolutions).filter(([, value]) => value.rationale.trim()).map(([finding_id, value]) => ({ finding_id, ...value })),
      } : {});
      await load();
    } catch (failure) { setError(failure instanceof Error ? failure.message : "Could not analyze or review story."); }
    finally { setBusy(false); }
  }
  return <section id="story-analysis" className="workspace-card p-5 space-y-3" aria-label="Story analysis">
    <h2 className="text-xl font-semibold">Review story against product knowledge</h2>
    <p>Review gaps, ambiguity, missing details and conflicts before generation. Story or knowledge changes require a new review.</p>
    <Link className="underline" href={`/projects/${projectId}/knowledge`}>Teach &amp; review product knowledge</Link>
    <div><button className="workspace-button" disabled={busy} onClick={() => void perform(false)}>Analyze with AI</button></div>
    <p role="status"><DesignBadge>{!loaded ? "Loading" : error && !analysis ? "Unavailable" : !analysis ? "Not analyzed" : analysis.stale ? "Stale" : analysis.status === "reviewed" ? "Reviewed" : "Findings need review"}</DesignBadge></p>
    {analysis && <>
      <p>{analysis.stale ? "Analyze current inputs again before generation." : "Review findings and clarify missing expectations."} <Link className="underline" href={`/projects/${projectId}/knowledge#knowledge-version-${analysis.knowledge_version_id}`}>Inspect approved knowledge version</Link></p>
      <p>{analysis.summary}</p>
      <label>Finding category<select aria-label="Finding category" value={category} onChange={event => setCategory(event.target.value)}><option value="all">All findings</option>{Object.entries(categories).map(([value,label]) => <option key={value} value={value}>{label}</option>)}</select></label>
      {!analysis.findings.length && <p>No findings proposed. Explicit review is still required.</p>}
      {analysis.findings.filter(finding => category === "all" || finding.category === category).map(finding => <div className="border rounded p-3 space-y-2" key={finding.finding_id}>
        <p><strong>{finding.severity === "blocker" ? "Blocker" : "Warning"} · {categories[finding.category] || finding.category}</strong>: {finding.description}</p><p>{finding.question}</p>
        {finding.criterion_quote && <blockquote>Acceptance criterion: {finding.criterion_quote}</blockquote>}
        {finding.knowledge_claim_id && <Link className="underline" href={`/projects/${projectId}/knowledge#claim-${analysis.knowledge_version_id}-${finding.knowledge_claim_id}`}>Inspect linked knowledge rule</Link>}
        {canReview && analysis.status !== "reviewed" && !analysis.stale && <>
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
      {canReview && analysis.status !== "reviewed" && !analysis.stale && <button className="workspace-button" disabled={busy || analysis.findings.some(item => item.severity === "blocker" && !resolutions[item.finding_id]?.rationale.trim())}
        onClick={() => void perform(true)}>Approve analysis review (project admin)</button>}
    </>}
    {error && <p role="alert">{error}</p>}
  </section>;
}
