"use client";

import { useState } from "react";
import { Eye, EyeOff, Plus, Trash2 } from "lucide-react";

export interface Credential {
  role: string;
  username: string;
  password: string;
  notes?: string;
}

interface Props {
  credentials: Credential[];
  setCredentials: (c: Credential[]) => void;
}

export default function CredentialFields({ credentials, setCredentials }: Props) {
  const [showPasswordIndex, setShowPasswordIndex] = useState<number | null>(null);

  function addCredential() {
    setCredentials([
      ...credentials,
      { role: "", username: "", password: "", notes: "" },
    ]);
  }

  function removeCredential(i: number) {
    setCredentials(credentials.filter((_, idx) => idx !== i));
  }

  function updateField<T extends keyof Credential>(
    i: number,
    field: T,
    value: Credential[T]
  ) {
    const updated = [...credentials];
    updated[i] = { ...updated[i], [field]: value };
    setCredentials(updated);
  }

  return (
    <div className="space-y-3 border p-4 rounded-lg bg-gray-50">
      <div className="flex justify-between items-center">
        <h3 className="font-medium">Credentials</h3>
        <button
          type="button"
          onClick={addCredential}
          className="flex items-center gap-1 text-sm bg-purple-600 hover:bg-purple-700 text-white px-2 py-1 rounded"
        >
          <Plus size={16} /> Add
        </button>
      </div>

      {credentials.length === 0 && (
        <p className="text-xs text-gray-500">No credentials added.</p>
      )}

      {credentials.map((c, i) => (
        <div
          key={i}
          className="border rounded-lg p-3 bg-white shadow-sm relative"
        >
          {/* Remove button */}
          <button
            type="button"
            onClick={() => removeCredential(i)}
            className="absolute top-2 right-2 text-red-500 hover:text-red-700"
          >
            <Trash2 size={16} />
          </button>

          <div className="grid grid-cols-2 gap-3 mt-3">
            <div>
              <label className="text-xs font-medium">Role</label>
              <input
                className="border rounded-md w-full p-2 mt-1"
                placeholder="admin, qa, customer"
                value={c.role}
                onChange={(e) => updateField(i, "role", e.target.value)}
              />
            </div>

            <div>
              <label className="text-xs font-medium">Username</label>
              <input
                className="border rounded-md w-full p-2 mt-1"
                value={c.username}
                onChange={(e) => updateField(i, "username", e.target.value)}
              />
            </div>

            <div className="col-span-2">
              <label className="text-xs font-medium flex items-center justify-between">
                Password
                <button
                  type="button"
                  onClick={() =>
                    setShowPasswordIndex(showPasswordIndex === i ? null : i)
                  }
                  className="text-gray-600 hover:text-gray-800"
                >
                  {showPasswordIndex === i ? (
                    <EyeOff size={14} />
                  ) : (
                    <Eye size={14} />
                  )}
                </button>
              </label>

              <input
                className="border rounded-md w-full p-2 mt-1"
                type={showPasswordIndex === i ? "text" : "password"}
                value={c.password}
                onChange={(e) => updateField(i, "password", e.target.value)}
              />
            </div>

            <div className="col-span-2">
              <label className="text-xs font-medium">Notes (optional)</label>
              <textarea
                className="border rounded-md w-full p-2 mt-1"
                placeholder="Any additional notes..."
                value={c.notes}
                rows={2}
                onChange={(e) => updateField(i, "notes", e.target.value)}
              />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
