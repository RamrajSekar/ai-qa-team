"use client";

import { useEffect, useState } from "react";
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

  async function loadEnvironments() {
    setLoading(true);

    const res = await apiFetch(`/environments?project_id=${project_id}`);
    console.log("ENV FETCH:", res);

    if (res.ok && Array.isArray(res.data)) {
      const normalized = res.data.map((env: any) => ({
        ...env,
        id: env.id ?? env._id ?? "",
      }));
      setEnvironments(normalized);
    } else {
      console.error("Failed to fetch environments:", res);
    }

    setLoading(false);
  }

  useEffect(() => {
    if (project_id) {
      loadEnvironments();
    }
  }, [project_id]);

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
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Project Environments</h2>
          <p className="text-sm text-gray-500">
            Manage endpoints, credentials, auth tokens, browsers & variables.
          </p>
        </div>

        <button
          onClick={handleAdd}
          className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-md flex items-center gap-2"
        >
          <Plus size={18} />
          Add Environment
        </button>
      </div>

      {loading ? (
        <p>Loading environments...</p>
      ) : environments.length === 0 ? (
        <div className="border rounded-md p-10 text-center text-gray-500">
          <Globe size={40} className="mx-auto mb-4 text-gray-400" />
          <p>No environments created for this project yet.</p>
          <button
            onClick={handleAdd}
            className="mt-4 bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-md"
          >
            Create Environment
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {environments.map((env) => (
            <EnvironmentCard
              key={env.id}
              env={env}
              refresh={loadEnvironments}
              onEdit={() => handleEdit(env)}
            />
          ))}
        </div>
      )}

      <EnvironmentModal
        open={modalOpen}
        mode={mode}
        projectId={project_id}
        env={selectedEnv}
        onClose={handleCloseModal}
        onSaved={handleSaved}
      />
    </div>
  );
}
