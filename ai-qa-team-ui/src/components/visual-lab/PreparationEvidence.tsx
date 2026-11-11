import type { PreparationDiagnostics } from "@/types/visual-batch.generated";

export default function PreparationEvidence({ diagnostics }: { diagnostics?: PreparationDiagnostics | null }) {
  if (!diagnostics) return null;
  return <details className="rounded-lg border p-3 text-sm">
    <summary>Container preparation — {diagnostics.stage.replaceAll("_", " ")}</summary>
    {diagnostics.error_stage && <p>Failed stage: {diagnostics.error_stage.replaceAll("_", " ")}</p>}
    {diagnostics.reason && <p>Reason: {diagnostics.reason.replaceAll("_", " ")}</p>}
    <dl>{Object.entries(diagnostics.timings_ms ?? {}).map(([stage, duration]) => <div key={stage}>
      <dt className="inline">{stage.replaceAll("_", " ")}: </dt><dd className="inline">{duration} ms</dd>
    </div>)}</dl>
    <ol aria-label="Container preparation timeline">{(diagnostics.events ?? []).map((event, index) => <li key={index}>
      {new Date(event.at).toLocaleString()} — {event.stage.replaceAll("_", " ")} {event.phase}
    </li>)}</ol>
    <p>Preparation and browser startup are separate stages. No browser execution is inferred from preparation alone.</p>
  </details>;
}
