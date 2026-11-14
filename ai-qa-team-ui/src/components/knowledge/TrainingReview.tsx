"use client";
import { useEffect, useState } from "react";
import { knowledgeRequest, type Claim, type Source, type TrainingSession, type TrainingProposal } from "./knowledgeApi";
import { DesignBadge } from "@/components/projects/DesignWorkspace";

export default function TrainingReview({ initial, base, canApprove, onSession, onRefresh, onInspect, onPendingChange, currentVersionId, sources }: {
  initial: TrainingSession; base: string; canApprove: boolean; onSession: (session: TrainingSession) => void;
  onRefresh: () => Promise<void>; onInspect: (id: string) => void;
  onPendingChange: (pending: boolean) => void;
  currentVersionId: string | null;
  sources: Source[];
}) {
  const [session, setSession] = useState(initial);
  const [proposals, setProposals] = useState(initial.proposals);
  const [answers, setAnswers] = useState(initial.clarification_answers);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [editId, setEditId] = useState<string | null>(null);
  const [saveNote, setSaveNote] = useState("Review progress saved");
  const path = `${base}/training/${session.review_id}`;
  const editable = session.state === "reviewing" && session.extraction_state === "completed";
  useEffect(() => { onPendingChange(dirty || saving); }, [dirty, saving, onPendingChange]);

  useEffect(() => {
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); };
    const guard = (event: MouseEvent) => {
      const link = (event.target as Element)?.closest("a");
      if (link && new URL(link.href).pathname !== window.location.pathname) {
        event.preventDefault(); event.stopPropagation();
        setSaveNote("Wait for Review progress saved before navigating away.");
      }
    };
    window.addEventListener("beforeunload", warn);
    document.addEventListener("click", guard, true);
    return () => { window.removeEventListener("beforeunload", warn); document.removeEventListener("click", guard, true); };
  }, [dirty]);

  useEffect(() => {
    if (!dirty || saving || !editable || error) return;
    const timer = setTimeout(() => {
      setSaving(true); setSaveNote("Saving review progress…");
      void knowledgeRequest<TrainingSession>(path + "/review", {
        expected_revision: session.revision, proposals, clarification_answers: answers,
      }).then(result => {
        setSession(result); onSession(result); setDirty(false); setSaveNote("Review progress saved");
      }).catch(failure => { setError(failure instanceof Error ? failure.message : "Could not save review. Refresh status before continuing.");
        setSaveNote("Changes not saved. Refresh status to reconcile before continuing.");
      }).finally(() => setSaving(false));
    }, 450);
    return () => clearTimeout(timer);
  }, [dirty, saving, editable, error, path, session.revision, proposals, answers, onSession]);

  function update(id: string, changes: Partial<TrainingProposal>, claimChanges?: Partial<Claim>) {
    setProposals(items => items.map(item => item.claim.claim_id === id ? {
      ...item, ...changes, claim: { ...item.claim, ...claimChanges },
    } : item)); setDirty(true); setError(""); setSaveNote("Unsaved changes");
  }

  async function perform(work: () => Promise<TrainingSession>) {
    setSaving(true); setError("");
    try { const result = await work(); setSession(result); setProposals(result.proposals); setAnswers(result.clarification_answers);
      setDirty(false); if (result.state !== "reviewing") setEditId(null);
      setSaveNote("Review progress saved"); onSession(result); await onRefresh(); }
    catch (failure) { setError(failure instanceof Error ? failure.message : "Could not complete request. Refresh status."); }
    finally { setSaving(false); }
  }
  const unresolved = proposals.some(item => (item.decision !== "confirmed" && item.decision !== "rejected") ||
    (item.decision === "confirmed" && item.clarification_question?.trim() && !item.clarification_answer?.trim())) || Object.values(answers).some(value => !value.trim());
  const accepted = proposals.some(item => item.decision === "confirmed") || session.removed_claim_ids.length > 0;
  return <section aria-label="Training review" className="workspace-card p-5 space-y-4">
    <div><p className="workspace-eyebrow">Review</p><h2>Review What the Agent Learned</h2><p>{session.title}</p></div>
    <p>Existing approved knowledge is retained automatically. Confirmed proposals are saved only after explicit approval.</p>
    {session.base_version_id !== currentVersionId && session.saved_version?.status !== "approved" && <div className="design-state">
      <p>Approved knowledge changed. Your review and extraction are retained. Review these proposals against current knowledge without another AI request.</p>
      <button className="workspace-button" disabled={dirty || saving} onClick={() => void perform(() => knowledgeRequest(path + "/rebase", {
        request_id: crypto.randomUUID().replaceAll("-", ""), expected_revision: session.revision,
      }))}>Review against current knowledge</button>
    </div>}
    {session.extraction_state !== "completed" && <>
      <p role="status">{session.extraction_state === "running" ? "Extraction is running. Refresh status; no automatic retry will occur." : session.extraction_state === "uncertain" ? "The extraction outcome is uncertain. Refresh first. An explicit retry may spend another AI request." : "Training is saved. Extraction has not started."}</p>
      {session.extraction_state !== "running" && <button className="workspace-button" disabled={saving} onClick={() => {
        const uncertain = session.extraction_state === "uncertain";
        if (uncertain && !window.confirm("Retry extraction? The previous request may already have been charged. This explicit retry may use another AI request.")) return;
        void perform(() => knowledgeRequest(path + "/extract", { retry_uncertain: uncertain, expected_attempt: session.attempt }));
      }}>{session.extraction_state === "uncertain" ? "Retry extraction explicitly" : "Start extraction"}</button>}
    </>}
    {session.mode === "removal" && <p role="status">You explicitly selected removal of one approved rule. Other rules remain unchanged. Review the saved removal before approving it.</p>}
    <fieldset disabled={saving} className="space-y-4 border-0 p-0 m-0">
      {proposals.map((item, index) => <article className="border rounded p-4 space-y-3" key={item.claim.claim_id} aria-label={`Proposal ${index + 1}`}>
        <div className="workspace-actions"><strong>{item.claim.category.replaceAll("_", " ")}</strong><DesignBadge tone={item.decision === "confirmed" ? "positive" : item.decision === "rejected" ? "negative" : "warning"}>{item.decision}</DesignBadge><span>{item.claim.epistemic_status}</span></div>
        <p className="whitespace-pre-wrap">{item.claim.statement}</p>
        <blockquote>{item.claim.quote}</blockquote><button className="workspace-button" type="button" onClick={() => onInspect(item.claim.source_id)}>Inspect source</button>
        {item.claim.segment_index !== null && <p>Transcript segment {item.claim.segment_index + 1}</p>}
        {editable && <div className="workspace-actions">
          <button type="button" className="workspace-button" onClick={() => update(item.claim.claim_id, { decision: "confirmed" })}>Confirm</button>
          <button type="button" className="workspace-button" onClick={() => setEditId(editId === item.claim.claim_id ? null : item.claim.claim_id)}>Edit</button>
          <button type="button" className="workspace-button" onClick={() => update(item.claim.claim_id, { decision: "rejected" }, session.proposals.find(proposal => proposal.claim.claim_id === item.claim.claim_id)?.claim)}>Reject</button>
          <button type="button" className="workspace-button" onClick={() => update(item.claim.claim_id, { decision: "clarify" })}>Clarify</button>
        </div>}
        {item.decision === "clarify" && <p>Clarification needed. Edit the statement using source evidence, then confirm or reject it. The proposal stays pending until then.</p>}
        {editable && (item.decision === "clarify" || item.clarification_question) && <div className="space-y-2">
          <label className="block">Clarification question<textarea aria-label="Clarification question" className="border rounded w-full" maxLength={1000} value={item.clarification_question || ""} onChange={event => update(item.claim.claim_id, { clarification_question: event.target.value, decision: "clarify" })} /></label>
          <label className="block">Clarification answer<textarea aria-label="Clarification answer" className="border rounded w-full" maxLength={2000} value={item.clarification_answer || ""} onChange={event => update(item.claim.claim_id, { clarification_answer: event.target.value, decision: "clarify" })} /></label>
        </div>}
        {editable && editId === item.claim.claim_id && <div className="space-y-3">
          <label className="block">Rule statement<textarea aria-label="Rule statement" className="border rounded w-full" maxLength={1500} value={item.claim.statement} onChange={event => update(item.claim.claim_id, { decision: "pending" }, { statement: event.target.value })} /></label>
          <label className="block">Information type<select value={item.claim.epistemic_status} onChange={event => update(item.claim.claim_id, { decision: "pending" }, { epistemic_status: event.target.value as Claim["epistemic_status"] })}>{["expected", "observed", "inferred", "unknown"].map(value => <option key={value}>{value}</option>)}</select></label>
          <p>A correction still needs supporting source evidence. Exact source quotes cannot be invented or changed into requirements automatically.</p>
          <label className="block">Supporting source<select value={item.claim.source_id} onChange={event => update(item.claim.claim_id, {decision:"pending"}, {source_id:event.target.value, segment_index:sources.find(source=>source.source_id===event.target.value)?.kind === "recording_transcript" ? 0 : null})}>
            {!sources.some(source=>source.source_id===item.claim.source_id) && <option value={item.claim.source_id}>Current source evidence</option>}
            {sources.map(source=><option key={source.source_id} value={source.source_id}>{source.title}</option>)}
          </select></label>
          {sources.find(source=>source.source_id===item.claim.source_id)?.kind === "recording_transcript" && <label>Transcript segment<select value={item.claim.segment_index ?? 0} onChange={event=>update(item.claim.claim_id,{decision:"pending"},{segment_index:Number(event.target.value)})}>{sources.find(source=>source.source_id===item.claim.source_id)?.segments.map((segment,index)=><option key={index} value={index}>{segment.start_seconds}–{segment.end_seconds}s</option>)}</select></label>}
          <label className="block">Exact source quote<textarea aria-label="Exact source quote" className="border rounded w-full" maxLength={1200} value={item.claim.quote} onChange={event => update(item.claim.claim_id, { decision: "pending" }, { quote: event.target.value })} /></label>
        </div>}
      </article>)}
      {session.clarification_questions.map(question => <label className="block" key={question}>{question}<textarea aria-label={question} disabled={!editable} className="border rounded w-full" maxLength={2000} value={answers[question] || ""} onChange={event => { setAnswers(current => ({ ...current, [question]: event.target.value })); setDirty(true); setError(""); setSaveNote("Unsaved changes"); }} /></label>)}
    </fieldset>
    {editable && <><p role="status">{saveNote}</p><p>Unresolved clarifications block saving for approval. Rejecting a proposal never deletes an existing rule.</p>
      <button className="workspace-button workspace-primary" disabled={saving || dirty || unresolved || !accepted || !!error} onClick={() => void perform(() => knowledgeRequest(path + "/save", { expected_revision: session.revision }))}>Save for approval</button></>}
    {session.saved_version && <section aria-label="Saved knowledge changes" className="space-y-3">
      <h3>Review additions, modifications and removals</h3>
      {(session.saved_version.changes || []).map(change => <div key={change.claim_id} className="border rounded p-3"><strong>{change.action === "add" ? "Addition" : change.action === "replace" ? "Modification" : "Removal"}</strong>{change.before && <p>Before: {change.before.statement}</p>}{change.after && <p>After: {change.after.statement}</p>}</div>)}
      <p>{session.saved_version.claims.length} rules in this complete version, including retained knowledge.</p>
      {session.saved_version.status === "approved" ? <p role="status">Knowledge approved and saved.</p> : canApprove ? <button className="workspace-button workspace-primary" disabled={saving} onClick={() => void perform(async () => {
        await knowledgeRequest(`${base}/versions/${session.saved_version!.version_id}/approve`, {});
        return knowledgeRequest<TrainingSession>(path);
      })}>Approve knowledge</button> : <p>A project administrator must approve this saved knowledge. Your review is available to the project team.</p>}
    </section>}
    {error && <p role="alert">{error} Your saved review is retained. Use Refresh status before further actions.</p>}
  </section>;
}
