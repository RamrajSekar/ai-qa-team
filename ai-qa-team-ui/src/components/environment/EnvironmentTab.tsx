"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/utils/api";
import { Environment } from "@/types/environment";
import EnvironmentList from "./EnvironmentList";
import EnvironmentModal from "./EnvironmentModal";

interface Props {
  projectId: string;
}

export default function EnvironmentTab({ projectId }: Props) {
  const [environments, setEnvironments] = useState<Environment[]>([]);
  const [loading, setLoading] = useState(true);

  const [modalOpen, setModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState<"create" | "edit">("create");
  const [selectedEnv, setSelectedEnv] = useState<Environment | null>(null);

  async function refresh() {
    setLoading(true);
    const res = await apiFetch(
      `${process.env.NEXT_PUBLIC_API_URL}/environments?project_id=${projectId}`
    );

    if (res.ok) {
      const data = (await res.json()) as Environment[];
      setEnvironments(data);
    }
    setLoading(false);
  }

  useEffect(() => {
    refresh();
  }, [projectId]);

  return (
    <div className="p-6 space-y-6">
      {/* HEADER */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-xl font-bold">Environments</h2>
          <p className="text-gray-500 text-sm">
            Each environment stores URLs, credentials, and variables.
          </p>
        </div>
        <button
          onClick={() => {
            setSelectedEnv(null);
            setModalMode("create");
            setModalOpen(true);
          }}
          className="bg-purple-600 text-white px-4 py-2 rounded-md hover:bg-purple-700"
        >
          + Add Environment
        </button>
      </div>

      {/* LIST */}
      <EnvironmentList
        environments={environments}
        loading={loading}
        onEdit={(env) => {
          setSelectedEnv(env);
          setModalMode("edit");
          setModalOpen(true);
        }}
        refresh={refresh}   // ✅ FIX: REQUIRED PROP PASSED HERE
      />

      {/* MODAL */}
      <EnvironmentModal
        open={modalOpen}
        mode={modalMode}
        projectId={projectId}
        env={selectedEnv}
        onClose={() => setModalOpen(false)}
        onSaved={refresh}
      />
    </div>
  );
}
