"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Plus, Globe } from "lucide-react";
import { apiFetch } from "@/utils/api";
import type { Environment } from "@/types/environment";
import EnvironmentCard from "@/components/environment/EnvironmentCard";
import EnvironmentModal from "@/components/environment/EnvironmentModal";

export default function EnvironmentsPage() {
  const params = useParams();
  const project_id = params.projectId as string;

  const [environments, setEnvironments] = useState<Environment[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [mode, setMode] = useState<"create" | "edit">("create");
  const [selectedEnv, setSelectedEnv] = useState<Environment | null>(null);
  const [canManage, setCanManage] = useState(false);
  const [error, setError] = useState("");

  const loadEnvironments = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const res = await apiFetch(`/environments?project_id=${encodeURIComponent(project_id)}`);
      if (!res.ok || !Array.isArray(res.data)) throw new Error("Could not load project environments. Try again.");
      setEnvironments((res.data as (Environment & { _id?: string })[]).map(env => ({ ...env, id: env.id ?? env._id ?? "" })));
    } catch { setError("Could not load project environments. Try again."); }
    finally { setLoading(false); }
  }, [project_id]);
  useEffect(() => {
    if (!project_id) return;
    void loadEnvironments();
    let current = true;
    apiFetch(`/projects/${encodeURIComponent(project_id)}`).then(response => {
      if (current && response.ok) setCanManage(response.data.current_user_role === "ADMIN");
    }).catch(() => { if (current) setCanManage(false); });
    return () => { current = false; };
  }, [project_id, loadEnvironments]);

  function handleAdd() {
    setSelectedEnv(null);
    setMode("create");
    setModalOpen(true);
  }

  function handleEdit(env: Environment) {
    setSelectedEnv(env);
    setMode("edit");
    setModalOpen(true);
  }

  function handleCloseModal() {
    setModalOpen(false);
    setSelectedEnv(null);
  }

  async function handleSaved() {
    await loadEnvironments();
    handleCloseModal();
  }

  return (
    <div className="design-page">
      <div className="workspace-page-header">
        <div>
          <p className="workspace-eyebrow">Project setup</p><h1>Project Environments</h1>
          <p className="workspace-description">
            Manage endpoints, credentials, auth tokens, browsers & variables.
          </p>
        </div>

        {canManage && <button
          onClick={handleAdd}
          className="workspace-button workspace-primary"
        >
          <Plus size={18} />
          Add Environment
        </button>}
      </div>

      {error && <div role="alert"><p>{error}</p><button className="workspace-button" onClick={() => void loadEnvironments()}>Try again</button></div>}
      {loading ? (
        <p>Loading environments...</p>
      ) : environments.length === 0 ? (
        <div className="border rounded-md p-10 text-center text-gray-500">
          <Globe size={40} className="mx-auto mb-4 text-gray-400" />
          <p>No environments created for this project yet.</p>
          {canManage && <button
            onClick={handleAdd}
            className="mt-4 bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-md"
          >
            Create Environment
          </button>}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {environments.map((env) => (
            <EnvironmentCard
              key={env.id}
              env={env}
              refresh={loadEnvironments}
              onEdit={() => handleEdit(env)}
              canManage={canManage}
            />
          ))}
        </div>
      )}

      {canManage && <EnvironmentModal
        open={modalOpen}
        mode={mode}
        projectId={project_id}
        env={selectedEnv}
        onClose={handleCloseModal}
        onSaved={handleSaved}
      />}
    </div>
  );
}
