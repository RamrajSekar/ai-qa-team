// src/app/dashboard/page.tsx
'use client';

import { useAuth } from '@/components/providers/AuthProvider';

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

  const plan = user?.subscription?.plan ?? 'free';
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
    <div className='space-y-8'>
      {/* Header + plan card */}
      <header className='flex flex-col gap-4 md:flex-row md:items-end md:justify-between'>
        <div>
          <p className='text-xs font-medium uppercase tracking-wide text-purple-600'>
            Dashboard
          </p>
          <h1 className='mt-2 text-2xl md:text-3xl font-semibold text-neutral-900'>
            Welcome back, {user?.name ?? 'there'} <span>👋</span>
          </h1>
          <p className='mt-2 text-sm text-neutral-500 max-w-xl'>
            Here’s a quick overview of your AI QA Team usage and what’s left in your current plan.
          </p>
        </div>

        <div className='rounded-2xl border border-neutral-200 bg-white px-5 py-4 shadow-sm flex flex-col items-start md:items-end gap-1'>
          <span className='text-xs uppercase tracking-wide text-neutral-500'>
            Current plan
          </span>
          <span className='text-sm font-semibold text-neutral-900'>
            {plan.toUpperCase()}
          </span>
          <span className='text-xs text-neutral-500'>
            {user?.subscription?.limits?.description ??
              'Perfect for trying out AI-powered test automation.'}
          </span>
          <button className='mt-2 inline-flex items-center rounded-full border border-purple-200 bg-purple-50 px-3 py-1 text-xs font-medium text-purple-700 hover:bg-purple-100 transition'>
            Upgrade plan
          </button>
        </div>
      </header>

      {/* Key stats row */}
      <section className='grid gap-4 md:grid-cols-3'>
        <StatCard
          label='Projects'
          value={projectsUsed}
          helper={`Limit: ${projectsLimit || '—'}`}
        />
        <StatCard
          label='Executions this month'
          value={executionsUsed}
          helper={
            executionsLimit
              ? `${executionsUsed}/${executionsLimit} used`
              : `${executionsUsed} run`
          }
        />
        <StatCard
          label='AI generations left'
          value={aiLimit ? aiLeft : '—'}
          helper={
            aiLimit
              ? `${aiUsed}/${aiLimit} used`
              : 'No AI limit configured yet'
          }
        />
      </section>

      {/* Usage breakdown */}
      <section className='space-y-4'>
        <div className='flex items-center justify-between'>
          <h2 className='text-sm font-semibold text-neutral-800'>
            Usage overview
          </h2>
          <span className='text-xs text-neutral-500'>
            Resets every billing period
          </span>
        </div>

        <div className='grid gap-4 md:grid-cols-2 lg:grid-cols-3'>
          {usage && limits ? (
            <>
              <UsageCard
                label='Stories'
                used={usage.stories_used}
                limit={limits.stories_limit}
              />
              <UsageCard
                label='Scenarios'
                used={usage.scenarios_used}
                limit={limits.scenarios_limit}
              />
              <UsageCard
                label='Executions'
                used={usage.executions_used}
                limit={limits.executions_limit}
              />
              <UsageCard
                label='AI generations'
                used={usage.ai_gen_used}
                limit={limits.ai_gen_limit}
              />
              <UsageCard
                label='Team members'
                used={usage.team_members_used}
                limit={limits.team_members_limit}
              />
              <UsageCard
                label='Projects'
                used={usage.projects_used}
                limit={limits.projects_limit}
              />
            </>
          ) : (
            <p className='text-sm text-neutral-500'>
              Usage data is not available yet. Run some executions to see stats
              here.
            </p>
          )}
        </div>
      </section>
    </div>
  );
}

function StatCard({ label, value, helper }: StatCardProps) {
  return (
    <div className='rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md'>
      <p className='text-xs font-medium text-neutral-500'>{label}</p>
      <p className='mt-2 text-2xl font-semibold text-neutral-900'>{value}</p>
      {helper && (
        <p className='mt-1 text-xs text-neutral-500'>
          {helper}
        </p>
      )}
    </div>
  );
}

function UsageCard({ label, used, limit }: UsageCardProps) {
  const safeLimit = limit || 1;
  const percent = Math.min(
    100,
    Math.round((used / safeLimit) * 100),
  );

  return (
    <div className='rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm flex flex-col gap-2 transition hover:-translate-y-0.5 hover:shadow-md'>
      <div className='flex items-center justify-between text-sm'>
        <span className='font-medium text-neutral-800'>{label}</span>
        <span className='text-xs text-neutral-500'>
          {used}/{limit || '∞'}
        </span>
      </div>
      <div className='h-2 w-full rounded-full bg-neutral-100 overflow-hidden'>
        <div
          className='h-full rounded-full bg-purple-500 transition-[width] duration-500'
          style={{ width: `${percent}%` }}
        />
      </div>
      <span className='text-[11px] text-neutral-400'>
        {percent >= 100
          ? 'Limit reached — consider upgrading your plan.'
          : `${percent}% of your ${label.toLowerCase()} quota used.`}
      </span>
    </div>
  );
}
