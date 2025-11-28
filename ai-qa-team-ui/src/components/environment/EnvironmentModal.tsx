"use client";

import { useState, useEffect } from "react";
import { X } from "lucide-react";
import { apiFetch } from "@/utils/api";
import { Environment } from "@/types/environment";

export interface EnvironmentModalProps {
  open: boolean;
  mode: "create" | "edit";
  projectId: string;
  env: Environment | null;
  onClose: () => void;
  onSaved: () => Promise<void>;
}

export default function EnvironmentModal({
  open,
  mode,
  projectId,
  env,
  onClose,
  onSaved,
}: EnvironmentModalProps) {
  const [loading, setLoading] = useState(false);

  const [envType, setEnvType] = useState<Environment["env_type"]>("qa");
  const [baseUrl, setBaseUrl] = useState("");
  const [apiBaseUrl, setApiBaseUrl] = useState("");

  const [authType, setAuthType] = useState<Environment["auth_type"]>("none");
  const [authToken, setAuthToken] = useState("");

  const [defaultBrowser, setDefaultBrowser] =
    useState<Environment["default_browser"]>("chromium");

  const [defaultHeaded, setDefaultHeaded] = useState(false);
  const [timeoutMs, setTimeoutMs] = useState(10000);

  const [credentials, setCredentials] = useState<Environment["credentials"]>([]);
  const [variables, setVariables] = useState<[string, string][]>([]);

  // LOAD EXISTING ENVIRONMENT (EDIT MODE)
  useEffect(() => {
    if (!env) return;

    setEnvType(env.env_type);
    setBaseUrl(env.base_url);
    setApiBaseUrl(env.api_base_url || "");

    setAuthType(env.auth_type);
    setAuthToken(env.auth_token || "");

    setDefaultBrowser(env.default_browser);
    setDefaultHeaded(env.default_headed);
    setTimeoutMs(env.default_timeout_ms);

    setCredentials(env.credentials || []);

    setVariables(
      Object.entries(env.variables || {}).map(([k, v]) => [k, String(v)])
    );
  }, [env]);

  async function save() {
    setLoading(true);

    const payload: Environment = {
      id: env?.id ?? "",
      project_id: projectId,
      env_id: env?.env_id ?? "",
      env_type: envType,
      base_url: baseUrl,
      api_base_url: apiBaseUrl,
      auth_type: authType,
      auth_token: authType !== "none" ? authToken : undefined,
      credentials,
      default_browser: defaultBrowser,
      default_headed: defaultHeaded,
      default_timeout_ms: timeoutMs,
      variables: Object.fromEntries(variables.filter(([k]) => k.trim() !== "")),
    };

    const url =
      mode === "edit"
        ? `${process.env.NEXT_PUBLIC_API_URL}/environments/${env?.id}`
        : `${process.env.NEXT_PUBLIC_API_URL}/environments`;

    const res = await apiFetch(url, {
      method: mode === "edit" ? "PUT" : "POST",
      body: JSON.stringify(payload),
    });

    setLoading(false);

    if (res.ok) {
      await onSaved();
      onClose();
    }
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white w-full max-w-3xl rounded-lg shadow-xl p-6 overflow-y-auto max-h-[90vh]">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-bold">
            {mode === "create" ? "Create Environment" : "Edit Environment"}
          </h2>

          <button onClick={onClose}>
            <X size={22} />
          </button>
        </div>

        {/* --- FORM START --- */}
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="label">Environment Type</label>
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
            <label className="label">Base URL</label>
            <input
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              className="input"
            />
          </div>

          <div>
            <label className="label">API Base URL</label>
            <input
              value={apiBaseUrl}
              onChange={(e) => setApiBaseUrl(e.target.value)}
              className="input"
            />
          </div>

          <div>
            <label className="label">Auth Type</label>
            <select
              value={authType}
              onChange={(e) =>
                setAuthType(e.target.value as Environment["auth_type"])
              }
              className="input"
            >
              <option value="none">None</option>
              <option value="basic">Basic</option>
              <option value="bearer">Bearer Token</option>
            </select>
          </div>

          {authType !== "none" && (
            <div className="col-span-2">
              <label className="label">Auth Token</label>
              <input
                value={authToken}
                onChange={(e) => setAuthToken(e.target.value)}
                className="input"
              />
            </div>
          )}
        </div>

        {/* --- CREDENTIALS --- */}
        <div className="mt-8">
          <h3 className="font-semibold text-lg mb-2">Credentials</h3>

          {credentials.map((c, idx) => (
            <div key={idx} className="border p-3 rounded-md mb-3">
              <div className="grid grid-cols-2 gap-2">
                <input
                  className="input"
                  value={c.username}
                  onChange={(e) => {
                    const copy = [...credentials];
                    copy[idx].username = e.target.value;
                    setCredentials(copy);
                  }}
                  placeholder="Username"
                />

                <input
                  className="input"
                  value={c.password}
                  onChange={(e) => {
                    const copy = [...credentials];
                    copy[idx].password = e.target.value;
                    setCredentials(copy);
                  }}
                  placeholder="Password"
                />
              </div>

              <input
                className="input mt-2"
                value={c.notes || ""}
                onChange={(e) => {
                  const copy = [...credentials];
                  copy[idx].notes = e.target.value;
                  setCredentials(copy);
                }}
                placeholder="Notes (optional)"
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
            className="btn-secondary"
          >
            Add Credential
          </button>
        </div>

        {/* --- VARIABLES --- */}
        <div className="mt-8">
          <h3 className="font-semibold text-lg mb-2">Variables</h3>

          {variables.map(([k, v], idx) => (
            <div key={idx} className="flex gap-2 mb-2">
              <input
                value={k}
                onChange={(e) => {
                  const copy = [...variables];
                  copy[idx][0] = e.target.value;
                  setVariables(copy);
                }}
                className="input"
                placeholder="Key"
              />
              <input
                value={v}
                onChange={(e) => {
                  const copy = [...variables];
                  copy[idx][1] = e.target.value;
                  setVariables(copy);
                }}
                className="input"
                placeholder="Value"
              />
            </div>
          ))}

          <button
            onClick={() => setVariables([...variables, ["", ""]])}
            className="btn-secondary"
          >
            Add Variable
          </button>
        </div>

        {/* FOOTER */}
        <div className="mt-8 flex justify-end gap-3">
          <button className="btn-secondary" onClick={onClose}>
            Cancel
          </button>

          <button className="btn-primary" onClick={save} disabled={loading}>
            {loading ? "Saving..." : "Save Environment"}
          </button>
        </div>
      </div>
    </div>
  );
}
