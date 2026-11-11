import type { CaseStartupDiagnostics } from "@/types/visual-batch.generated";

export default function StartupEvidence({ stage, reason, timings, diagnostics }: {
  stage?: string | null; reason?: string | null;
  timings?: Record<string, number>; diagnostics?: CaseStartupDiagnostics | null;
}) {
  if (!stage && !diagnostics && !Object.keys(timings ?? {}).length) return <p className="text-sm">Startup details were not recorded or are unavailable for this check.</p>;
  return <details className="rounded-lg border p-3 text-sm">
    <summary className="cursor-pointer font-medium">Startup diagnostics{stage ? ` — ${stage}` : ""}</summary>
    {reason && <p className="mt-2">Startup reason: {reason}</p>}
    {diagnostics && <dl className="grid grid-cols-2 gap-2 mt-3">
      <dt>ChromeDriver version</dt><dd>{diagnostics.driver_version ?? "Not available"}</dd>
      <dt>Driver before cleanup</dt><dd>{diagnostics.driver_state ?? "unknown"}{diagnostics.driver_exit_code != null ? ` (exit ${diagnostics.driver_exit_code})` : ""}</dd>
      <dt>Browser before cleanup</dt><dd>{diagnostics.browser_state ?? "unavailable"}</dd>
      <dt>DevTools port file</dt><dd>{diagnostics.devtools_port_file ?? "unavailable"}</dd>
      <dt>Session created</dt><dd>{diagnostics.session_created === true ? "Yes" : diagnostics.session_created === false ? "No" : "Unknown"}</dd>
      <dt>Cleanup observation</dt><dd>{diagnostics.cleanup ?? "unverified"}</dd>
      <dt>Browser after cleanup</dt><dd>{diagnostics.cleanup_browser_state ?? "unavailable"}</dd>
      <dt>Driver cleanup exit code</dt><dd>{diagnostics.cleanup_driver_exit_code ?? "Not available"}</dd>
      <dt>Native error categories</dt><dd>{diagnostics.native_errors?.join(", ") || "None captured (does not establish absence of errors)"}</dd>
    </dl>}
    {!!Object.keys(timings ?? {}).length && <ul aria-label="Startup stage timings" className="mt-3 space-y-1">
      {Object.entries(timings ?? {}).map(([name, ms]) => <li key={name}>{name}: {ms} ms</li>)}
    </ul>}
    <p className="mt-3">Stage timings describe observed transitions. Cleanup-induced termination is not proof of a browser crash. Browser observations may be unavailable.</p>
  </details>;
}
