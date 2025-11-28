"use client";

import { Credentials } from "@/types/environment";
import { Plus, Trash } from "lucide-react";

interface Props {
  items: Credentials[];
  onChange: (items: Credentials[]) => void;
}

export default function CredentialFields({ items, onChange }: Props) {
  function addCred() {
    onChange([
      ...items,
      { role: "qa", username: "", password: "", notes: "" },
    ]);
  }

  function removeCred(idx: number) {
    onChange(items.filter((_, i) => i !== idx));
  }

  return (
    <div className="space-y-3">
      {items.map((c, idx) => (
        <div key={idx} className="border p-3 rounded-md">
          {/* REMOVE BUTTON */}
          <div className="flex justify-between items-center">
            <strong>{c.role}</strong>
            <button
              className="text-red-500"
              onClick={() => removeCred(idx)}
            >
              <Trash size={16} />
            </button>
          </div>

          {/* USERNAME + PASSWORD */}
          <div className="grid grid-cols-2 gap-2 mt-2">
            <input
              value={c.username}
              onChange={(e) => {
                const arr = [...items];
                arr[idx].username = e.target.value;
                onChange(arr);
              }}
              className="input"
              placeholder="Username"
            />

            <input
              value={c.password}
              onChange={(e) => {
                const arr = [...items];
                arr[idx].password = e.target.value;
                onChange(arr);
              }}
              className="input"
              placeholder="Password"
            />
          </div>

          <textarea
            value={c.notes || ""}
            onChange={(e) => {
              const arr = [...items];
              arr[idx].notes = e.target.value;
              onChange(arr);
            }}
            className="input mt-2"
            placeholder="Notes"
          />
        </div>
      ))}

      <button
        onClick={addCred}
        className="bg-gray-200 px-3 py-1 rounded-md flex items-center gap-2"
      >
        <Plus size={16} /> Add Credential
      </button>
    </div>
  );
}
