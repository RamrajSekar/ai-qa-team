"use client";

import { useCallback, useEffect, useState } from "react";
import { CheckCircle2, FolderGit2, Github, RefreshCw, TriangleAlert } from "lucide-react";
import { apiFetch } from "@/utils/api";
import type { DiscoveredTest, RepositoryRecord, RepositorySource } from "@/types/repository";

type Props = {
  projectId: string;
  onboarding?: boolean;
  onContinue?: () => void;
  onSkip?: () => void;
};

export default function RepositoryManager({ projectId, onboarding = false, onContinue, onSkip }: Props) {
  const [repositories, setRepositories] = useState<RepositoryRecord[]>([]);
  const [selected, setSelected] = useState<RepositoryRecord | null>(null);
  const [tests, setTests] = useState<DiscoveredTest[]>([]);
  const [sourceType, setSourceType] = useState<RepositorySource>("GITHUB_PUBLIC");
  const [repositoryUrl, setRepositoryUrl] = useState("");
  const [localPath, setLocalPath] = useState("");
  const [branch, setBranch] = useState("main");
  const [localEnabled, setLocalEnabled] = useState(false);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadTests = useCallback(async (repository: RepositoryRecord) => {
    const response = await apiFetch(`/repositories/${repository.repository_id}/tests`);
    setTests(response.ok && Array.isArray(response.data) ? response.data : []);
  }, []);

  useEffect(() => {
    let active = true;
    async function initialLoad() {
      const [options, records] = await Promise.all([
        apiFetch("/repositories/options"),
        apiFetch(`/repositories?project_id=${encodeURIComponent(projectId)}`),
      ]);
      if (!active) return;
      setLocalEnabled(options.ok && options.data?.local_repository === true);
      const list = records.ok && Array.isArray(records.data) ? records.data : [];
      setRepositories(list);
      if (list.length) {
        setSelected(list[0]);
        await loadTests(list[0]);
      }
      if (active) setLoading(false);
    }
    initialLoad();
    return () => { active = false; };
  }, [projectId, loadTests]);

  async function connect() {
    setScanning(true);
    setError(null);
    const response = await apiFetch("/repositories", {
      method: "POST",
      body: JSON.stringify({
        project_id: projectId,
        source_type: sourceType,
        repository_url: sourceType === "GITHUB_PUBLIC" ? repositoryUrl : null,
        local_path: sourceType === "LOCAL" ? localPath : null,
        branch,
        framework: "auto",
      }),
    });
    if (!response.ok) {
      setError(response.data?.detail || "Repository connection failed. Check the repository and try again.");
    } else {
      const repository = response.data as RepositoryRecord;
      setSelected(repository);
      setRepositories((current) => [repository, ...current.filter((item) => item.repository_id !== repository.repository_id)]);
      await loadTests(repository);
    }
    setScanning(false);
  }

  async function rescan(repository: RepositoryRecord) {
    setScanning(true);
    setError(null);
    const response = await apiFetch(`/repositories/${repository.repository_id}/rescan`, { method: "POST" });
    if (response.ok) {
      const updated = response.data as RepositoryRecord;
      setSelected(updated);
      setRepositories((current) => current.map((item) => item.repository_id === updated.repository_id ? updated : item));
      await loadTests(updated);
    } else {
      setError(response.data?.detail || "Rescan failed. Try again.");
    }
    setScanning(false);
  }

  if (loading) return <p role="status" className="workspace-description">Loading repositories…</p>;

  return (
    <div className="repository-manager">
      {!selected || selected.scan_status === "failed" ? (
        <section className="repository-connect-card">
          <div className="repository-source-grid">
            <button type="button" className={sourceType === "GITHUB_PUBLIC" ? "is-selected" : ""} onClick={() => setSourceType("GITHUB_PUBLIC")}>
              <Github size={20} /><strong>GitHub Repository</strong><span>Public HTTPS repositories</span>
            </button>
            {localEnabled && <button type="button" className={sourceType === "LOCAL" ? "is-selected" : ""} onClick={() => setSourceType("LOCAL")}>
              <FolderGit2 size={20} /><strong>Local Repository</strong><span>Development backend only</span>
            </button>}
          </div>
          <label>{sourceType === "LOCAL" ? "Repository path" : "Repository URL"}
            <input value={sourceType === "LOCAL" ? localPath : repositoryUrl} onChange={(event) => sourceType === "LOCAL" ? setLocalPath(event.target.value) : setRepositoryUrl(event.target.value)} placeholder={sourceType === "LOCAL" ? "F:\\salesforce-robot-automation" : "https://github.com/user/repository"} />
          </label>
          {sourceType === "LOCAL" && <p className="repository-note">The path must be accessible to the machine running FastAPI. Cloud deployments cannot read your computer.</p>}
          <div className="repository-form-grid">
            <label>Branch<input value={branch} onChange={(event) => setBranch(event.target.value)} /></label>
            <label>Framework<input value="Auto Detect" disabled /></label>
          </div>
          {error && <p role="alert" className="repository-error">{error}</p>}
          {selected?.scan_status === "failed" && <p role="alert" className="repository-error"><TriangleAlert size={16} />{selected.scan_error}</p>}
          <div className="repository-actions">
            {onSkip && <button className="workspace-button" onClick={onSkip}>Skip for now</button>}
            {selected?.scan_status === "failed" && (
              <button className="workspace-button" onClick={() => rescan(selected)} disabled={scanning}>
                <RefreshCw size={15} />{scanning ? "Scanning…" : "Retry Scan"}
              </button>
            )}
            <button className="workspace-button workspace-primary" onClick={connect} disabled={scanning || (sourceType === "LOCAL" ? !localPath.trim() : !repositoryUrl.trim())}>
              {scanning ? <RefreshCw size={15} className="animate-spin" /> : <Github size={15} />}Connect & Scan
            </button>
          </div>
        </section>
      ) : (
        <section className="repository-result">
          <div className="repository-result-header"><CheckCircle2 size={22} /><div><strong>Repository Connected</strong><span>{selected.repository_url || selected.local_path}</span></div></div>
          <dl className="repository-summary">
            <div><dt>Source</dt><dd>{selected.provider === "github" ? "GitHub" : "Local development"}</dd></div>
            <div><dt>Framework</dt><dd>{selected.framework === "robot" ? "Robot Framework" : "Unsupported"}</dd></div>
            <div><dt>Branch</dt><dd>{selected.branch}</dd></div>
            <div><dt>Commit</dt><dd>{selected.source_commit_sha?.slice(0, 8) || "—"}</dd></div>
            <div><dt>Tests Discovered</dt><dd>{selected.test_count}</dd></div>
            <div><dt>Last Scan</dt><dd>{selected.last_scanned_at ? new Date(selected.last_scanned_at).toLocaleString() : "—"}</dd></div>
          </dl>
          {selected.scan_status === "unsupported" && <p className="repository-error"><TriangleAlert size={16} />{selected.scan_error}</p>}
          <div className="repository-tests"><h3>Discovered Tests</h3>
            {tests.length ? tests.map((test) => <div className="repository-test-row" key={test.test_id}><div><strong>{test.test_name}</strong><span>{test.relative_file_path}{test.line_number ? `:${test.line_number}` : ""}</span></div>{test.tags.length > 0 && <small>{test.tags.join(" · ")}</small>}</div>) : <p>No Robot Framework tests discovered.</p>}
          </div>
          {error && <p role="alert" className="repository-error">{error}</p>}
          <div className="repository-actions">
            <button className="workspace-button" onClick={() => rescan(selected)} disabled={scanning}><RefreshCw size={15} />{scanning ? "Scanning…" : "Rescan"}</button>
            {onContinue && <button className="workspace-button workspace-primary" onClick={onContinue}>Continue</button>}
          </div>
        </section>
      )}
      {!onboarding && repositories.length > 1 && <section className="workspace-panel"><div className="workspace-panel-header"><h2>Connected repositories</h2></div><div className="workspace-panel-body">{repositories.map((repository) => <button key={repository.repository_id} className="workspace-row" onClick={() => { setSelected(repository); loadTests(repository); }}><div><div className="workspace-row-title">{repository.repository_url || repository.local_path}</div><div className="workspace-row-subtitle">{repository.branch} · {repository.framework} · {repository.source_commit_sha?.slice(0, 8) || "Not scanned"}</div></div><span className="workspace-badge">{repository.scan_status}</span></button>)}</div></section>}
    </div>
  );
}
