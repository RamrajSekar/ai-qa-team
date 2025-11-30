// src/app/(app)/dashboard/page.tsx
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/components/providers/AuthProvider";
import { apiFetch } from "@/utils/api";
import CreateProjectModal from "@/components/projects/CreateProjectModal";
import ExecutionTrendChart from "@/components/dashboard/ExecutionTrendChart";
import AiUsageChart from "@/components/dashboard/AiUsage";
import OnboardingModal from "@/components/onboarding/OnboardingModal";

interface Project {
  id: string;
  project_id: string;
  name: string;
  created_by: string;
  created_at: string;
}

export default function DashboardPage() {
  const { user, setUser } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [openProjectModal, setOpenProjectModal] = useState(false);
  const [openOnboarding, setOpenOnboarding] = useState(false);

  const loadProjects = async () => {
    setLoading(true);
    const res = await apiFetch("/projects");
    if (res.ok && Array.isArray(res.data)) {
      setProjects(res.data);
    }
    setLoading(false);
  };

  const refreshUser = async () => {
    const res = await apiFetch("/auth/me");
    if (res.ok) {
      setUser(res.data.user);
    }
  };

  useEffect(() => {
    loadProjects();
  }, []);

  // Only open onboarding when we *know* user is loaded and not completed
  useEffect(() => {
    if (!user) return;
    const status = user.onboarding?.onboarding_status;
    if (status && status !== "completed") {
      setOpenOnboarding(true);
    }
  }, [user]);

  if (!user) {
    return <p className="p-6">Loading...</p>;
  }

  const usage = user.subscription?.usage;
  const limits = user.subscription?.limits;

  return (
    <div className="relative p-6 space-y-10">
      {openOnboarding && (
        <OnboardingModal
          user={user}
          refreshUser={async () => {
            await refreshUser();
            await loadProjects();
          }}
          onProjectsReload={loadProjects}
          onClose={() => setOpenOnboarding(false)}
        />
      )}

      {/* HEADER */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Dashboard</h2>
        <button
          onClick={() => setOpenProjectModal(true)}
          className="bg-purple-600 text-white px-4 py-2 rounded-md hover:bg-purple-700"
        >
          + Create Project
        </button>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-lg shadow border">
          <p className="text-sm text-gray-500">Projects</p>
          <p className="text-2xl font-bold">
            {(usage?.projects_used ?? projects.length)}/{limits?.projects_limit ?? "—"}
          </p>
        </div>

        <div className="bg-white p-4 rounded-lg shadow border">
          <p className="text-sm text-gray-500">Executions</p>
          <p className="text-2xl font-bold">
            {usage?.executions_used ?? 0}/{limits?.executions_limit ?? "—"}
          </p>
        </div>

        <div className="bg-white p-4 rounded-lg shadow border">
          <p className="text-sm text-gray-500">AI Generations</p>
          <p className="text-2xl font-bold">
            {usage?.ai_gen_used ?? 0}/{limits?.ai_gen_limit ?? "—"}
          </p>
        </div>

        <div className="bg-white p-4 rounded-lg shadow border">
          <p className="text-sm text-gray-500">Team Members</p>
          <p className="text-2xl font-bold">
            {usage?.team_members_used ?? 0}/{limits?.team_members_limit ?? "—"}
          </p>
        </div>
      </div>

      {/* CHARTS */}
      <div className="grid grid-cols-2 gap-4 mb-10">
        <ExecutionTrendChart
          data={[
            { date: "Mon", total: 5, passed: 4, failed: 1 },
            { date: "Tue", total: 7, passed: 6, failed: 1 },
            { date: "Wed", total: 3, passed: 2, failed: 1 },
            { date: "Thu", total: 6, passed: 4, failed: 2 },
            { date: "Fri", total: 9, passed: 7, failed: 2 },
          ]}
        />
        <AiUsageChart />
      </div>

      {/* PROJECT LIST */}
      <div className="space-y-4">
        <h3 className="text-xl font-semibold">Your Projects</h3>

        {loading ? (
          <p>Loading...</p>
        ) : projects.length === 0 ? (
          <div className="border rounded-md p-8 text-center text-gray-500">
            <p>No projects created yet.</p>
            <button
              onClick={() => setOpenProjectModal(true)}
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

      <CreateProjectModal
        open={openProjectModal}
        onClose={() => setOpenProjectModal(false)}
        onCreated={async () => {
          await loadProjects();
          await refreshUser(); // keep subscription usage in sync
        }}
        createdBy={user.email}
      />
    </div>
  );
}
