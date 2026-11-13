"use client";
import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { WorkspaceDialog } from "@/components/ui/workspace-dialog";
import { apiFetch } from "@/utils/api";

export default function CreateManualExecution({ projectId, cases, onClose }: {
  projectId: string; cases: { testcase_id: string; version_id: string; title: string }[]; onClose: () => void;
}) {
  const router = useRouter();
  const [title, setTitle] = useState(""); const [release, setRelease] = useState("");
  const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  const key = useRef<{ fingerprint: string; key: string } | null>(null);
  async function create(event: React.FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    const content = { title: title.trim(), release_cycle: release.trim(), cases: cases.map(({ testcase_id, version_id }) => ({ testcase_id, version_id })) };
    const fingerprint = JSON.stringify(content);
    if (key.current?.fingerprint !== fingerprint) key.current = { fingerprint, key: crypto.randomUUID().replaceAll("-", "") };
    try {
      const response = await apiFetch(`/projects/${encodeURIComponent(projectId)}/test-results/executions`, { method: "POST", body: JSON.stringify({ ...content, idempotency_key: key.current.key }), signal: AbortSignal.timeout(30000) });
      if (!response.ok) throw new Error(typeof response.data?.detail === "string" ? response.data.detail : "Execution creation was not confirmed. Retry unchanged content to recover the same execution.");
      router.push(`/projects/${encodeURIComponent(projectId)}/test-execution?execution=${encodeURIComponent(response.data.execution_id)}`);
      onClose();
    } catch (failure) { setError(failure instanceof Error ? failure.message : "Could not create a manual execution."); }
    finally { setBusy(false); }
  }
  return <WorkspaceDialog open title="Create manual test execution" onClose={onClose} busy={busy} className="workspace-dialog-wide">
    <form className="design-page manual-results" onSubmit={event => void create(event)}><header><p className="workspace-eyebrow">Manual testing</p><h2 className="text-xl font-semibold">Create Test Execution</h2><p>Pin up to 10 current approved cases. This does not launch a browser.</p></header>
      <label>Execution title<input required maxLength={240} value={title} disabled={busy} onChange={event => setTitle(event.target.value)} /></label>
      <label>Release / Cycle details<textarea required rows={4} maxLength={2000} value={release} disabled={busy} onChange={event => setRelease(event.target.value)} placeholder="Release, sprint, build and testing context. No credentials or personal data." /></label>
      <p>Mode: <strong>Manual</strong></p><ul>{cases.map(item => <li key={item.testcase_id}>{item.title}</li>)}</ul>
      {error && <p role="alert">{error}</p>}<div className="design-row-actions"><button type="button" className="workspace-button" disabled={busy} onClick={onClose}>Cancel</button><button className="workspace-button workspace-primary" disabled={busy || !title.trim() || !release.trim()}>{busy ? "Creating…" : "Create manual execution"}</button></div>
    </form>
  </WorkspaceDialog>;
}
