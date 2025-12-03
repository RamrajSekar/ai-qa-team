// src/app/projects/[project_id]/environments/NewEnvironmentModal.tsx
"use client";

import { useState } from "react";
import { X, Plus, Trash } from "lucide-react";
import { apiFetch } from "@/utils/api";
import type { Environment, Credentials } from "@/types/environment";

interface NewEnvironmentModalProps {
  open: boolean;
  onClose: () => void;
  projectId: string;
  refresh: () => Promise<void>;
}

export default function NewEnvironmentModal({
  open,
  onClose,
  projectId,
  refresh,
}: NewEnvironmentModalProps) {
  const [envType, setEnvType] = useState<Environment["env_type"]>("qa");
  const [baseUrl, setBaseUrl] = useState("");
  const [apiBaseUrl, setApiBaseUrl] = useState("");
  const [authType, setAuthType] = useState<Environment["auth_type"]>("none");
  const [authToken, setAuthToken] = useState("");

  const [defaultBrowser, setDefaultBrowser] =
    useState<Environment["default_browser"]>("chromium");
  const [defaultHeaded, setDefaultHeaded] = useState(false);
  const [timeoutMs, setTimeoutMs] = useState(10000);

  const [credentials, setCredentials] = useState<Credentials[]>([]);
  const [variables, setVariables] = useState<[string, string][]>([]);

  const [saving, setSaving] = useState(false);

  if (!open) return null;

  async function save() {
    setSaving(true);

    const payload = {
      project_id: projectId,
      env_id: "", // backend can generate or you can add a small input later
      env_type: envType,
      base_url: baseUrl,
      api_base_url: apiBaseUrl || null,
      auth_type: authType,
      auth_token: authType !== "none" ? authToken : null,
      credentials,
      default_browser: defaultBrowser,
      default_headed: defaultHeaded,
      default_timeout_ms: timeoutMs,
      variables: Object.fromEntries(
        variables.filter(([k]) => k.trim() !== "")
      ),
    };

    const res = await apiFetch(
      `${process.env.NEXT_PUBLIC_API_URL}/environments`,
      {
        method: "POST",
        body: JSON.stringify(payload),
      }
    );

    setSaving(false);

    if (res.ok) {
      await refresh();
      onClose();
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center">
      <div className="bg-white w-full max-w-3xl rounded-lg shadow-lg p-6 overflow-y-auto max-h-[90vh]">
        {/* HEADER */}
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">New Environment</h2>
          <button onClick={onClose}>
            <X size={22} />
          </button>
        </div>

        {/* BASIC FIELDS */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium">Environment Type</label>
            <select
              value={envType}
              onChange={(e) =>
                setEnvType(e.target.value as Environment["env_type"])
              }
              className="input"
            >
              <option value="local">Local</option>
              <option value="dev">Dev</option>
              <option value="qa">QA</option>
              <option value="staging">Staging</option>
              <option value="prod">Prod</option>
            </select>
          </div>

          <div>
            <label className="text-sm font-medium">Base URL</label>
            <input
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              className="input"
              placeholder="https://app.example.com"
            />
          </div>

          <div>
            <label className="text-sm font-medium">API Base URL</label>
            <input
              value={apiBaseUrl}
              onChange={(e) => setApiBaseUrl(e.target.value)}
              className="input"
              placeholder="https://api.example.com"
            />
          </div>

          <div>
            <label className="text-sm font-medium">Auth Type</label>
            <select
              value={authType}
              onChange={(e) =>
                setAuthType(e.target.value as Environment["auth_type"])
              }
              className="input"
            >
              <option value="none">None</option>
              <option value="basic">Basic Auth</option>
              <option value="bearer">Bearer Token</option>
            </select>
          </div>

          {authType !== "none" && (
            <div className="col-span-2">
              <label className="text-sm font-medium">Auth Token</label>
              <input
                value={authToken}
                onChange={(e) => setAuthToken(e.target.value)}
                className="input"
                placeholder="Token or API Key"
              />
            </div>
          )}

          <div>
            <label className="text-sm font-medium">Default Browser</label>
            <select
              value={defaultBrowser}
              onChange={(e) =>
                setDefaultBrowser(
                  e.target.value as Environment["default_browser"]
                )
              }
              className="input"
            >
              <option value="chromium">Chromium</option>
              <option value="firefox">Firefox</option>
              <option value="webkit">Webkit</option>
            </select>
          </div>

          <div className="flex items-center gap-2 mt-6">
            <input
              type="checkbox"
              checked={defaultHeaded}
              onChange={(e) => setDefaultHeaded(e.target.checked)}
            />
            <label>Run headed (show browser)</label>
          </div>

          <div>
            <label className="text-sm font-medium">Timeout (ms)</label>
            <input
              type="number"
              value={timeoutMs}
              onChange={(e) => setTimeoutMs(Number(e.target.value))}
              className="input"
            />
          </div>
        </div>

        {/* CREDENTIALS */}
        <div className="mt-6">
          <h3 className="font-semibold text-lg mb-2">Credentials</h3>

          {credentials.map((c, idx) => (
            <div key={idx} className="border rounded-md p-3 mb-3">
              <div className="flex justify-between">
                <input
                  value={c.role}
                  onChange={(e) => {
                    const copy = [...credentials];
                    copy[idx].role = e.target.value;
                    setCredentials(copy);
                  }}
                  className="input w-32 text-sm"
                  placeholder="Role (qa/admin)"
                />
                <button
                  onClick={() =>
                    setCredentials(credentials.filter((_, i) => i !== idx))
                  }
                >
                  <Trash size={16} />
                </button>
              </div>

              <div className="grid grid-cols-2 gap-2 mt-2">
                <input
                  value={c.username}
                  onChange={(e) => {
                    const copy = [...credentials];
                    copy[idx].username = e.target.value;
                    setCredentials(copy);
                  }}
                  className="input"
                  placeholder="Username"
                />
                <input
                  value={c.password}
                  onChange={(e) => {
                    const copy = [...credentials];
                    copy[idx].password = e.target.value;
                    setCredentials(copy);
                  }}
                  className="input"
                  placeholder="Password"
                />
              </div>

              <textarea
                value={c.notes || ""}
                onChange={(e) => {
                  const copy = [...credentials];
                  copy[idx].notes = e.target.value;
                  setCredentials(copy);
                }}
                className="input mt-2"
                placeholder="Notes"
              />
            </div>
          ))}

          <button
            onClick={() =>
              setCredentials([
                ...credentials,
                { role: "qa", username: "", password: "" },
              ])
            }
            className="bg-gray-200 hover:bg-gray-300 px-3 py-1 rounded-md flex items-center gap-2"
          >
            <Plus size={16} /> Add credential
          </button>
        </div>

        {/* VARIABLES */}
        <div className="mt-6">
          <h3 className="font-semibold text-lg mb-2">Variables</h3>

          {variables.map(([key, value], idx) => (
            <div key={idx} className="flex gap-2 mb-2">
              <input
                value={key}
                onChange={(e) => {
                  const copy = [...variables];
                  copy[idx][0] = e.target.value;
                  setVariables(copy);
                }}
                className="input"
                placeholder="Key"
              />
              <input
                value={value}
                onChange={(e) => {
                  const copy = [...variables];
                  copy[idx][1] = e.target.value;
                  setVariables(copy);
                }}
                className="input"
                placeholder="Value"
              />
              <button
                onClick={() =>
                  setVariables(variables.filter((_, i) => i !== idx))
                }
                className="text-red-500"
              >
                <Trash size={16} />
              </button>
            </div>
          ))}

          <button
            onClick={() => setVariables([...variables, ["", ""]])}
            className="bg-gray-200 hover:bg-gray-300 px-3 py-1 rounded-md flex items-center gap-2"
          >
            <Plus size={16} /> Add variable
          </button>
        </div>

        {/* FOOTER */}
        <div className="mt-8 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-200 rounded-md"
          >
            Cancel
          </button>
          <button
            onClick={save}
            disabled={saving}
            className="px-5 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700"
          >
            {saving ? "Saving..." : "Create"}
          </button>
        </div>
      </div>
    </div>
  );
}
