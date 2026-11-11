"use client";
import { useFeatures } from "@/components/providers/FeatureFlagsProvider";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/providers/AuthProvider";
import CreateProjectModal from "@/components/projects/CreateProjectModal";
import ExecutionTrendChart from "@/components/dashboard/ExecutionTrendChart";
import AiUsageChart from "@/components/dashboard/AiUsage";
import OnboardingModal from "@/components/onboarding/OnboardingModal";
import { useProjects } from "@/hooks/useProjects";
import Link from "next/link";

export default function DashboardPage() {
  const { enabled } = useFeatures();
  const aiEnabled = enabled("scenario_generation") || enabled("test_generation");
  const { user, refreshSubscription } = useAuth();
  const { projects, loading, failed, reload: loadProjects } = useProjects();

  const [openProjectModal, setOpenProjectModal] = useState(false);
  const [openOnboarding, setOpenOnboarding] = useState(false);

  /** Reopen onboarding when last project is deleted */
  useEffect(() => {
    if (!loading && !failed && projects.length === 0) {
      setOpenOnboarding(true);
    }
  }, [loading, failed, projects.length]);

  /** Open onboarding if new user */
  useEffect(() => {
    if (!user) return;

    if (user.onboarding?.onboarding_status !== "completed") {
      setOpenOnboarding(true);
    }
  }, [user]);

  if (!user) return <p className="p-8">Loading...</p>;

  const usage = user.subscription?.usage || {};
  const limits = user.subscription?.limits || {};

  return (
    <div className="px-6 py-8 md:px-10 lg:px-14 space-y-10 max-w-[1400px]">

      {/* ONBOARDING MODAL */}
      {openOnboarding && (
        <OnboardingModal
          user={user}
          refreshUser={refreshSubscription}
          onProjectsReload={loadProjects}
          onClose={() => setOpenOnboarding(false)}
        />
      )}

      {/* HEADER */}
      <div className="flex items-center justify-between">
        <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>

        <button
          onClick={() => setOpenProjectModal(true)}
          className="bg-purple-600 text-white px-4 py-2 rounded-md hover:bg-purple-700 transition"
        >
          + Create Project
        </button>
      </div>

      {/* KPI CARDS */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5 pt-2">
        <KPI title="Projects" used={usage.projects_used} max={limits.projects_limit} />
        {enabled("story_management") && <KPI title="Stories" used={usage.stories_used} max={limits.stories_limit} />}
        {enabled("scenario_generation") && <KPI title="Scenarios" used={usage.scenarios_used} max={limits.scenarios_limit} />}
        <KPI title="Executions" used={usage.executions_used} max={limits.executions_limit} />
        {aiEnabled && <KPI title="AI Generations" used={usage.ai_gen_used} max={limits.ai_gen_limit} />}
        <KPI title="Team Members" used={usage.team_members_used} max={limits.team_members_limit} />
      </div>

      {/* CHARTS SECTION */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {enabled("native_execution") && <ExecutionTrendChart
          data={[
            { date: "Mon", total: 5, passed: 4, failed: 1 },
            { date: "Tue", total: 7, passed: 6, failed: 1 },
            { date: "Wed", total: 3, passed: 2, failed: 1 },
            { date: "Thu", total: 6, passed: 4, failed: 2 },
            { date: "Fri", total: 9, passed: 7, failed: 2 },
          ]}
        />}
        {aiEnabled && <AiUsageChart />}
      </div>

      {/* PROJECT LIST */}
      <div className="pt-2 max-w-[1200px]">
        <h3 className="text-xl font-semibold mb-4">Your Projects</h3>

        {loading ? (
          <p>Loading...</p>
        ) : projects.length === 0 ? (
          <div className="border rounded-md p-10 text-center text-gray-500 bg-white shadow-sm">
            <p>No projects created yet.</p>
            <button
              onClick={() => setOpenProjectModal(true)}
              className="mt-4 bg-purple-600 text-white px-4 py-2 rounded-md hover:bg-purple-700 transition"
            >
              Create your first project
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {projects.map((p: any) => (
              <Link
                key={p.project_id}
                href={`/projects/${p.project_id}`}
                className="p-5 border rounded-lg bg-white shadow hover:shadow-md transition"
              >
                <h4 className="font-semibold text-lg">{p.name}</h4>
                <p className="text-xs text-gray-500 mt-1">ID: {p.project_id}</p>
              </Link>
            ))}
          </div>
        )}
      </div>

      {/* CREATE PROJECT MODAL */}
      <CreateProjectModal
        open={openProjectModal}
        onClose={() => setOpenProjectModal(false)}
        onCreated={async () => { await Promise.all([loadProjects(), refreshSubscription()]); }}
        createdBy={user.email}
      />
    </div>
  );
}

function KPI({ title, used, max }: { title: string; used: any; max: any }) {
  return (
    <div className="bg-white border rounded-lg p-5 shadow-sm hover:shadow transition">
      <p className="text-sm text-gray-600">{title}</p>
      <p className="text-2xl font-bold mt-1">
        {used ?? 0}/{max ?? 0}
      </p>
    </div>
  );
}
