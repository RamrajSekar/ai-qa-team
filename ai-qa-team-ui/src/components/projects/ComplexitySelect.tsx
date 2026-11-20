"use client";

export type GenerationComplexity = "basic" | "medium" | "advanced";

export default function ComplexitySelect({ value, onChange, disabled = false }: {
  value: GenerationComplexity;
  onChange: (value: GenerationComplexity) => void;
  disabled?: boolean;
}) {
  return <label className="block">Complexity
    <select className="border rounded p-2 ml-3" value={value} disabled={disabled}
      onChange={event => onChange(event.target.value as GenerationComplexity)}>
      <option value="basic">Basic</option>
      <option value="medium">Medium</option>
      <option value="advanced">Advanced</option>
    </select>
  </label>;
}
