'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useOnboarding } from '@/store/useOnboarding';
import { useAuth } from '@/components/providers/AuthProvider';

type StepId =
  | 'welcome'
  | 'project'
  | 'environments'
  | 'team'
  | 'stories'
  | 'summary';

type OnboardingData = {
  projectName: string;
  projectDomain: string;
  teamSize: string;
  primaryTool: string;
  firstStoryTitle: string;
  firstStoryGoal: string;
};

const STEPS: { id: StepId; title: string; description: string }[] = [
  {
    id: 'welcome',
    title: 'Welcome to QA Squad',
    description:
      'Let’s get your workspace ready – we’ll set up a project, environments, and your first test scenario.',
  },
  {
    id: 'project',
    title: 'Create your first project',
    description:
      'Give your project a name and tell us what kind of application you are testing.',
  },
  {
    id: 'environments',
    title: 'Configure environments',
    description:
      'Connect the environments (QA, Staging, Prod) that your tests will run against.',
  },
  {
    id: 'team',
    title: 'Team & tools',
    description:
      'Tell us about your team and which automation framework you’re using.',
  },
  {
    id: 'stories',
    title: 'Define your first story',
    description:
      'Capture a high-level user story so we can help you generate scenarios and test cases.',
  },
  {
    id: 'summary',
    title: 'Review & finish',
    description:
      'Confirm your setup and jump into the dashboard to start creating scenarios and executions.',
  },
];

export function OnboardingWizard() {
  const router = useRouter();
  const { user } = useAuth();
  const { setCompleted } = useOnboarding();

  const [currentIndex, setCurrentIndex] = useState(0);
  const [saving, setSaving] = useState(false);

  const [data, setData] = useState<OnboardingData>({
    projectName: '',
    projectDomain: '',
    teamSize: '',
    primaryTool: '',
    firstStoryTitle: '',
    firstStoryGoal: '',
  });

  const currentStep = STEPS[currentIndex];
  const isLast = currentIndex === STEPS.length - 1;

  function update<K extends keyof OnboardingData>(key: K, value: OnboardingData[K]) {
    setData((prev) => ({ ...prev, [key]: value }));
  }

  function next() {
    if (currentIndex < STEPS.length - 1) {
      setCurrentIndex((i) => i + 1);
    }
  }

  function back() {
    if (currentIndex > 0) {
      setCurrentIndex((i) => i - 1);
    }
  }

  async function finish() {
    setSaving(true);
    try {
      // ✅ TODO: Call backend here to create:
      // - first project
      // - maybe environments
      // - first story
      //
      // Example (pseudo):
      // await apiFetch('/projects', { method: 'POST', body: JSON.stringify({ name: data.projectName, ...}) })

      setCompleted();
      router.push('/dashboard');
    } catch (err) {
      console.error('Failed to finish onboarding', err);
      // TODO: show toast
    } finally {
      setSaving(false);
    }
  }

  function skipAll() {
    setCompleted();
    router.push('/dashboard');
  }

  if (!user) {
    // Optional: don't render onboarding if unauthenticated
    return null;
  }

  return (
    <div className='min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center px-4'>
      <div className='w-full max-w-4xl bg-slate-900 border border-slate-800 rounded-3xl shadow-xl p-6 md:p-8'>
        {/* Header */}
        <header className='flex items-center justify-between mb-6'>
          <div>
            <h1 className='text-xl font-semibold text-slate-50'>
              Setup Wizard
            </h1>
            <p className='text-sm text-slate-400'>
              Step {currentIndex + 1} of {STEPS.length} · {currentStep.title}
            </p>
          </div>
          <button
            type='button'
            onClick={skipAll}
            className='text-xs md:text-sm text-slate-400 hover:text-slate-200 underline underline-offset-4'
          >
            Skip for now
          </button>
        </header>

        {/* Progress bar */}
        <div className='mb-8'>
          <div className='flex items-center justify-between mb-2'>
            {STEPS.map((step, idx) => {
              const done = idx < currentIndex;
              const active = idx === currentIndex;
              return (
                <div
                  key={step.id}
                  className='flex-1 flex items-center gap-2'
                >
                  <div
                    className={`h-2 rounded-full w-full transition-all ${
                      done
                        ? 'bg-emerald-500'
                        : active
                        ? 'bg-indigo-500'
                        : 'bg-slate-700'
                    }`}
                  />
                </div>
              );
            })}
          </div>
          <p className='text-xs text-slate-400'>
            {currentStep.description}
          </p>
        </div>

        {/* Step content */}
        <div className='mb-8'>
          {currentStep.id === 'welcome' && (
            <div className='space-y-4'>
              <h2 className='text-2xl font-semibold'>
                Welcome, {user?.name || 'there'} 👋
              </h2>
              <p className='text-slate-300 max-w-2xl text-sm md:text-base'>
                In a few quick steps we’ll help you:
              </p>
              <ul className='list-disc list-inside text-slate-300 text-sm md:text-base space-y-1'>
                <li>Create your first QA project.</li>
                <li>Connect the environments you test against.</li>
                <li>Capture your first user story and scenarios.</li>
              </ul>
              <p className='text-xs text-slate-500'>
                You can change everything later from the dashboard &amp; settings.
              </p>
            </div>
          )}

          {currentStep.id === 'project' && (
            <div className='space-y-4'>
              <h2 className='text-xl font-semibold'>Project basics</h2>
              <div className='grid gap-4 md:grid-cols-2'>
                <div className='space-y-2'>
                  <label className='text-sm text-slate-200'>
                    Project name
                  </label>
                  <input
                    type='text'
                    value={data.projectName}
                    onChange={(e) => update('projectName', e.target.value)}
                    placeholder='E.g. Checkout Automation'
                    className='w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500'
                  />
                </div>
                <div className='space-y-2'>
                  <label className='text-sm text-slate-200'>
                    Application domain
                  </label>
                  <select
                    value={data.projectDomain}
                    onChange={(e) => update('projectDomain', e.target.value)}
                    className='w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500'
                  >
                    <option value=''>Select domain</option>
                    <option value='saas'>SaaS / B2B</option>
                    <option value='ecommerce'>E-commerce</option>
                    <option value='fintech'>Fintech</option>
                    <option value='travel'>Travel / Booking</option>
                    <option value='healthcare'>Healthcare</option>
                    <option value='other'>Other</option>
                  </select>
                </div>
              </div>
              <p className='text-xs text-slate-500'>
                This helps us tailor default scenarios and future AI suggestions.
              </p>
            </div>
          )}

          {currentStep.id === 'environments' && (
            <div className='space-y-4'>
              <h2 className='text-xl font-semibold'>Environments</h2>
              <p className='text-sm text-slate-300'>
                You mentioned that environment components/pages already exist –
                so here we just embed or link them.
              </p>
              <div className='mt-4 rounded-xl border border-slate-700 bg-slate-900/60 p-4'>
                {/* 🔁 Replace this block with your real Environment components */}
                {/* Example: <EnvironmentManager /> or <EnvironmentsPanel /> */}
                <p className='text-sm text-slate-400'>
                  TODO: Render your existing <code>Environments</code> component here.
                </p>
              </div>
              <p className='text-xs text-slate-500'>
                You can always add more environments later from Settings → Environments.
              </p>
            </div>
          )}

          {currentStep.id === 'team' && (
            <div className='space-y-4'>
              <h2 className='text-xl font-semibold'>Team & tools</h2>
              <div className='grid gap-4 md:grid-cols-2'>
                <div className='space-y-2'>
                  <label className='text-sm text-slate-200'>
                    Team size
                  </label>
                  <select
                    value={data.teamSize}
                    onChange={(e) => update('teamSize', e.target.value)}
                    className='w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500'
                  >
                    <option value=''>Select</option>
                    <option value='solo'>Solo QA</option>
                    <option value='2-5'>2–5 members</option>
                    <option value='6-10'>6–10 members</option>
                    <option value='10+'>{'10+ members'}</option>
                  </select>
                </div>
                <div className='space-y-2'>
                  <label className='text-sm text-slate-200'>
                    Primary automation framework
                  </label>
                  <select
                    value={data.primaryTool}
                    onChange={(e) => update('primaryTool', e.target.value)}
                    className='w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500'
                  >
                    <option value=''>Select</option>
                    <option value='playwright'>Playwright</option>
                    <option value='selenium'>Selenium / WebDriver</option>
                    <option value='cypress'>Cypress</option>
                    <option value='robot'>Robot Framework</option>
                    <option value='other'>Other / mixed</option>
                  </select>
                </div>
              </div>
              <p className='text-xs text-slate-500'>
                This doesn&apos;t affect limits – it just helps us show relevant examples.
              </p>
            </div>
          )}

          {currentStep.id === 'stories' && (
            <div className='space-y-4'>
              <h2 className='text-xl font-semibold'>Your first story</h2>
              <div className='space-y-3'>
                <div className='space-y-2'>
                  <label className='text-sm text-slate-200'>
                    Story title
                  </label>
                  <input
                    type='text'
                    value={data.firstStoryTitle}
                    onChange={(e) => update('firstStoryTitle', e.target.value)}
                    placeholder='E.g. User completes checkout successfully'
                    className='w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500'
                  />
                </div>
                <div className='space-y-2'>
                  <label className='text-sm text-slate-200'>
                    Goal / acceptance criteria
                  </label>
                  <textarea
                    value={data.firstStoryGoal}
                    onChange={(e) => update('firstStoryGoal', e.target.value)}
                    rows={4}
                    placeholder='E.g. Given a logged-in user with items in the cart, when they submit payment, then the order is created and confirmation email is sent.'
                    className='w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm'
                  />
                </div>
              </div>
              <p className='text-xs text-slate-500'>
                Later we can use this to auto-generate scenarios and testcases per complexity.
              </p>
            </div>
          )}

          {currentStep.id === 'summary' && (
            <div className='space-y-4'>
              <h2 className='text-xl font-semibold'>Review your setup</h2>
              <p className='text-sm text-slate-300'>
                Here&apos;s what we&apos;ll create for you. You can edit any of this later in the dashboard.
              </p>
              <div className='grid gap-4 md:grid-cols-2'>
                <div className='rounded-xl border border-slate-800 bg-slate-900/70 p-4 space-y-2'>
                  <h3 className='text-sm font-semibold text-slate-100'>
                    Project
                  </h3>
                  <p className='text-sm text-slate-300'>
                    <span className='font-medium'>Name:</span>{' '}
                    {data.projectName || 'Not set'}
                  </p>
                  <p className='text-sm text-slate-300'>
                    <span className='font-medium'>Domain:</span>{' '}
                    {data.projectDomain || 'Not set'}
                  </p>
                </div>
                <div className='rounded-xl border border-slate-800 bg-slate-900/70 p-4 space-y-2'>
                  <h3 className='text-sm font-semibold text-slate-100'>
                    Team & tools
                  </h3>
                  <p className='text-sm text-slate-300'>
                    <span className='font-medium'>Team size:</span>{' '}
                    {data.teamSize || 'Not set'}
                  </p>
                  <p className='text-sm text-slate-300'>
                    <span className='font-medium'>Framework:</span>{' '}
                    {data.primaryTool || 'Not set'}
                  </p>
                </div>
                <div className='rounded-xl border border-slate-800 bg-slate-900/70 p-4 space-y-2 md:col-span-2'>
                  <h3 className='text-sm font-semibold text-slate-100'>
                    First story
                  </h3>
                  <p className='text-sm text-slate-300'>
                    <span className='font-medium'>Title:</span>{' '}
                    {data.firstStoryTitle || 'Not set'}
                  </p>
                  <p className='text-sm text-slate-300'>
                    <span className='font-medium'>Goal:</span>{' '}
                    {data.firstStoryGoal || 'Not set'}
                  </p>
                </div>
              </div>
              <p className='text-xs text-slate-500'>
                When you click Finish, we&apos;ll set up your workspace and take you to the dashboard.
              </p>
            </div>
          )}
        </div>

        {/* Footer buttons */}
        <footer className='flex items-center justify-between gap-4'>
          <button
            type='button'
            onClick={back}
            disabled={currentIndex === 0}
            className={`px-3 py-2 rounded-lg text-sm border border-slate-700
              ${currentIndex === 0 ? 'opacity-40 cursor-not-allowed' : 'hover:bg-slate-800'}
            `}
          >
            Back
          </button>

          <div className='flex items-center gap-3'>
            {!isLast && (
              <button
                type='button'
                onClick={next}
                className='px-4 py-2 rounded-lg text-sm bg-indigo-600 hover:bg-indigo-500 text-white font-medium'
              >
                Next
              </button>
            )}
            {isLast && (
              <button
                type='button'
                onClick={finish}
                disabled={saving}
                className='px-4 py-2 rounded-lg text-sm bg-emerald-600 hover:bg-emerald-500 text-white font-medium disabled:opacity-60'
              >
                {saving ? 'Finishing...' : 'Finish & go to dashboard'}
              </button>
            )}
          </div>
        </footer>
      </div>
    </div>
  );
}
