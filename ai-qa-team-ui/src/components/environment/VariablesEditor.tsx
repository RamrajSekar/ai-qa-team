"use client";

import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";

interface Props {
  variables: Record<string, any>;
  setVariables: (v: Record<string, any>) => void;
}

export default function VariablesEditor({ variables, setVariables }: Props) {
  const [newKey, setNewKey] = useState("");
  const [newValue, setNewValue] = useState("");

  function addVariable() {
    if (!newKey) return;
    setVariables({ ...variables, [newKey]: newValue });
    setNewKey("");
    setNewValue("");
  }

  function removeVariable(key: string) {
    const copy = { ...variables };
    delete copy[key];
    setVariables(copy);
  }

  return (
    <div className="border p-4 rounded-lg bg-gray-50 space-y-3">
      <h3 className="font-medium">Variables</h3>

      {/* Add field */}
      <div className="grid grid-cols-3 gap-2">
        <input
          value={newKey}
          onChange={(e) => setNewKey(e.target.value)}
          className="border rounded-md p-2"
          placeholder="Key"
        />
        <input
          value={newValue}
          onChange={(e) => setNewValue(e.target.value)}
          className="border rounded-md p-2"
          placeholder="Value"
        />
        <button
          onClick={addVariable}
          className="bg-purple-600 hover:bg-purple-700 text-white rounded-md px-3"
        >
          <Plus size={16} />
        </button>
      </div>

      {/* Existing variables */}
      {Object.keys(variables).length === 0 && (
        <p className="text-xs text-gray-500">No variables added.</p>
      )}

      {Object.entries(variables).map(([key, value]) => (
        <div
          key={key}
          className="flex items-center justify-between border rounded-md bg-white p-2"
        >
          <span className="font-mono text-sm">{key}</span>
          <div className="flex items-center gap-3">
            <span className="font-mono text-xs text-gray-600">{String(value)}</span>
            <button
              onClick={() => removeVariable(key)}
              className="text-red-500 hover:text-red-700"
            >
              <Trash2 size={16} />
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
