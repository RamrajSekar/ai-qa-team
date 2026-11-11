"use client";

export interface StepValue { source: "literal" | "credential" | "parameter"; text?: string; field?: "username" | "password"; name?: string }
export interface AuthoredStep {
  action: "navigate" | "click" | "type" | "assert_text" | "reusable";
  path?: string; target?: string; value?: StepValue; expected?: string;
  workflow_version_id?: string; inputs?: Record<string, StepValue>;
}
export interface WorkflowVersion {
  workflow_id: string; version_id: string; title: string; status: "draft" | "approved";
  steps: AuthoredStep[]; parameters: string[];
}

function defaultStep(action: AuthoredStep["action"]): AuthoredStep {
  if (action === "navigate") return { action, path: "/" };
  if (action === "click") return { action, target: "" };
  if (action === "type") return { action, target: "", value: { source: "literal", text: "" } };
  if (action === "assert_text") return { action, expected: "" };
  return { action, workflow_version_id: "", inputs: {} };
}

function InputEditor({ value, onChange, parameters }: { value: StepValue; onChange: (value: StepValue) => void; parameters: boolean }) {
  return <div className="flex flex-wrap gap-2">
    <label>Input source <select value={value.source} onChange={event => {
      const source = event.target.value as StepValue["source"];
      onChange(source === "literal" ? { source, text: "" } : source === "parameter" ? { source, name: "" } : { source, field: "username" });
    }}><option value="literal">Public text</option><option value="credential">Environment credential</option>{parameters && <option value="parameter">Reusable input</option>}</select></label>
    {value.source === "literal" && <label>Public value <input className="workspace-input" value={value.text || ""} onChange={event => onChange({ source: "literal", text: event.target.value })} /></label>}
    {value.source === "parameter" && <label>Input name <input className="workspace-input" value={value.name || ""} onChange={event => onChange({ source: "parameter", name: event.target.value })} /></label>}
    {value.source === "credential" && <label>Credential field <select value={value.field} onChange={event => onChange({ source: "credential", field: event.target.value as "username" | "password" })}><option value="username">Selected role’s username</option><option value="password">Selected role’s password</option></select></label>}
  </div>;
}

export default function VisualStepEditor({ steps, onChange, workflows, reusable }: {
  steps: AuthoredStep[]; onChange: (steps: AuthoredStep[]) => void; workflows: WorkflowVersion[]; reusable: boolean;
}) {
  function update(index: number, step: AuthoredStep) { onChange(steps.map((row, position) => position === index ? step : row)); }
  return <div className="space-y-3">
    <p className="text-sm">Describe visible targets in plain language. Use credential references for usernames/passwords. Public input values are stored with the specification.</p>
    {steps.map((step, index) => <div className="border rounded p-3 space-y-2" key={index}>
      <div className="flex gap-3"><label>Step {index + 1} <select value={step.action} onChange={event => update(index, defaultStep(event.target.value as AuthoredStep["action"]))}>
        <option value="navigate">Navigate within environment</option><option value="click">Click visible target</option><option value="type">Enter value</option><option value="assert_text">Assert exact visible text</option>{!reusable && <option value="reusable">Use reusable workflow</option>}
      </select></label><button type="button" onClick={() => onChange(steps.filter((_, position) => position !== index))}>Remove step {index + 1}</button>
      <button type="button" disabled={index === 0} onClick={() => { const reordered = [...steps]; [reordered[index - 1], reordered[index]] = [reordered[index], reordered[index - 1]]; onChange(reordered); }}>Move up</button></div>
      {step.action === "navigate" && <label>Relative path <input className="workspace-input" value={step.path || ""} onChange={event => update(index, { ...step, path: event.target.value })} /></label>}
      {(step.action === "click" || step.action === "type") && <label>Visible target <input className="workspace-input" value={step.target || ""} onChange={event => update(index, { ...step, target: event.target.value })} /></label>}
      {step.action === "type" && <InputEditor value={step.value || { source: "literal", text: "" }} parameters={reusable} onChange={value => update(index, { ...step, value })} />}
      {step.action === "assert_text" && <label>Expected visible text <input className="workspace-input" value={step.expected || ""} onChange={event => update(index, { ...step, expected: event.target.value })} /></label>}
      {step.action === "reusable" && <>
        <label>Approved workflow version <select value={step.workflow_version_id || ""} onChange={event => update(index, { action: "reusable", workflow_version_id: event.target.value, inputs: {} })}>
          <option value="">Choose a version</option>{workflows.filter(row => row.status === "approved").map(row => <option key={row.version_id} value={row.version_id}>{row.title} · {row.version_id.slice(0, 8)}</option>)}
        </select></label>
        {workflows.find(row => row.version_id === step.workflow_version_id)?.parameters.map(name => <div key={name}><p>{name}</p>
          <InputEditor parameters={false} value={step.inputs?.[name] || { source: "literal", text: "" }} onChange={value => update(index, { ...step, inputs: { ...step.inputs, [name]: value } })} />
          {!step.inputs?.[name] && <button type="button" onClick={() => update(index, { ...step, inputs: { ...step.inputs, [name]: { source: "literal", text: "" } } })}>Use empty public value</button>}
        </div>)}
      </>}
    </div>)}
    <button type="button" className="workspace-button" disabled={steps.length >= (reusable ? 20 : 40)} onClick={() => onChange([...steps, defaultStep("click")])}>Add step</button>
  </div>;
}
