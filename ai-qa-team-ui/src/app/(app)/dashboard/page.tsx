"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/providers/AuthProvider";
import CreateProjectModal from "@/components/projects/CreateProjectModal";
import ExecutionTrendChart from "@/components/dashboard/ExecutionTrendChart";
import AiUsageChart from "@/components/dashboard/AiUsage";
import OnboardingModal from "@/components/onboarding/OnboardingModal";
import { apiFetch } from "@/utils/api";
import Link from "next/link";

export default function DashboardPage() {
  const { user, setUser } = useAuth();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);

  const [openProjectModal, setOpenProjectModal] = useState(false);
  const [openOnboarding, setOpenOnboarding] = useState(false);

  async function loadProjects() {
    setLoading(true);
    const res = await apiFetch(`/projects`);
    if (res.ok) setProjects(res.data);
    setLoading(false);
  }

  async function refreshUser() {
    const res = await apiFetch(`/auth/me`);
    if (res.ok) setUser(res.data.user);
  }

  /* LOAD PROJECTS */
  useEffect(() => {
    loadProjects();
  }, []);

  /* OPEN ONBOARDING ONLY IF NEEDED */
  useEffect(() => {
    if (!user) return;

    const status = user.onboarding?.onboarding_status;

    if (status !== "completed") {
      setOpenOnboarding(true);
    }
  }, [user]);

  if (!user) return <p className="p-6">Loading...</p>;

  const usage = user.subscription?.usage || {};
  const limits = user.subscription?.limits || {};

  return (
    <div className="relative p-6 space-y-10">

      {/* ONBOARDING */}
      {openOnboarding && (
        <OnboardingModal
          user={user}
          refreshUser={refreshUser}
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

      {/* KPI CARDS */}
      <div className="grid grid-cols-4 gap-4">
        <KPI title="Projects" used={usage.projects_used} max={limits.projects_limit} />
        <KPI title="Executions" used={usage.executions_used} max={limits.executions_limit} />
        <KPI title="AI Generations" used={usage.ai_gen_used} max={limits.ai_gen_limit} />
        <KPI title="Team Members" used={usage.team_members_used} max={limits.team_members_limit} />
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
            {projects.map((p: any) => (
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

      {/* PROJECT CREATE MODAL */}
      <CreateProjectModal
        open={openProjectModal}
        onClose={() => setOpenProjectModal(false)}
        onCreated={loadProjects}
        createdBy={user.email}
      />
    </div>
  );
}

function KPI({ title, used, max }: { title: string; used: any; max: any }) {
  return (
    <div className="bg-white p-4 rounded-lg shadow border">
      <p className="text-sm text-gray-500">{title}</p>
      <p className="text-2xl font-bold">
        {used ?? 0}/{max ?? 0}
      </p>
    </div>
  );
}
