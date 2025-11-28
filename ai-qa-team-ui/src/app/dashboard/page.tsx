"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/providers/AuthProvider";
import CreateProjectModal from "@/components/projects/CreateProjectModal";
import { apiFetch } from "@/utils/api";
import Link from "next/link";

interface Project {
  id: string;
  project_id: string;
  name: string;
  created_by: string;
  created_at: string;
}

export default function DashboardPage() {
  const { user } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  const [openModal, setOpenModal] = useState(false);

  // -----------------------------
  // LOAD PROJECTS
  // -----------------------------
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

  if (!user) return <p className="p-6">Loading...</p>;

  return (
    <div className="p-6 space-y-10">
      {/* ---------------- HEADER ---------------- */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Dashboard</h2>

        <button
          onClick={() => setOpenModal(true)}
          className="bg-purple-600 text-white px-4 py-2 rounded-md hover:bg-purple-700"
        >
          + Create Project
        </button>
      </div>

      {/* ---------------- PROJECT LIST ---------------- */}
      <div className="space-y-4">
        <h3 className="text-xl font-semibold">Your Projects</h3>

        {loading ? (
          <p>Loading...</p>
        ) : projects.length === 0 ? (
          <div className="border rounded-md p-8 text-center text-gray-500">
            <p>No projects created yet.</p>
            <button
              onClick={() => setOpenModal(true)}
              className="mt-4 bg-purple-600 text-white px-4 py-2 rounded-md hover:bg-purple-700"
            >
              Create your first project
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4">
            {projects.map((p) => (
              <Link
                key={p.project_id}
                href={`/projects/${p.project_id}`}
                className="p-5 border rounded-lg shadow-sm hover:shadow-md bg-white transition"
              >
                <h4 className="font-semibold text-lg">{p.name}</h4>
                <p className="text-xs text-gray-500">ID: {p.project_id}</p>
              </Link>
            ))}
          </div>
        )}
      </div>

      {/* ---------------- MODAL ---------------- */}
      <CreateProjectModal
        open={openModal}
        onClose={() => setOpenModal(false)}
        onCreated={loadProjects}
        createdBy={user.email}     // FIXED ✔
      />
    </div>
  );
}
