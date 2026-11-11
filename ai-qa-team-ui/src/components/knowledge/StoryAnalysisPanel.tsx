"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { knowledgeRequest } from "./knowledgeApi";

interface Analysis {
  analysis_id: string; status: string; stale?: boolean; summary: string; knowledge_version_id: string;
  findings: { finding_id: string; category: string; severity: string; description: string; question: string;
    criterion_quote?: string; knowledge_claim_id?: string }[];
  resolutions?: { finding_id: string; decision: "clarified" | "dismissed"; rationale: string }[];
}
export default function StoryAnalysisPanel({ projectId, storyId }: { projectId: string; storyId: string }) {
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
  return <section className="workspace-card p-5 space-y-3" aria-label="Story analysis">
    <h2 className="text-xl font-semibold">Review story against product knowledge</h2>
    <p>Review gaps, ambiguity, missing details and conflicts before generation. Story or knowledge changes require a new review.</p>
    <Link className="underline" href={`/projects/${projectId}/knowledge`}>Teach &amp; review product knowledge</Link>
    <div><button className="workspace-button" disabled={busy} onClick={() => void perform(false)}>Analyze with AI</button></div>
    {analysis && <>
      <p role="status">{analysis.stale ? "Stale — analyze current inputs again" : analysis.status} · Knowledge {analysis.knowledge_version_id}</p>
      <p>{analysis.summary}</p>
      {analysis.findings.map(finding => <div className="border rounded p-3 space-y-2" key={finding.finding_id}>
        <p><strong>{finding.severity} · {finding.category}</strong>: {finding.description}</p><p>{finding.question}</p>
        {finding.criterion_quote && <blockquote>Acceptance criterion: {finding.criterion_quote}</blockquote>}
        {finding.knowledge_claim_id && <p>Knowledge rule: {finding.knowledge_claim_id}</p>}
        {analysis.status !== "reviewed" && !analysis.stale && <>
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
      {analysis.status !== "reviewed" && !analysis.stale && <button className="workspace-button" disabled={busy || analysis.findings.some(item => item.severity === "blocker" && !resolutions[item.finding_id]?.rationale.trim())}
        onClick={() => void perform(true)}>Approve analysis review (project admin)</button>}
    </>}
    {error && <p role="alert">{error}</p>}
  </section>;
}
