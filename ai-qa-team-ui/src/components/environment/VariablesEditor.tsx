"use client";

import { useState } from "react";
import { Trash } from "lucide-react";

export interface VariablesMap {
  [key: string]: string;
}

export default function VariablesEditor({
  variables,
  setVariables,
}: {
  variables: VariablesMap;
  setVariables: React.Dispatch<React.SetStateAction<VariablesMap>>;   // ✅ FIXED
}) {
  const [error, setError] = useState("");

  function addVariable() {
    setVariables((prev) => {
      const updated = { ...prev };
      let newKey = "NEW_VAR";
      let count = 1;

      while (updated[newKey]) {
        newKey = `NEW_VAR_${count++}`;
      }

      updated[newKey] = "";
      return updated;
    });
  }

  function updateKey(oldKey: string, newKey: string) {
    if (!newKey.trim()) {
      setError("Variable key cannot be empty");
      return;
    }

    if (oldKey !== newKey && variables[newKey]) {
      setError("Duplicate variable key");
      return;
    }

    setError("");

    setVariables((prev) => {
      const updated = { ...prev };
      const value = updated[oldKey];
      delete updated[oldKey];
      updated[newKey] = value;
      return updated;
    });
  }

  function updateValue(key: string, value: string) {
    setVariables((prev) => ({
      ...prev,
      [key]: value,
    }));
  }

  function removeVariable(key: string) {
    setVariables((prev) => {
      const updated = { ...prev };
      delete updated[key];
      return updated;
    });
  }

  return (
    <div className="space-y-4">
      <button
        onClick={addVariable}
        className="bg-purple-600 text-white px-3 py-1 rounded text-sm"
      >
        + Add Variable
      </button>

      {error && <p className="text-sm text-red-500 font-medium">{error}</p>}

      {Object.entries(variables).length === 0 && (
        <p className="text-sm text-gray-500">No variables added yet.</p>
      )}

      {Object.entries(variables).map(([key, value]) => (
        <div
          key={key}
          className="flex items-center gap-4 border rounded p-4 bg-gray-50"
        >
          <input
            className="border p-2 rounded w-1/3"
            value={key}
            onChange={(e) => updateKey(key, e.target.value)}
            placeholder="KEY"
          />

          <input
            className="border p-2 rounded w-1/3"
            value={value}
            onChange={(e) => updateValue(key, e.target.value)}
            placeholder="value"
          />

          <button
            onClick={() => removeVariable(key)}
            className="text-red-500 hover:text-red-700"
          >
            <Trash size={18} />
          </button>
        </div>
      ))}
    </div>
  );
}
