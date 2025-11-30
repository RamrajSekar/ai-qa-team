"use client";

import { useState, useEffect } from "react";
import { apiFetch } from "@/utils/api";

export interface Project {
  id: string;
  project_id: string;
  name: string;
  created_at: string;
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
    load();
  }, []);

  return { projects, loading, reload: load };
}
