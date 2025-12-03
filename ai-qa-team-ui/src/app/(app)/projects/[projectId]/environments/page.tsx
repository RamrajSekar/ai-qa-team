// src/app/projects/[project_id]/environments/page.tsx
"use client";

import { useEffect, useState } from "react";
import { Plus, Globe } from "lucide-react";
import { apiFetch } from "@/utils/api";
import type { Environment } from "@/types/environment";
import EnvironmentCard from "@/components/environment/EnvironmentCard";
import NewEnvironmentModal from "./NewEnvironmentModal";
import EditEnvironmentModal from "./EditEnvironmentModal";

interface PageProps {
  params: {
    project_id: string;
  };
}

export default function EnvironmentsPage({ params }: PageProps) {
  const { project_id } = params;

  const [environments, setEnvironments] = useState<Environment[]>([]);
  const [loading, setLoading] = useState(true);

  const [createOpen, setCreateOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [selectedEnv, setSelectedEnv] = useState<Environment | null>(null);

  async function loadEnvironments() {
    setLoading(true);

    const res = await apiFetch(
      `${process.env.NEXT_PUBLIC_API_URL}/environments?project_id=${project_id}`
    );

    if (res.ok) {
      const data: Environment[] = await res.data;
      setEnvironments(data);
    }

    setLoading(false);
  }

  useEffect(() => {
    if (!project_id) return;
    loadEnvironments();
  }, [project_id]);

  function handleEdit(env: Environment) {
    setSelectedEnv(env);
    setEditOpen(true);
  }

  return (
    <div className="p-6 space-y-6">
      {/* HEADER */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Project Environments</h2>
          <p className="text-sm text-gray-500">
            Manage URLs, credentials, auth tokens, browsers & variables.
          </p>
        </div>

        <button
          onClick={() => setCreateOpen(true)}
          className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-md flex items-center gap-2"
        >
          <Plus size={18} />
          Add Environment
        </button>
      </div>

      {/* LIST / EMPTY / LOADING */}
      {loading ? (
        <p>Loading environments...</p>
      ) : environments.length === 0 ? (
        <div className="border rounded-md p-10 text-center text-gray-500">
          <Globe size={40} className="mx-auto mb-4 text-gray-400" />
          <p>No environments created for this project yet.</p>
          <button
            onClick={() => setCreateOpen(true)}
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
              onEdit={handleEdit}
            />
          ))}
        </div>
      )}

      {/* MODALS */}
      <NewEnvironmentModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        projectId={project_id}
        refresh={loadEnvironments}
      />

      <EditEnvironmentModal
        open={editOpen}
        onClose={() => setEditOpen(false)}
        env={selectedEnv}
        refresh={loadEnvironments}
      />
    </div>
  );
}
