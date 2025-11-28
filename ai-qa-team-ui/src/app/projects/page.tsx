"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/utils/api";
import CreateProjectModal from "@/components/projects/CreateProjectModal";
import { useAuth } from "@/components/providers/AuthProvider";

interface Project {
  id: string;
  project_id: string;
  name: string;
  created_by: string;
  created_at: string;
  agent_identities: Record<string, any>;
}

export default function ProjectsPage() {
  const { user } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [openModal, setOpenModal] = useState(false);

  async function loadProjects() {
    try {
      setLoading(true);
      const res = await apiFetch(`${process.env.NEXT_PUBLIC_API_URL}/projects`);

      if (res.ok) {
        const data = (await res.json()) as Project[];
        setProjects(data);
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadProjects();
  }, []);

  return (
    <div className="p-6">
      {/* Header + CTA */}
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-bold">Your Projects</h2>

        <button
          onClick={() => setOpenModal(true)}
          className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700"
        >
          + Create Project
        </button>
      </div>

      {/* Projects List */}
      {loading ? (
        <p>Loading...</p>
      ) : projects.length === 0 ? (
        <div className="text-gray-500 text-center mt-10">
          <p>No projects found.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {projects.map((p) => (
            <Link
              key={p.project_id}
              href={`/projects/${p.project_id}`}
              className="p-5 border rounded-lg shadow-sm hover:shadow-md bg-white transition"
            >
              <h3 className="font-semibold text-lg">{p.name}</h3>
              <p className="text-xs text-gray-500">ID: {p.project_id}</p>
            </Link>
          ))}
        </div>
      )}

      {/* Create Project Modal */}
      <CreateProjectModal
        open={openModal}
        onClose={() => setOpenModal(false)}
        onCreated={loadProjects}
        createdBy={user?.email ?? ""}
      />
    </div>
  );
}
