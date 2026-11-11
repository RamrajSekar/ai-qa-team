"use client";

import { useState } from "react";
import { Eye, EyeOff, Trash } from "lucide-react";

import type { EnvironmentCredentials as Credential } from "@/types/environment";

export default function CredentialFields({
  credentials,
  setCredentials,
}: {
  credentials: Credential[];
  setCredentials: (x: Credential[]) => void;
}) {
  const [visibleIndex, setVisibleIndex] = useState<number | null>(null);

  function addCredential() {
    setCredentials([
      ...credentials,
      { role: "", username: "", password: "", notes: "" },
    ]);
  }

  function update(i: number, field: "role" | "username" | "password" | "notes", value: string) {
    const updated = [...credentials];
    updated[i] = { ...updated[i], [field]: value };
    setCredentials(updated);
  }

  function remove(i: number) {
    setCredentials(credentials.filter((_, idx) => idx !== i));
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-600">Passwords are encrypted when saved and are never returned. Leave a saved password blank to keep it. Remove a credential row to revoke it. Keep secrets out of notes and variables.</p>
      <button
        type="button"
        onClick={addCredential}
        className="bg-purple-600 text-white px-3 py-1 rounded text-sm"
      >
        + Add Credential
      </button>

      {credentials.length === 0 && (
        <p className="text-sm text-gray-500">No credentials added yet.</p>
      )}

      {credentials.map((cred, i) => (
        <div key={i} className="border rounded p-4 bg-gray-50 space-y-4 relative">
          {/* DELETE BUTTON */}
          <button
            type="button"
            aria-label={`Remove credential ${i + 1}`}
            onClick={() => remove(i)}
            className="absolute right-4 top-4 text-red-500 hover:text-red-700"
          >
            <Trash size={18} />
          </button>

          {/* ROLE / USERNAME / PASSWORD */}
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label htmlFor={`credential-role-${i}`} className="text-sm font-medium">Application role</label>
              <input
                className="border p-2 rounded w-full mt-1"
                id={`credential-role-${i}`}
                value={cred.role}
                onChange={(e) => update(i, "role", e.target.value)}
                placeholder="e.g. admin"
              />
            </div>

            <div>
              <label htmlFor={`credential-username-${i}`} className="text-sm font-medium">Username</label>
              <input
                className="border p-2 rounded w-full mt-1"
                id={`credential-username-${i}`}
                autoComplete="off"
                value={cred.username}
                onChange={(e) => update(i, "username", e.target.value)}
                placeholder="username"
              />
            </div>

            <div>
              <label htmlFor={`credential-password-${i}`} className="text-sm font-medium flex items-center justify-between">
                Password
                <button
                  aria-label={`Toggle password visibility ${i + 1}`}
                  type="button"
                  onClick={() =>
                    setVisibleIndex(visibleIndex === i ? null : i)
                  }
                >
                  {visibleIndex === i ? (
                    <EyeOff size={16} />
                  ) : (
                    <Eye size={16} />
                  )}
                </button>
              </label>

              <input
                className="border p-2 rounded w-full mt-1"
                type={visibleIndex === i ? "text" : "password"}
                id={`credential-password-${i}`}
                autoComplete="new-password"
                value={cred.password}
                onChange={(e) => update(i, "password", e.target.value)}
                placeholder={cred.password_configured ? "Saved — leave blank to keep" : "Enter password"}
              />
            </div>
          </div>

          {/* NOTES */}
          <div>
            <label className="text-sm font-medium">Notes</label>
            <textarea
              className="border p-2 rounded w-full mt-1"
              rows={2}
              value={cred.notes || ""}
              onChange={(e) => update(i, "notes", e.target.value)}
              placeholder="Non-secret notes only"
            />
          </div>
        </div>
      ))}
    </div>
  );
}
