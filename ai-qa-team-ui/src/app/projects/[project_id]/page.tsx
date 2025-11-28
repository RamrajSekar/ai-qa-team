"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/utils/api";

interface Project {
  id: string;
  project_id: string;
  name: string;
  created_by: string;
  created_at: string;
  agent_identities: Record<string, any>;
}

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  async function loadProjects() {
    setLoading(true);

    const res = await apiFetch(`${process.env.NEXT_PUBLIC_API_URL}/projects`);
    if (res.ok) {
      const data = await res.json();
      setProjects(data);
    }

    setLoading(false);
  }

  useEffect(() => {
    loadProjects();
  }, []);

  return (
    <div className="p-6">
      <h2 className="text-xl font-bold mb-4">Your Projects</h2>

      {loading ? (
        <p>Loading...</p>
      ) : projects.length === 0 ? (
        <p>No projects found.</p>
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
    </div>
  );
}
