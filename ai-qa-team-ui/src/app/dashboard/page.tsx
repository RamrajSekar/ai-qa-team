"use client";

import { motion } from "framer-motion";
import { useAuth } from "@/components/providers/AuthProvider";

interface StatCardProps {
  label: string;
  value: number | string;
  helper?: string;
}

interface UsageCardProps {
  label: string;
  used: number;
  limit: number;
}

export default function DashboardPage() {
  const { user } = useAuth();

  const plan = user?.subscription?.plan ?? "free";
  const usage = user?.subscription?.usage;
  const limits = user?.subscription?.limits;

  const executionsUsed = usage?.executions_used ?? 0;
  const executionsLimit = limits?.executions_limit ?? 0;
  const aiUsed = usage?.ai_gen_used ?? 0;
  const aiLimit = limits?.ai_gen_limit ?? 0;
  const projectsUsed = usage?.projects_used ?? 0;
  const projectsLimit = limits?.projects_limit ?? 1;

  const aiLeft = aiLimit ? Math.max(aiLimit - aiUsed, 0) : 0;

  return (
    <motion.div
      className="space-y-10"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
    >
      {/* ---------------- HEADER ---------------- */}
      <motion.header
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between"
      >
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-purple-600">
            Dashboard
          </p>

          {/* <h1 className="text-3xl font-bold text-neutral-900 mt-1">
            Welcome , {user?.name ?? "there"} 👋
          </h1> */}

          <p className="text-sm text-neutral-600 mt-2">
            Here's your usage overview and plan details.
          </p>
        </div>

      </motion.header>

      {/* ---------------- STATS ---------------- */}
      <section className="grid gap-6 md:grid-cols-3">
        <StatCard
          label="Projects"
          value={projectsUsed}
          helper={`Limit: ${projectsLimit}`}
        />
        <StatCard
          label="Executions this month"
          value={executionsUsed}
          helper={`${executionsUsed}/${executionsLimit} used`}
        />
        <StatCard
          label="AI generations left"
          value={aiLimit ? aiLeft : "—"}
          helper={`${aiUsed}/${aiLimit} used`}
        />
      </section>

      {/* ---------------- USAGE CARDS ---------------- */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-neutral-800">
            Usage overview
          </h2>
          <span className="text-xs text-neutral-500">Resets each billing period</span>
        </div>

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {usage && limits ? (
            <>
              <UsageCard label="Stories" used={usage.stories_used} limit={limits.stories_limit} />
              <UsageCard label="Scenarios" used={usage.scenarios_used} limit={limits.scenarios_limit} />
              <UsageCard label="Executions" used={usage.executions_used} limit={limits.executions_limit} />
              <UsageCard label="AI generations" used={usage.ai_gen_used} limit={limits.ai_gen_limit} />
              <UsageCard label="Team members" used={usage.team_members_used} limit={limits.team_members_limit} />
              <UsageCard label="Projects" used={usage.projects_used} limit={limits.projects_limit} />
            </>
          ) : (
            <p className="text-sm text-neutral-500">
              No usage data available yet.
            </p>
          )}
        </div>
      </section>
    </motion.div>
  );
}

/* ---------------- COMPONENTS ---------------- */

function StatCard({ label, value, helper }: StatCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="backdrop-blur-xl bg-white/50 border border-white/30 shadow-lg rounded-xl p-5"
    >
      <p className="text-xs text-neutral-600">{label}</p>
      <p className="mt-2 text-3xl font-semibold text-neutral-900">{value}</p>
      {helper && <p className="mt-1 text-xs text-neutral-500">{helper}</p>}
    </motion.div>
  );
}

function UsageCard({ label, used, limit }: UsageCardProps) {
  const percent = Math.min(100, Math.round((used / (limit || 1)) * 100));

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="backdrop-blur-xl bg-white/50 border border-white/30 shadow-lg rounded-xl p-5 flex flex-col gap-2"
    >
      <div className="flex items-center justify-between">
        <span className="font-medium text-neutral-800">{label}</span>
        <span className="text-xs text-neutral-600">
          {used}/{limit}
        </span>
      </div>

      <div className="h-2 bg-neutral-200 rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${percent}%` }}
          transition={{ duration: 0.6 }}
          className="h-full bg-purple-500 rounded-full"
        />
      </div>

      <span className="text-[11px] text-neutral-500">
        {percent}% of {label.toLowerCase()} used.
      </span>
    </motion.div>
  );
}
