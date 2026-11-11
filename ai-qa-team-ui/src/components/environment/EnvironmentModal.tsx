"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import CredentialFields from "./CredentialFields";
import VariablesEditor from "./VariablesEditor";

// ----------------------------------------
// TABS
// ----------------------------------------
const TABS = ["General", "Auth", "Credentials", "Variables", "Execution"];

// ----------------------------------------
// MAIN MODAL COMPONENT
// ----------------------------------------
export default function EnvironmentModal({
  open,
  onClose,
  mode,            // "create" | "edit"
  projectId,
  env,
  onSaved
}: any) {

  // -------------------------------
  // Unified form object
  // -------------------------------
  const [form, setForm] = useState({
    env_type: "",
    base_url: "",
    api_base_url: "",
    auth_type: "none",
    auth_token: "",
    credentials: [],
    variables: {},
    default_browser: "chromium",
    default_headed: false,
    default_timeout_ms: 10000,
  });

  const [activeTab, setActiveTab] = useState("General");

  // -----------------------------------
  // Sync form values when editing
  // -----------------------------------
  useEffect(() => {
    if (open && mode === "edit" && env) {
      setForm({
        env_type: env.env_type || "",
        base_url: env.base_url || "",
        api_base_url: env.api_base_url || "",
        auth_type: env.auth_type || "none",
        auth_token: env.auth_token || "",
        credentials: env.credentials || [],
        variables: env.variables || {},
        default_browser: env.default_browser || "chromium",
        default_headed: env.default_headed || false,
        default_timeout_ms: env.default_timeout_ms || 10000,
      });
      setActiveTab("General");
    }

    if (open && mode === "create") {
      setForm({
        env_type: "",
        base_url: "",
        api_base_url: "",
        auth_type: "none",
        auth_token: "",
        credentials: [],
        variables: {},
        default_browser: "chromium",
        default_headed: false,
        default_timeout_ms: 10000,
      });
      setActiveTab("General");
    }
  }, [open, mode, env]);

  if (!open) return null;

  // -----------------------------------
  // Update form fields
  // -----------------------------------
  function updateField(key: string, value: any) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  // -----------------------------------
  // Save
  // -----------------------------------
  async function handleSave() {
    const payload = {
      project_id: projectId,
      ...form,
      auth_token: form.auth_type === "bearer" ? form.auth_token : null,
    };

    const url =
      mode === "edit"
        ? `/environments/${env.env_id}`
        : `/environments`;

    const method = mode === "edit" ? "PATCH" : "POST";

    const res = await fetch(process.env.NEXT_PUBLIC_API_URL + url, {
      method,
      credentials: "include",
      headers: { "Content-Type": "application/json" },
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
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        className="bg-white rounded-xl shadow-2xl w-[900px] max-h-[90vh] overflow-hidden flex flex-col"
      >
        {/* HEADER */}
        <div className="flex justify-between items-center px-6 py-4 border-b">
          <h2 className="text-xl font-semibold">
            {mode === "edit" ? "Edit Environment" : "Create Environment"}
          </h2>

          <button onClick={onClose} className="text-gray-500 hover:text-black text-xl">
            ✕
          </button>
        </div>

        {/* TAB BAR */}
        <div className="px-6 py-3 border-b flex gap-4 text-sm font-medium">
          {TABS.map((t) => (
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
              <TabGeneral form={form} updateField={updateField} />
            )}

            {/* AUTH */}
            {activeTab === "Auth" && (
              <TabAuth form={form} updateField={updateField} />
            )}

            {/* CREDENTIALS */}
            {activeTab === "Credentials" && (
              <CredentialFields
                credentials={form.credentials}
                setCredentials={(v: any) => updateField("credentials", v)}
              />
            )}

            {/* VARIABLES */}
            {activeTab === "Variables" && (
              <VariablesEditor
                variables={form.variables}
                setVariables={(v: any) => updateField("variables", v)}
              />
            )}

            {/* EXEC */}
            {activeTab === "Execution" && (
              <TabExecution form={form} updateField={updateField} />
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
            disabled={!form.env_type || !form.base_url}
            className={`px-4 py-2 rounded text-white 
              ${
                form.env_type && form.base_url
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

//
// ------------------------------------------------------
// SUB COMPONENTS
// ------------------------------------------------------
//

function TabGeneral({ form, updateField }: any) {
  return (
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
          value={form.env_type}
          onChange={(e) => updateField("env_type", e.target.value)}
          placeholder="qa / staging / prod"
          className="w-full border p-2 rounded mt-1"
        />
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div>
          <label className="text-sm font-medium">Base URL</label>
          <input
            value={form.base_url}
            onChange={(e) => updateField("base_url", e.target.value)}
            className="w-full border p-2 rounded mt-1"
          />
        </div>

        <div>
          <label className="text-sm font-medium">API Base URL</label>
          <input
            value={form.api_base_url}
            onChange={(e) => updateField("api_base_url", e.target.value)}
            className="w-full border p-2 rounded mt-1"
          />
        </div>
      </div>
    </motion.div>
  );
}

function TabAuth({ form, updateField }: any) {
  return (
    <motion.div
      key="auth"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="space-y-4"
    >
      <label className="text-sm font-medium">Auth Type</label>

      <select
        value={form.auth_type}
        onChange={(e) => updateField("auth_type", e.target.value)}
        className="border p-2 rounded"
      >
        <option value="none">None</option>
        <option value="basic">Basic Auth</option>
        <option value="bearer">Bearer Token</option>
      </select>

      {form.auth_type === "bearer" && (
        <div>
          <label className="text-sm font-medium">Bearer Token</label>
          <input
            value={form.auth_token}
            onChange={(e) => updateField("auth_token", e.target.value)}
            className="w-full border p-2 rounded mt-1"
          />
        </div>
      )}
    </motion.div>
  );
}

function TabExecution({ form, updateField }: any) {
  return (
    <motion.div
      key="exec"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="space-y-4"
    >
      <div className="grid grid-cols-3 gap-6">
        <div>
          <label className="text-sm font-medium">Default Browser</label>
          <select
            value={form.default_browser}
            onChange={(e) => updateField("default_browser", e.target.value)}
            className="border p-2 rounded w-full mt-1"
          >
            <option value="chromium">Chromium</option>
            <option value="firefox">Firefox</option>
            <option value="webkit">Webkit</option>
          </select>
        </div>

        <div>
          <label className="text-sm font-medium flex gap-2 items-center">
            Headed
            <input
              type="checkbox"
              checked={form.default_headed}
              onChange={(e) =>
                updateField("default_headed", e.target.checked)
              }
            />
          </label>
        </div>

        <div>
          <label className="text-sm font-medium">Timeout (ms)</label>
          <input
            type="number"
            className="border p-2 rounded w-full mt-1"
            value={form.default_timeout_ms}
            onChange={(e) =>
              updateField("default_timeout_ms", Number(e.target.value))
            }
          />
        </div>
      </div>
    </motion.div>
  );
}
