"use client";

import { useState } from "react";
import { apiFetch } from "@/utils/api";
import { motion, AnimatePresence } from "framer-motion";

const tabs = ["General", "Auth", "Credentials", "Variables", "Execution"];

export default function EnvironmentModal({
  open,
  onClose,
  mode,
  projectId,
  env,
  onSaved,
}: any) {
  const [activeTab, setActiveTab] = useState("General");

  // Main fields
  const [envType, setEnvType] = useState(env?.env_type || "");
  const [baseUrl, setBaseUrl] = useState(env?.base_url || "");
  const [apiBaseUrl, setApiBaseUrl] = useState(env?.api_base_url || "");

  // Auth fields
  const [authType, setAuthType] = useState(env?.auth_type || "none");
  const [authToken, setAuthToken] = useState(env?.auth_token || "");

  // Credentials
  const [credentials, setCredentials] = useState(env?.credentials || []);

  // Variables
  const [variables, setVariables] = useState(env?.variables || {});

  // Execution
  const [defaultBrowser, setDefaultBrowser] = useState(
    env?.default_browser || "chromium"
  );
  const [defaultHeaded, setDefaultHeaded] = useState(
    env?.default_headed || false
  );
  const [defaultTimeoutMs, setDefaultTimeoutMs] = useState(
    env?.default_timeout_ms || 10000
  );

  if (!open) return null;

  function addCredential() {
    setCredentials([
      ...credentials,
      { role: "", username: "", password: "", notes: "" },
    ]);
  }

  function updateCredential(i: number, field: string, value: any) {
    const updated = [...credentials];
    updated[i][field] = value;
    setCredentials(updated);
  }

  function removeCredential(i: number) {
  setCredentials(
    credentials.filter((_: unknown, idx: number) => idx !== i)
  );
}

  function addVariable() {
    setVariables({ ...variables, "": "" });
  }

  function updateVariable(oldKey: string, key: string, value: string) {
    const updated = { ...variables };
    delete updated[oldKey];
    updated[key] = value;
    setVariables(updated);
  }

  function removeVariable(key: string) {
    const updated = { ...variables };
    delete updated[key];
    setVariables(updated);
  }

  async function handleSave() {
    const payload = {
      project_id: projectId,
      env_type: envType,
      base_url: baseUrl,
      api_base_url: apiBaseUrl,

      auth_type: authType,
      auth_token: authType === "bearer" ? authToken : null,

      credentials,
      variables,

      default_browser: defaultBrowser,
      default_headed: defaultHeaded,
      default_timeout_ms: defaultTimeoutMs,
    };

    const url =
      mode === "edit"
        ? `/environments/${env.env_id}`
        : `/environments`;

    const method = mode === "edit" ? "PATCH" : "POST";

    const res = await apiFetch(url, {
      method,
      body: JSON.stringify(payload),
    });

    if (res.ok) {
      onSaved();
      onClose();
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center">
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        className="bg-white rounded-xl shadow-2xl w-[900px] max-h-[90vh] overflow-hidden flex flex-col"
      >
        {/* HEADER */}
        <div className="flex justify-between items-center px-6 py-4 border-b">
          <h2 className="text-xl font-semibold">
            {mode === "edit" ? "Edit Environment" : "Create Environment"}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-black text-xl"
          >
            ✕
          </button>
        </div>

        {/* TAB BAR */}
        <div className="px-6 py-3 border-b flex gap-4 text-sm font-medium">
          {tabs.map((t) => (
            <button
              key={t}
              onClick={() => setActiveTab(t)}
              className={`pb-2 ${
                activeTab === t
                  ? "text-purple-600 border-b-2 border-purple-600"
                  : "text-gray-500 hover:text-black"
              }`}
            >
              {t}
            </button>
          ))}
        </div>

        {/* CONTENT */}
        <div className="flex-1 overflow-y-auto px-6 py-6">
          <AnimatePresence mode="wait">
            {/* GENERAL */}
            {activeTab === "General" && (
              <motion.div
                key="general"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="space-y-4"
              >
                <div>
                  <label className="text-sm font-medium">Environment Name</label>
                  <input
                    value={envType}
                    onChange={(e) => setEnvType(e.target.value)}
                    className="w-full border p-2 rounded mt-1"
                    placeholder="qa / staging / client-dev / integration"
                  />
                </div>

                <div className="grid grid-cols-2 gap-6">
                  <div>
                    <label className="text-sm font-medium">Base URL</label>
                    <input
                      value={baseUrl}
                      onChange={(e) => setBaseUrl(e.target.value)}
                      className="w-full border p-2 rounded mt-1"
                    />
                  </div>

                  <div>
                    <label className="text-sm font-medium">API Base URL</label>
                    <input
                      value={apiBaseUrl}
                      onChange={(e) => setApiBaseUrl(e.target.value)}
                      className="w-full border p-2 rounded mt-1"
                    />
                  </div>
                </div>
              </motion.div>
            )}

            {/* AUTH */}
            {activeTab === "Auth" && (
              <motion.div
                key="auth"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="space-y-4"
              >
                <label className="text-sm font-medium">Auth Type</label>
                <select
                  value={authType}
                  onChange={(e) => setAuthType(e.target.value)}
                  className="border p-2 rounded"
                >
                  <option value="none">None</option>
                  <option value="basic">Basic Auth</option>
                  <option value="bearer">Bearer Token</option>
                </select>

                {authType === "bearer" && (
                  <div>
                    <label className="text-sm font-medium">Bearer Token</label>
                    <input
                      value={authToken}
                      onChange={(e) => setAuthToken(e.target.value)}
                      className="w-full border p-2 rounded mt-1"
                    />
                  </div>
                )}
              </motion.div>
            )}

            {/* CREDENTIALS */}
            {activeTab === "Credentials" && (
              <motion.div
                key="creds"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="space-y-4"
              >
                <button
                  onClick={addCredential}
                  className="bg-purple-600 text-white px-3 py-1 rounded text-sm"
                >
                  + Add Credential
                </button>

                {credentials.map((cred: any, i: number) => (
                  <div
                    key={i}
                    className="border rounded p-4 bg-gray-50 space-y-2"
                  >
                    <div className="grid grid-cols-3 gap-4">
                      <input
                        className="border p-2 rounded"
                        placeholder="Role"
                        value={cred.role}
                        onChange={(e) =>
                          updateCredential(i, "role", e.target.value)
                        }
                      />
                      <input
                        className="border p-2 rounded"
                        placeholder="Username"
                        value={cred.username}
                        onChange={(e) =>
                          updateCredential(i, "username", e.target.value)
                        }
                      />
                      <input
                        type="password"
                        className="border p-2 rounded"
                        placeholder="Password"
                        value={cred.password}
                        onChange={(e) =>
                          updateCredential(i, "password", e.target.value)
                        }
                      />
                    </div>

                    <textarea
                      className="border p-2 rounded w-full"
                      placeholder="Notes"
                      value={cred.notes}
                      onChange={(e) =>
                        updateCredential(i, "notes", e.target.value)
                      }
                    />

                    <button
                      className="text-red-500 text-sm"
                      onClick={() => removeCredential(i)}
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </motion.div>
            )}

            {/* VARIABLES */}
            {activeTab === "Variables" && (
              <motion.div
                key="vars"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="space-y-4"
              >
                <button
                  onClick={addVariable}
                  className="bg-purple-600 text-white px-3 py-1 rounded text-sm"
                >
                  + Add Variable
                </button>

                {Object.entries(variables).map(([key, val]) => (
                  <div key={key} className="flex gap-3 items-center">
                    <input
                      className="border p-2 rounded w-1/3"
                      defaultValue={key}
                      onChange={(e) =>
                        updateVariable(key, e.target.value, val as string)
                      }
                    />
                    <input
                      className="border p-2 rounded w-1/3"
                      defaultValue={val as string}
                      onChange={(e) =>
                        updateVariable(key, key, e.target.value)
                      }
                    />
                    <button
                      className="text-red-500 text-sm"
                      onClick={() => removeVariable(key)}
                    >
                      ✕
                    </button>
                  </div>
                ))}
              </motion.div>
            )}

            {/* EXECUTION */}
            {activeTab === "Execution" && (
              <motion.div
                key="exec"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="space-y-4"
              >
                <div className="grid grid-cols-3 gap-6">
                  <div>
                    <label className="text-sm font-medium">
                      Default Browser
                    </label>
                    <select
                      value={defaultBrowser}
                      onChange={(e) => setDefaultBrowser(e.target.value)}
                      className="border p-2 rounded w-full mt-1"
                    >
                      <option value="chromium">Chromium</option>
                      <option value="firefox">Firefox</option>
                      <option value="webkit">Webkit</option>
                    </select>
                  </div>

                  <div>
                    <label className="text-sm font-medium flex gap-2 items-center">
                      Headed Mode
                      <input
                        type="checkbox"
                        checked={defaultHeaded}
                        onChange={(e) => setDefaultHeaded(e.target.checked)}
                      />
                    </label>
                  </div>

                  <div>
                    <label className="text-sm font-medium">
                      Timeout (ms)
                    </label>
                    <input
                      type="number"
                      className="border p-2 rounded w-full mt-1"
                      value={defaultTimeoutMs}
                      onChange={(e) =>
                        setDefaultTimeoutMs(Number(e.target.value))
                      }
                    />
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* FOOTER */}
        <div className="flex justify-end gap-4 px-6 py-4 border-t bg-gray-50">
          <button onClick={onClose} className="px-4 py-2 border rounded">
            Cancel
          </button>

          <button
            onClick={handleSave}
            disabled={!envType || !baseUrl}
            className={`px-4 py-2 rounded text-white 
              ${
                envType && baseUrl
                  ? "bg-purple-600 hover:bg-purple-700"
                  : "bg-gray-400 cursor-not-allowed"
              }`}
          >
            Save Environment
          </button>
        </div>
      </motion.div>
    </div>
  );
}
