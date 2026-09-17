"use client";

import { useState } from "react";
import { AlertCircle, CheckCircle2, Sparkles } from "lucide-react";
import { apiFetch } from "@/utils/api";
import type { BugInterpretResponse, IntentConstraint, IntentInput } from "@/types/test-intent";

function readableName(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function constraintText(constraint?: IntentConstraint | null) {
  if (!constraint) return null;
  if (constraint.type === "DATE_RANGE" && constraint.start && constraint.end) {
    const format = (value: string | number) => new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeZone: "UTC" }).format(new Date(`${value}T00:00:00Z`));
    return `${format(constraint.start)} – ${format(constraint.end)}`;
  }
  return constraint.description || constraint.value || [constraint.start, constraint.end].filter(Boolean).join(" – ");
}

function InputCard({ input }: { input: IntentInput }) {
  return <article className={`intent-input intent-input-${input.constraint_type.toLowerCase()}`}>
    <header><strong>{readableName(input.name)}</strong><span className="workspace-badge">{input.constraint_type}</span></header>
    <dl>
      <div><dt>{input.constraint_type === "CONSTRAINED" ? "Source constraint" : "Value"}</dt><dd>{input.raw_value || "Not supplied"}</dd></div>
      {input.constraint && <div><dt>{input.constraint.type === "DATE_RANGE" ? "Allowed range" : "Constraint"}</dt><dd>{String(constraintText(input.constraint) || "Specified condition")}</dd></div>}
      <div><dt>Meaning</dt><dd>{input.constraint_type === "EXACT" ? "Must remain this value" : input.constraint_type === "CONSTRAINED" ? "Resolve later within this condition" : "Relevant value was not supplied"}</dd></div>
      {input.confidence && <div><dt>Confidence</dt><dd>{input.confidence}</dd></div>}
    </dl>
  </article>;
}

export default function BugInterpreter({ projectId }: { projectId: string }) {
  const [bugText, setBugText] = useState("");
  const [result, setResult] = useState<BugInterpretResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function interpret() {
    if (!bugText.trim()) { setError("Paste a bug report or steps to reproduce first."); return; }
    setLoading(true); setError(null);
    const response = await apiFetch(`/projects/${encodeURIComponent(projectId)}/bugs/interpret`, {
      method: "POST", body: JSON.stringify({ bug_text: bugText }),
    });
    if (response.ok) setResult(response.data as BugInterpretResponse);
    else {
      const detail = response.data?.detail;
      setError(detail?.message || (typeof detail === "string" ? detail : "The bug could not be interpreted. Try again."));
    }
    setLoading(false);
  }

  const intent = result?.test_intent;
  return <div className="bug-interpreter">
    <section className="bug-input-card">
      <label htmlFor="bug-text">Paste a bug report or Steps to Reproduce</label>
      <textarea id="bug-text" rows={11} value={bugText} onChange={(event) => setBugText(event.target.value)} placeholder="1. Login to the QA environment&#10;2. Open…&#10;3. Observe…" />
      <div className="bug-input-footer"><p>The report is interpreted as untrusted source text. No automation is selected or run.</p>
        <button className="workspace-button workspace-primary" onClick={interpret} disabled={loading}>{loading ? "Interpreting…" : result ? "Interpret Again" : "Interpret Bug"}<Sparkles size={15} /></button>
      </div>
      {error && <div className="repository-error" role="alert"><AlertCircle size={16} />{error}</div>}
    </section>

    {intent && <div className="intent-review" aria-live="polite">
      <div className="intent-review-heading"><div><p className="workspace-eyebrow">Interpretation review</p><h2>{intent.title}</h2><p>{intent.description}</p></div><span className="intent-confidence"><CheckCircle2 size={15} />{intent.confidence} confidence</span></div>
      <section className="intent-summary-grid">
        <div><h3>Environment</h3><p>{intent.environment || "Not specified"}</p></div>
        <div><h3>Preconditions</h3>{intent.preconditions.length ? <ul>{intent.preconditions.map((item) => <li key={item}>{item}</li>)}</ul> : <p>None explicitly supplied</p>}</div>
      </section>
      <section className="intent-section"><h3>Workflow</h3><ol className="intent-workflow">{intent.workflow_steps.map((step) => <li key={step.step_number}><span>{step.step_number}</span><div><strong>{step.action}{step.target ? ` · ${step.target}` : ""}</strong><p>{step.details}</p><small>Source: {step.raw_text}</small></div></li>)}</ol></section>
      <section className="intent-section"><h3>Inputs</h3>{intent.inputs.length ? <div className="intent-input-grid">{intent.inputs.map((input) => <InputCard input={input} key={input.name} />)}</div> : <p className="workspace-description">No explicit inputs identified.</p>}</section>
      <section className="intent-outcomes">
        <div><h3>Expected Result</h3><p>{intent.expected_result || "Not explicitly provided"}</p></div>
        <div><h3>Actual Result</h3><p>{intent.actual_result || "Not explicitly provided"}</p></div>
        <div><h3>Reported Behavior</h3><p>{intent.reported_behavior || "Not explicitly provided"}</p></div>
      </section>
      <section className="intent-section"><h3>Ambiguities</h3>{intent.ambiguities.length ? <div className="intent-ambiguities">{intent.ambiguities.map((item, index) => <div key={`${item.field}-${index}`}><span className="workspace-badge">{item.severity}</span><p><strong>{readableName(item.field)}:</strong> {item.description}</p></div>)}</div> : <p className="workspace-description">No meaningful ambiguities identified.</p>}</section>
      <footer className="intent-metadata">Schema TestIntentV{result.interpretation_metadata.schema_version} · Prompt {result.interpretation_metadata.prompt_key} / {result.interpretation_metadata.prompt_version} · {result.interpretation_metadata.prompt_source.replaceAll("_", " ")}</footer>
    </div>}
  </div>;
}
