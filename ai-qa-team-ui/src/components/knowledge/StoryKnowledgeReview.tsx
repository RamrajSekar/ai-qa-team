"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { knowledgeRequest } from "./knowledgeApi";

interface Finding {
  finding_id: string; category: string; severity: string; description: string;
  criterion_quote?: string; knowledge_claim_id?: string;
}
interface Analysis { analysis_id: string; stale?: boolean; findings: Finding[] }
interface Decision {
  finding_id: string; decision: "intentional_change" | "correct_story" | "needs_clarification";
  action: "replace" | "remove"; rule_id: string; expected_result: string; rationale: string;
}
interface Review {
  review_id: string; analysis_id: string; status: string; stale: boolean; timing: "now" | "later";
  target_release: string; decisions: Decision[];
  changes: { action: string; before: string; after: string | null; expected_behavior: string; reason: string }[];
  impact: Record<string, { id: string; title: string }[]>;
  approver?: { approved_by_name: string; approved_at: string };
}
interface Listing { knowledge_version_id: string | null; rules: {claim_id: string; statement: string}[]; reviews: Review[] }

export default function StoryKnowledgeReview({ projectId, storyId, analysis, admin, onComplete }: {
  projectId: string; storyId: string; analysis: Analysis; admin: boolean; onComplete: () => Promise<void>;
}) {
  const root = `/projects/${encodeURIComponent(projectId)}/knowledge/stories/${encodeURIComponent(storyId)}/change-reviews`;
  const [data, setData] = useState<Listing | null>(null);
  const [decisions, setDecisions] = useState<Record<string, Decision>>({});
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [timing, setTiming] = useState<"now" | "later">("now");
  const [release, setRelease] = useState("");
  const [selected, setSelected] = useState<Review | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const saveKey = useRef<{body: string; id: string} | null>(null);
  const conflicts = analysis.findings.filter(f => f.category === "knowledge_conflict");
  const blockers = analysis.findings.filter(f => f.category !== "knowledge_conflict" && f.severity === "blocker");
  const load = useCallback(async () => setData(await knowledgeRequest<Listing>(root)), [root]);
  useEffect(() => { void load().catch(e => setError(e instanceof Error ? e.message : "Could not load reviews.")); }, [load, analysis.analysis_id]);

  function decision(finding: Finding): Decision {
    return decisions[finding.finding_id] || { finding_id: finding.finding_id, decision: "intentional_change",
      action: "replace", rule_id: finding.knowledge_claim_id || "", expected_result: finding.criterion_quote || "", rationale: "" };
  }
  function edit(finding: Finding, change: Partial<Decision>) {
    setDecisions(values => ({ ...values, [finding.finding_id]: { ...decision(finding), ...change } }));
  }
  async function perform(work: () => Promise<void>) {
    setBusy(true); setError(""); setMessage("");
    try { await work(); await load(); }
    catch (failure) { setError(failure instanceof Error ? failure.message : "Response uncertain. Open the saved review before retrying."); }
    finally { setBusy(false); }
  }
  const pending = data?.reviews.filter(r => r.status !== "completed") || [];
  const lastApproved = data?.reviews.find(r => r.status === "completed");
  if (!conflicts.length && !pending.length && !error) return null;
  return <section aria-label="Story and knowledge review" className="space-y-4 border-t pt-5">
    <div><h3 className="text-lg font-semibold">Resolve knowledge conflicts</h3>
      <p className="text-sm text-slate-600">Decide whether the story changes the product or needs correction. Only a Project Admin can approve knowledge changes.</p></div>
    {lastApproved?.approver && <p className="text-sm text-emerald-700">Last knowledge change approved by {lastApproved.approver.approved_by_name} · {lastApproved.target_release}</p>}
    {!!conflicts.length && !analysis.stale && <fieldset disabled={busy} className="space-y-4">
      {conflicts.map((finding, index) => {
        const current = decision(finding);
        const rule = data?.rules.find(r => r.claim_id === finding.knowledge_claim_id);
        return <article key={finding.finding_id} className="rounded-lg border p-4 space-y-3">
          <p className="font-medium">{finding.description}</p>
          <div className="grid gap-3 md:grid-cols-2">
            <div className="rounded bg-slate-50 p-3"><p className="text-xs font-semibold uppercase text-slate-500">Current knowledge</p><p>{rule?.statement || "Load the current rule before review."}</p></div>
            <div className="rounded bg-violet-50 p-3"><p className="text-xs font-semibold uppercase text-violet-700">Story requirement</p><p>{finding.criterion_quote || "See the story requirements above."}</p></div>
          </div>
          <label className="block">Decision<select className="border rounded w-full p-2" aria-label={`Conflict decision ${index + 1}`} value={current.decision}
            onChange={e => edit(finding, { decision: e.target.value as Decision["decision"] })}>
            <option value="intentional_change">Intentional product change</option><option value="correct_story">Correct the story</option><option value="needs_clarification">Needs clarification</option>
          </select></label>
          {current.decision === "intentional_change" && <>
            <label className="block">Knowledge change<select className="border rounded w-full p-2" aria-label={`Knowledge change ${index + 1}`} value={current.action}
              onChange={e => edit(finding, { action: e.target.value as Decision["action"] })}>
              <option value="replace">Update this rule</option><option value="remove">Remove this rule</option>
            </select></label>
            <label className="block">{current.action === "remove" ? "Expected behavior after removal" : "New approved behavior"}
              <textarea className="border rounded w-full p-2" aria-label={`New behavior ${index + 1}`} maxLength={1500} value={current.expected_result}
                onChange={e => edit(finding, { expected_result: e.target.value })} /></label>
          </>}
          <label className="block">Reason<textarea className="border rounded w-full p-2" aria-label={`Change reason ${index + 1}`} maxLength={2000} value={current.rationale}
            onChange={e => edit(finding, { rationale: e.target.value })} /></label>
        </article>;
      })}
      {blockers.map((finding, index) => <label className="block" key={finding.finding_id}>{finding.description}
        <textarea className="border rounded w-full p-2" aria-label={`Other blocker answer ${index + 1}`} maxLength={2000} value={answers[finding.finding_id] || ""}
          onChange={e => setAnswers(values => ({ ...values, [finding.finding_id]: e.target.value }))} /></label>)}
      <label className="block">When should knowledge change?<select aria-label="Knowledge change timing" className="border rounded p-2 ml-2" value={timing} onChange={e => setTiming(e.target.value as "now" | "later")}>
        <option value="now">After approval</option><option value="later">Future release — activate later</option>
      </select></label>
      {timing === "later" && <label className="block">Target release<input aria-label="Change target release" className="border rounded p-2 ml-2" value={release} maxLength={100} onChange={e => setRelease(e.target.value)} /></label>}
      <button className="workspace-button workspace-primary" disabled={!data?.knowledge_version_id || conflicts.some(f => {
        const d = decision(f); return !d.rationale.trim() || (d.decision === "intentional_change" && !d.expected_result.trim());
      }) || blockers.some(f => !answers[f.finding_id]?.trim()) || (timing === "later" && !release.trim())} onClick={() => void perform(async () => {
        const body = { analysis_id: analysis.analysis_id, parent_version_id: data!.knowledge_version_id, timing, target_release: timing === "later" ? release : "Current",
          decisions: conflicts.map(f => { const d = decision(f); return { finding_id: f.finding_id, decision: d.decision, rationale: d.rationale,
            ...(d.decision === "intentional_change" ? { action: d.action, rule_id: d.rule_id, expected_result: d.expected_result } : {}) }; }),
          resolutions: blockers.map(f => ({ finding_id: f.finding_id, decision: "clarified", rationale: answers[f.finding_id] })) };
        const serialized = JSON.stringify(body);
        if (saveKey.current?.body !== serialized) saveKey.current = { body: serialized, id: crypto.randomUUID().replaceAll("-", "") };
        setSelected(await knowledgeRequest<Review>(root, { ...body, request_id: saveKey.current.id }));
        setMessage(admin ? "Review the exact changes below before approval." : "Submitted for Project Admin review.");
      })}>{admin ? "Review changes" : "Submit for review"}</button>
    </fieldset>}
    {!!pending.length && <div className="space-y-2"><h4 className="font-semibold">Pending reviews ({pending.length})</h4>{pending.map(review =>
      <div key={review.review_id} className="flex items-center justify-between gap-3 rounded border p-3"><span>{review.target_release} · {review.status === "submitted" ? "Awaiting review" : review.status === "approved_pending" ? "Approved · pending update" : "Finishing update"}{review.stale && review.status !== "reconciling" ? " · Inputs changed" : ""}</span>
        <button className="workspace-button" disabled={busy} onClick={() => setSelected(review)}>Review</button></div>)}</div>}
    {selected && <section aria-label="Story change summary" className="rounded-lg border p-4 space-y-3">
      <h4 className="font-semibold">Review changes · {selected.target_release}</h4>
      {selected.changes.map((change, index) => <div key={index} className="border-b pb-3"><p><strong>{change.action === "remove" ? "Remove rule" : "Update rule"}</strong></p>
        <p className="text-sm text-slate-600">Current: {change.before}</p><p>After: {change.after || "Rule removed"}</p><p className="text-sm">Reason: {change.reason}</p></div>)}
      {selected.decisions.some(d => d.decision !== "intentional_change") && <p>Follow-up is needed. Correct the story or clarify the decisions before approval. Existing knowledge remains unchanged.</p>}
      {selected.decisions.filter(d => d.decision !== "intentional_change").map(d => <p key={d.finding_id}>{d.decision === "correct_story" ? "Correct the story" : "Needs clarification"}: {d.rationale}</p>)}
      <details><summary>Affected scenarios and test cases ({Object.values(selected.impact).reduce((sum, items) => sum + items.length, 0)})</summary>
        {Object.entries(selected.impact).map(([kind, items]) => <div key={kind}><strong>{kind === "scenarios" ? "Scenarios" : "Test cases"}</strong><ul>{items.map(item => <li key={item.id}>{item.title}</li>)}</ul></div>)}</details>
      <p className="text-sm">Unrelated knowledge is retained. Affected designs will need review; execution history stays unchanged.</p>
      {selected.approver && <p className="text-sm">Approved by {selected.approver.approved_by_name}</p>}
      {selected.status === "completed" ? <p role="status">Story change approved and knowledge updated.</p> : admin && <>
        {selected.stale && selected.status !== "reconciling" ? <p>Inputs changed. Submit a new review against the current story and knowledge.</p> : <button className="workspace-button workspace-primary" disabled={busy || selected.decisions.some(d => d.decision !== "intentional_change")}
          onClick={() => void perform(async () => {
            const action = selected.timing === "later" && ["approved_pending", "reconciling"].includes(selected.status) ? "activate" : "approve";
            const saved = await knowledgeRequest<Review>(`${root}/${selected.review_id}/${action}`, {});
            setSelected(saved); await onComplete();
            setMessage(saved.status === "approved_pending" ? "Approved for the future release. Current knowledge is unchanged." : "Story change approved and knowledge updated.");
          })}>{selected.status === "reconciling" ? "Finish update" : selected.timing === "later" ? selected.status === "approved_pending" ? "Activate knowledge update" : "Approve for future release" : "Approve story and update knowledge"}</button>}
      </>}
    </section>}
    {error && <p role="alert">{error}</p>}{message && <p role="status">{message}</p>}
  </section>;
}
