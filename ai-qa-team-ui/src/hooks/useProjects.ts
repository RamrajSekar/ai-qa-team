"use client";

import { createContext, createElement, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { apiFetch } from "@/utils/api";
import { useAuth } from "@/components/providers/AuthProvider";

export interface Project {
  id: string;
  project_id: string;
  name: string;
  created_at: string;
  current_user_role?: "ADMIN" | "TESTER";
}

const ProjectContext = createContext<{
  projects: Project[]; loading: boolean; failed: boolean; reload: () => Promise<void>;
} | null>(null);

export function ProjectsProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const owner: string | undefined = user?.email;
  const [state, setState] = useState<{ owner: string; projects: Project[]; failed: boolean }>();
  const pending = useRef<AbortController | null>(null);
  const load = useCallback(async () => {
    if (!owner) return;
    pending.current?.abort();
    const controller = new AbortController();
    pending.current = controller;
    try {
      const res = await apiFetch("/projects", {
        signal: AbortSignal.any([controller.signal, AbortSignal.timeout(15000)]),
      });
      if (!res.ok || !Array.isArray(res.data)) throw new Error("Could not load projects.");
      if (!controller.signal.aborted) setState({ owner, projects: res.data, failed: false });
    } catch {
      if (!controller.signal.aborted) setState(previous => ({
        owner, projects: previous?.owner === owner ? previous.projects : [], failed: true,
      }));
    }
  }, [owner]);

  useEffect(() => {
    const refresh = () => { void load(); };
    refresh();
    window.addEventListener("projects-updated", refresh);

    return () => {
      window.removeEventListener("projects-updated", refresh);
      pending.current?.abort();
    };
  }, [load]);

  const active = owner && state?.owner === owner ? state : undefined;
  return createElement(ProjectContext.Provider, {
    value: { projects: active?.projects ?? [], loading: !active, failed: active?.failed ?? false, reload: load },
  }, children);
}

export function useProjects() {
  const context = useContext(ProjectContext);
  if (!context) throw new Error("useProjects must be inside ProjectsProvider");
  return context;
}
