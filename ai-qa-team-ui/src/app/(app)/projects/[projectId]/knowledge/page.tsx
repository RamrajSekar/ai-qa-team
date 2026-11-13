"use client";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import KnowledgeUploads from "@/components/knowledge/KnowledgeUploads";
import { useProjects } from "@/hooks/useProjects";
import { knowledgeRequest, type Claim, type Source, type KnowledgeVersion } from "@/components/knowledge/knowledgeApi";

interface Overview { sources: Source[]; versions: KnowledgeVersion[]; active_version_id: string | null }
export default function KnowledgePage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { projects } = useProjects();
  const canApprove = projects.find(item => item.project_id === projectId)?.current_user_role === "ADMIN";
  const [storyId, setStoryId] = useState("");
  const [stories, setStories] = useState<{story_id:string;title:string}[]>([]);
  const base = `/projects/${encodeURIComponent(projectId)}/knowledge`;
  const [data, setData] = useState<Overview>({ sources: [], versions: [], active_version_id: null });
  const [sourceTitle, setSourceTitle] = useState("");
  const [kind, setKind] = useState<Source["kind"]>("document");
  const [text, setText] = useState("");
  const [start, setStart] = useState(0); const [end, setEnd] = useState(60);
  const [claims, setClaims] = useState<Claim[]>([]);
  const [title, setTitle] = useState("Product knowledge");
  const [parent, setParent] = useState<string | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false); const [error, setError] = useState(""); const [message, setMessage] = useState("");
  const load = useCallback(async () => { setData(await knowledgeRequest<Overview>(base)); }, [base]);
  useEffect(() => { load().catch(() => setError("Could not load project knowledge.")); }, [load]);
  async function act(work: () => Promise<void>) {
    setBusy(true); setError(""); setMessage("");
    try { await work(); } catch (failure) { setError(failure instanceof Error ? failure.message : "Request failed."); }
    finally { setBusy(false); }
  }
  useEffect(() => {
    let active = true;
    void knowledgeRequest<{story_id:string;title:string}[]>(`/stories?project_id=${encodeURIComponent(projectId)}&skip=0&limit=100`).then(rows => {if(active && Array.isArray(rows)) setStories(rows);}).catch(() => { /* Story proposals are optional; text sources remain available. */ });
    return () => {active=false;};
  }, [projectId]);
  function edit(index: number, fields: Partial<Claim>) { setClaims(items => items.map((item, i) => i === index ? { ...item, ...fields } : item)); }
  return <div className="design-page">
    <header><p className="workspace-eyebrow">Project knowledge</p><h1>Teach &amp; review product knowledge</h1><p className="workspace-description">Build reviewed project memory, then use it to analyze stories and design tests.</p></header>
    <p>Text and timestamped transcript excerpts are available. Private document intake is disabled pending storage and worker qualification. Audio/video uploads are deferred. Use non-sensitive product material; do not paste credentials or personal data.</p>
    <p>AI proposals need human correction and approval. Observed, inferred and unknown information never automatically becomes an expected requirement.</p>
    <nav className="workspace-actions" aria-label="Knowledge workflow"><a className="workspace-button" href="#knowledge-sources">Sources</a><a className="workspace-button" href="#knowledge-review">Review &amp; Clarify</a><a className="workspace-button" href="#approved-knowledge">Approved Knowledge</a></nav>
    <section id="knowledge-sources" className="space-y-4"><h2 className="text-xl font-semibold">Sources</h2>
    <KnowledgeUploads projectId={projectId} canDelete={canApprove} onReady={load} />
    <section className="border rounded p-4 space-y-3"><h3>Suggest knowledge from story</h3><p>A story supplies unapproved proposals, not independent evidence validating itself. Suggestions require review and approval.</p>
      <label>Source story<select aria-label="Source story" disabled={busy} value={storyId} onChange={event => setStoryId(event.target.value)}><option value="">Select a story</option>{stories.map(story => <option key={story.story_id} value={story.story_id}>{story.title}</option>)}</select></label>
      <button className="workspace-button" disabled={busy || !storyId} onClick={() => void act(async () => {
        const result = await knowledgeRequest<{claims:Claim[];clarification_questions:string[]}>(base + `/stories/${encodeURIComponent(storyId)}/suggest-knowledge`, {});
        setClaims(items => [...items, ...result.claims]);setAnswers(items => ({...items,...Object.fromEntries(result.clarification_questions.map(question=>[question,""]))}));await load();setMessage("Story proposals are inferred and unapproved. Review source links before saving a snapshot.");
      })}>Suggest knowledge from story</button>
    </section>
    <fieldset disabled={busy} className="border rounded p-4 space-y-3">
      <legend>Add text or transcript source</legend><p>Paste product documentation, terminology, workflows or business rules. Keep expected behavior separate from observations.</p>
      <label className="block">Source title <input className="border rounded p-2" maxLength={200} value={sourceTitle} onChange={event => setSourceTitle(event.target.value)} /></label>
      <label className="block">Source type <select value={kind} onChange={event => setKind(event.target.value as Source["kind"])}><option value="document">Document text</option><option value="recording_transcript">Timestamped transcript excerpt</option></select></label>
      {kind === "recording_transcript" && <div><label>Start seconds <input type="number" min={0} max={1800} value={start} onChange={event => setStart(Number(event.target.value))} /></label><label>End seconds <input type="number" min={start} max={1800} value={end} onChange={event => setEnd(Number(event.target.value))} /></label></div>}
      <label className="block">Source content<textarea className="border rounded w-full" rows={5} maxLength={kind === "document" ? 60000 : 12000} value={text} onChange={event => setText(event.target.value)} /></label>
      <button className="workspace-button workspace-primary" disabled={!sourceTitle.trim() || !text.trim()} onClick={() => void act(async () => {
        await knowledgeRequest(base + "/sources", { title: sourceTitle, kind, text: kind === "document" ? text : "", segments: kind === "document" ? [] : [{ start_seconds: start, end_seconds: end, text }] });
        setText(""); setSourceTitle(""); await load();
      })}>Save source</button>
    </fieldset>
    <section className="space-y-3"><h3 className="text-lg font-semibold">Saved sources</h3>
      {data.sources.map(source => <details id={`source-${source.source_id}`} key={source.source_id} className="border rounded p-3">
        <summary>{source.title} · {source.kind}</summary>
        {source.origin?.upload_id && <p>Upload source · {source.origin.page_number ? `Page ${source.origin.page_number}` : source.origin.block_number ? `Paragraph block ${source.origin.block_number} (not a rendered page)` : source.origin.timestamp_seconds !== undefined ? `Frame sampled near ${source.origin.timestamp_seconds} seconds` : "Timestamped transcript"} · Unapproved ingestion observation</p>}
        {source.origin?.kind === "story" && <p>Proposed from <Link className="underline" href={`/projects/${projectId}/stories/${source.origin.story_id}`}>story {source.origin.story_id}</Link> · Snapshot digest {source.origin.story_digest}</p>}
        {source.kind === "document" ? <p className="whitespace-pre-wrap">{source.text}</p> : source.segments.map((segment, i) => <p key={i}>Segment {i} [{segment.start_seconds}–{segment.end_seconds}s]: {segment.text}</p>)}
        <button className="workspace-button" disabled={busy} onClick={() => void act(async () => {
          const result = await knowledgeRequest<{ claims: Claim[]; clarification_questions: string[] }>(base + `/sources/${source.source_id}/extract`, {});
          setClaims(items => [...items, ...result.claims]); setAnswers(items => ({ ...items, ...Object.fromEntries(result.clarification_questions.map(question => [question, ""])) }));
          setMessage("Proposals added to the editor. Review citations and statements before saving.");
        })}>Extract proposals with AI</button>
      </details>)}
    </section>
    </section><section id="knowledge-review" className="space-y-4"><h2 className="text-xl font-semibold">Review &amp; Clarify</h2><fieldset disabled={busy} className="border rounded p-4 space-y-3"><legend>Review knowledge snapshot</legend>
      <p>To revise approved knowledge, first select “Create successor” below. Include every claim that should remain current.</p>
      <label>Snapshot title <input className="border rounded p-2" value={title} maxLength={200} onChange={event => setTitle(event.target.value)} /></label>
      <p>Parent: {parent || "current approved version at save time"}</p>
      {claims.map((claim, i) => <div key={claim.claim_id} className="border rounded p-3 space-y-2">
        <p>{claim.claim_id}</p>
        <label className="block">Category <select value={claim.category} onChange={event => edit(i, { category: event.target.value as Claim["category"] })}>{["terminology", "role", "business_rule", "workflow", "exception", "unknown"].map(value => <option key={value}>{value}</option>)}</select></label>
        <label className="block">Information type <select value={claim.epistemic_status} onChange={event => edit(i, { epistemic_status: event.target.value as Claim["epistemic_status"] })}>{["expected", "observed", "inferred", "unknown"].map(value => <option key={value}>{value}</option>)}</select></label>
        <label className="block">Statement<textarea className="border rounded w-full" maxLength={1500} value={claim.statement} onChange={event => edit(i, { statement: event.target.value })} /></label>
        <label className="block">Source <select value={claim.source_id} onChange={event => edit(i, { source_id: event.target.value, segment_index: data.sources.find(source => source.source_id === event.target.value)?.kind === "recording_transcript" ? 0 : null })}><option value="">Select source</option>{data.sources.map(source => <option key={source.source_id} value={source.source_id}>{source.title}</option>)}</select></label>
        {data.sources.find(source => source.source_id === claim.source_id)?.kind === "recording_transcript" && <label className="block">Segment index <input type="number" min={0} value={claim.segment_index ?? 0} onChange={event => edit(i, { segment_index: Number(event.target.value) })} /></label>}
        <label className="block">Exact source quote<textarea className="border rounded w-full" maxLength={1200} value={claim.quote} onChange={event => edit(i, { quote: event.target.value })} /></label>
        <a href={`#source-${claim.source_id}`} className="underline">Review source</a>{" "}<button onClick={() => setClaims(items => items.filter((_, index) => index !== i))}>Remove claim from successor</button>
      </div>)}
      <button className="workspace-button" disabled={!data.sources.length || claims.length >= 100} onClick={() => setClaims(items => [...items, { claim_id: "K_" + crypto.randomUUID().replaceAll("-", ""), category: "business_rule", epistemic_status: "unknown", statement: "", source_id: data.sources[0].source_id, segment_index: data.sources[0].kind === "recording_transcript" ? 0 : null, quote: "" }])}>Add reviewed claim manually</button>
      {Object.entries(answers).map(([question, answer]) => <label className="block" key={question}>{question}<textarea className="border rounded w-full" maxLength={2000} value={answer} onChange={event => setAnswers(items => ({ ...items, [question]: event.target.value }))} /></label>)}
      <button className="workspace-button" disabled={!claims.length || claims.some(claim => !claim.statement.trim() || !claim.quote.trim())} onClick={() => void act(async () => {
        await knowledgeRequest(base + "/versions", { title, claims, parent_version_id: parent, clarification_answers: answers }); await load(); setMessage("Immutable draft saved. Review the saved snapshot before approval.");
      })}>Save new draft snapshot</button>
    </fieldset>
    <section className="space-y-3"><h2 className="text-xl font-semibold">Saved versions</h2>
      {data.versions.map(version => <details id={`knowledge-version-${version.version_id}`} className="border rounded p-3" key={version.version_id}><summary>{version.title} · {version.status}{version.version_id === data.active_version_id ? " · current" : ""} · {version.version_id}</summary>
        {version.claims.map(claim => <div id={`claim-${version.version_id}-${claim.claim_id}`} key={claim.claim_id} className="py-2"><p>{claim.epistemic_status} · {claim.category}: {claim.statement}</p><a className="underline" href={`#source-${claim.source_id}`}>{claim.quote} {claim.segment_index !== null ? ` (segment ${claim.segment_index})` : ""}</a></div>)}
        {Object.entries(version.clarification_answers).map(([question, answer]) => <p key={question}>{question}: {answer || "Unanswered"}</p>)}
        <p>Digest: {version.content_digest}</p>
        <button className="workspace-button" disabled={busy} onClick={() => { setParent(version.version_id); setTitle(version.title); setClaims(version.claims.map(claim => ({ ...claim }))); setAnswers({ ...version.clarification_answers }); setMessage("Snapshot copied into the editor; the saved version remains unchanged."); }}>Create successor</button>
        {canApprove && version.status === "draft" && <button className="workspace-button" disabled={busy} onClick={() => void act(async () => { await knowledgeRequest(base + `/versions/${version.version_id}/approve`, {}); await load(); setMessage("Knowledge approved. Affected story analyses and specifications require review before new generation or execution."); })}>Approve saved knowledge (project admin)</button>}
      </details>)}
    </section>
    </section><section id="approved-knowledge" className="space-y-3"><h2 className="text-xl font-semibold">Approved Knowledge</h2>
      {!data.active_version_id && <p>No approved knowledge yet. Review a saved snapshot before approval.</p>}
      {data.versions.filter(version=>version.status === "approved").map(version=><article className="border rounded p-3" key={version.version_id}><h3>{version.title} · {version.version_id===data.active_version_id?"Current approved":"Historical approved"}</h3><p>{version.claims.length} reviewed claims. Approved content remains immutable.</p><a className="underline" href={`#knowledge-version-${version.version_id}`}>Inspect version, source citations and correction controls</a></article>)}
    </section>
    {busy && <p role="status">Working…</p>}{error && <p role="alert">{error}</p>}{message && <p role="status">{message}</p>}
  </div>;
}
