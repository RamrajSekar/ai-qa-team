"use client";
import { WorkspaceDialog } from "@/components/ui/workspace-dialog";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import CredentialFields from "./CredentialFields";
import VariablesEditor from "./VariablesEditor";
import { apiFetch } from "@/utils/api";
import type { Environment, EnvironmentFormState } from "@/types/environment";

type UpdateField = <K extends keyof EnvironmentFormState>(key: K, value: EnvironmentFormState[K]) => void;
interface ModalProps {
  open: boolean;
  onClose: () => void;
  mode: "create" | "edit";
  projectId: string;
  env?: Environment | null;
  onSaved: () => void | Promise<void>;
}
interface TabProps { form: EnvironmentFormState; updateField: UpdateField }


// ----------------------------------------
// TABS
// ----------------------------------------
const TABS = ["General", "Auth", "Credentials", "Variables", "Execution"];

// ----------------------------------------
// MAIN MODAL COMPONENT
// ----------------------------------------
export default function EnvironmentModal(props: ModalProps) {
  if (!props.open) return null;
  return <EnvironmentEditor key={`${props.mode}:${props.env?.env_id || "new"}:${props.env?.revision || 0}`} {...props} />;
}

function EnvironmentEditor({ onClose, mode, projectId, env, onSaved }: ModalProps) {
  const initial = mode === "edit" ? env : null;
  const [form, setForm] = useState<EnvironmentFormState>(() => ({
    env_type: initial?.env_type || "",
    base_url: initial?.base_url || "",
    api_base_url: initial?.api_base_url || "",
    auth_type: initial?.auth_type || "none",
    auth_token: "",
    auth_token_configured: initial?.auth_token_configured || false,
    credentials: (initial?.credentials || []).map(credential => ({ ...credential, password: "" })),
    variables: initial?.variables || {},
    default_browser: initial?.default_browser || "chromium",
    default_headed: initial?.default_headed || false,
    default_timeout_ms: initial?.default_timeout_ms || 10000,
    revision: initial?.revision,
  }));
  const [activeTab, setActiveTab] = useState("General");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const updateField: UpdateField = (key, value) => setForm(previous => ({ ...previous, [key]: value }));

  // -----------------------------------
  // Save
  // -----------------------------------
  async function handleSave() {
    setSaving(true);
    setError("");
    try {
      const url = mode === "edit" ? `/environments/${env?.env_id}` : "/environments";
      const response = await apiFetch(url, {
        method: mode === "edit" ? "PATCH" : "POST",
        body: JSON.stringify({ project_id: projectId, ...form }),
      });
      if (!response.ok) throw new Error(typeof response.data?.detail === "string" ? response.data.detail : "Check the environment fields and try again.");
      await onSaved();
      onClose();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Could not save environment.");
    } finally { setSaving(false); }
  }

  return (
    <WorkspaceDialog open onClose={onClose} title={mode === "edit" ? "Edit Environment" : "Create Environment"} busy={saving} className="workspace-dialog-wide environment-dialog">
      <motion.div
        className="environment-dialog-layout"
      >
        {/* HEADER */}
        <div className="flex justify-between items-center px-6 py-4 border-b">
          <h2 className="text-xl font-semibold">
            {mode === "edit" ? "Edit Environment" : "Create Environment"}
          </h2>
        </div>

        {/* TAB BAR */}
        <div className="environment-tabs" aria-label="Environment settings">
          {TABS.map((t) => (
            <button
              key={t}
              aria-pressed={activeTab === t}
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
                setCredentials={(v) => updateField("credentials", v)}
              />
            )}

            {/* VARIABLES */}
            {activeTab === "Variables" && (
              <VariablesEditor
                variables={form.variables}
                setVariables={value => setForm(previous => ({ ...previous, variables: typeof value === "function" ? value(previous.variables) : value }))}
              />
            )}

            {/* EXEC */}
            {activeTab === "Execution" && (
              <TabExecution form={form} updateField={updateField} />
            )}
          </AnimatePresence>
        </div>

        {error && <p role="alert" className="px-6 text-red-700">{error}</p>}
        {/* FOOTER */}
        <div className="flex justify-end gap-4 px-6 py-4 border-t bg-gray-50">
          <button onClick={onClose} className="px-4 py-2 border rounded">
            Cancel
          </button>

          <button
            onClick={handleSave}
            disabled={saving || !form.env_type || !form.base_url}
            className={`px-4 py-2 rounded text-white 
              ${
                form.env_type && form.base_url
                  ? "bg-purple-600 hover:bg-purple-700"
                  : "bg-gray-400 cursor-not-allowed"
              }`}
          >
            {saving ? "Saving…" : "Save Environment"}
          </button>
        </div>
      </motion.div>
    </WorkspaceDialog>
  );
}

//
// ------------------------------------------------------
// SUB COMPONENTS
// ------------------------------------------------------
//

function TabGeneral({ form, updateField }: TabProps) {
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

function TabAuth({ form, updateField }: TabProps) {
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
        onChange={(e) => updateField("auth_type", e.target.value as EnvironmentFormState["auth_type"])}
        className="border p-2 rounded"
      >
        <option value="none">None</option>
        <option value="basic">Basic Auth</option>
        <option value="bearer">Bearer Token</option>
      </select>

      {form.auth_type !== "none" && (
        <div>
          <label className="text-sm font-medium">{form.auth_type === "bearer" ? "Bearer token" : "Basic authorization token"}</label>
          <input
            type="password"
            autoComplete="new-password"
            placeholder={form.auth_token_configured ? "Saved — leave blank to keep" : "Enter token"}
            value={form.auth_token || ""}
            onChange={(e) => updateField("auth_token", e.target.value)}
            className="w-full border p-2 rounded mt-1"
          />
          <label className="block"><input type="checkbox" checked={!!form.clear_auth_token} onChange={event => updateField("clear_auth_token", event.target.checked)} /> Remove saved token</label>
        </div>
      )}
    </motion.div>
  );
}

function TabExecution({ form, updateField }: TabProps) {
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
            onChange={(e) => updateField("default_browser", e.target.value as EnvironmentFormState["default_browser"])}
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
