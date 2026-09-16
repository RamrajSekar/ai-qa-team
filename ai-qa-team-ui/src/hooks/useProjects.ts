"use client";

import { useState, useEffect } from "react";
import { apiFetch } from "@/utils/api";

export interface Project {
  id: string;
  project_id: string;
  name: string;
  created_at: string;
  current_user_role?: "ADMIN" | "TESTER";
}

export function useProjects() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    const res = await apiFetch("/projects");
    if (res.ok && Array.isArray(res.data)) {
      setProjects(res.data);
    }
    setLoading(false);
  }

  useEffect(() => {
    // Initial load
    load();

    // 🔥 Listen for project updates globally
    const refresh = () => load();
    window.addEventListener("projects-updated", refresh);

    return () => {
      window.removeEventListener("projects-updated", refresh);
    };
  }, []);

  return { projects, loading, reload: load };
}
