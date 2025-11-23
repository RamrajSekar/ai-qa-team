import React from 'react';

/* ---------------------------------------------------
 * Floating “Meet Your AI Squad” panel
 * --------------------------------------------------- */
const AgentPanel = () => (
  <aside className='hidden lg:block lg:w-72 sticky top-28 self-start ml-8'>
    <div className='qs-card p-6'>
      <h3 className='text-lg font-bold text-slate-900 dark:text-slate-50'>Meet your AI Squad</h3>
      <p className='text-sm text-slate-600 dark:text-slate-300 mt-2'>
        Four specialized agents power each stage of your testing workflow. You can rename them to match your
        team’s style.
      </p>

      <ul className='mt-6 space-y-4 text-sm'>
        <li className='flex items-start'>
          <div className='h-3 w-3 mt-1 rounded-full bg-blue-500 mr-3' />
          <div>
            <strong className='text-slate-900 dark:text-slate-50'>Recorder Agent</strong>
            <p className='text-xs text-slate-600 dark:text-slate-300'>
              Captures real user interactions and records step-by-step flows.
            </p>
          </div>
        </li>

        <li className='flex items-start'>
          <div className='h-3 w-3 mt-1 rounded-full bg-green-500 mr-3' />
          <div>
            <strong className='text-slate-900 dark:text-slate-50'>Scenario Builder</strong>
            <p className='text-xs text-slate-600 dark:text-slate-300'>
              Converts recordings or stories into draft scenarios using AI.
            </p>
          </div>
        </li>

        <li className='flex items-start'>
          <div className='h-3 w-3 mt-1 rounded-full bg-amber-500 mr-3' />
          <div>
            <strong className='text-slate-900 dark:text-slate-50'>Test Generator</strong>
            <p className='text-xs text-slate-600 dark:text-slate-300'>
              Turns approved scenarios into structured, runnable test cases.
            </p>
          </div>
        </li>

        <li className='flex items-start'>
          <div className='h-3 w-3 mt-1 rounded-full bg-violet-600 mr-3' />
          <div>
            <strong className='text-slate-900 dark:text-slate-50'>Executor Agent</strong>
            <p className='text-xs text-slate-600 dark:text-slate-300'>
              Executes tests in the cloud and streams live logs back to QA Squad.
            </p>
          </div>
        </li>
      </ul>
    </div>
  </aside>
);

/* ---------------------------------------------------
 * HERO ICONS
 * --------------------------------------------------- */
const CloudIcon = () => (
  <svg
    width='18'
    height='18'
    viewBox='0 0 24 24'
    fill='none'
    stroke='currentColor'
    strokeWidth='2'
    strokeLinecap='round'
    strokeLinejoin='round'
    className='text-violet-600 dark:text-violet-400'
  >
    <path d='M17.5 19a4.5 4.5 0 0 0 0-9h-1.26A8 8 0 1 0 4 15' />
  </svg>
);

const LaptopIcon = () => (
  <svg
    width='18'
    height='18'
    viewBox='0 0 24 24'
    fill='none'
    stroke='currentColor'
    strokeWidth='2'
    strokeLinecap='round'
    strokeLinejoin='round'
    className='text-slate-400 dark:text-slate-500'
  >
    <path d='M3 3h18v14H3z' />
    <path d='M2 21h20' />
  </svg>
);

/* ---------------------------------------------------
 * MAIN PAGE
 * --------------------------------------------------- */
const HomePage = () => {
  const currentYear = new Date().getFullYear();

  return (
    <main className='min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100'>
      {/* NAVBAR */}
      <header className='border-b border-slate-200 bg-white/80 backdrop-blur sticky top-0 z-20 dark:bg-slate-900/80 dark:border-slate-800'>
        <div className='qs-container flex items-center justify-between py-4'>
          <div className='flex items-center gap-2'>
            <div className='h-8 w-8 rounded-xl bg-gradient-to-tr from-violet-600 to-indigo-500 shadow-lg' />
            <span className='text-lg font-semibold tracking-tight'>QA Squad</span>
          </div>

          <nav className='hidden md:flex items-center gap-6 text-sm text-slate-600 dark:text-slate-300'>
            <a href='#how-it-works' className='hover:text-slate-900 dark:hover:text-slate-50 transition'>
              Workflow
            </a>
            <a href='#features' className='hover:text-slate-900 dark:hover:text-slate-50 transition'>
              Features
            </a>
            <a href='#pricing' className='hover:text-slate-900 dark:hover:text-slate-50 transition'>
              Pricing
            </a>
          </nav>

          <div className='flex items-center gap-3'>
            <a
              href='/login'
              className='hidden md:inline-block text-sm font-medium text-slate-700 hover:text-slate-900 dark:text-slate-300 dark:hover:text-slate-50 transition'
            >
              Log in
            </a>
            <a
              href='/signup'
              className='rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700 shadow-md transition dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200'
            >
              Get started
            </a>
          </div>
        </div>
      </header>

      {/* HERO */}
      <section className='border-b border-slate-200 bg-gradient-to-b from-white to-slate-50 dark:from-slate-950 dark:to-slate-900'>
        <div className='qs-container flex flex-col md:flex-row items-center gap-12 py-20 md:py-28'>
          {/* Left */}
          <div className='flex-1'>
            <span className='qs-pill'>
              Recording → Scenario → Review → Test Generation
            </span>

            <h1 className='mt-6 text-4xl md:text-5xl lg:text-6xl font-semibold tracking-tight'>
              Your AI-powered
              <span className='block bg-gradient-to-r from-violet-600 to-indigo-500 bg-clip-text text-transparent'>
                test automation companion.
              </span>
            </h1>

            <p className='mt-5 max-w-xl text-base md:text-lg text-slate-600 dark:text-slate-300'>
              Capture real user flows, let AI draft scenarios, keep humans in control of approvals, and generate
              runnable tests in minutes.
            </p>

            {/* Cloud vs Local toggle (non-functional, marketing only) */}
            <div className='mt-6 inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-2 py-2 shadow-md dark:border-slate-700 dark:bg-slate-900'>
              <div className='flex items-center gap-2 rounded-lg bg-violet-50 px-3 py-1 text-xs font-semibold text-violet-700 border border-violet-200 shadow-sm dark:bg-violet-500/10 dark:text-violet-200 dark:border-violet-500/40'>
                <CloudIcon />
                <span>Cloud (default)</span>
              </div>
              <div className='flex items-center gap-2 rounded-lg bg-slate-100 px-3 py-1 text-xs font-medium text-slate-400 border border-slate-200 cursor-not-allowed dark:bg-slate-800 dark:border-slate-700 dark:text-slate-500'>
                <LaptopIcon />
                <span>Local (coming soon)</span>
              </div>
            </div>

            <div className='mt-8 flex flex-wrap items-center gap-4'>
              <a
                href='/signup'
                className='rounded-xl bg-slate-900 px-6 py-3 text-base font-semibold text-white hover:bg-slate-700 transition shadow-lg hover:shadow-xl transform hover:scale-[1.01] active:scale-[0.99] dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200'
              >
                Get started free
              </a>
              <a
                href='/demo'
                className='rounded-xl border border-slate-200 bg-white px-6 py-3 text-base font-semibold text-slate-800 hover:border-slate-300 hover:bg-slate-50 transition shadow-md dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:hover:bg-slate-800'
              >
                Request demo
              </a>
            </div>
          </div>

          {/* Right: Hero preview */}
          <div className='flex-1'>
            <div className='qs-card qs-hover-card p-5 space-y-4'>
              {/* Recording */}
              <div className='rounded-lg bg-slate-50 p-3 border border-slate-100 dark:bg-slate-900 dark:border-slate-700'>
                <p className='text-xs font-semibold text-slate-700 dark:text-slate-200 mb-1'>
                  Recording (12 steps captured)
                </p>
                <pre className='text-[11px] text-slate-600 dark:text-slate-300 whitespace-pre-wrap leading-relaxed'>
{`• Click "Login"
• Type username
• Type password
• Click "Sign In"
• Navigate to dashboard
• View execution summary`}
                </pre>
              </div>

              {/* Story */}
              <div className='rounded-lg bg-white p-3 border border-slate-100 dark:bg-slate-900 dark:border-slate-700'>
                <p className='text-xs font-semibold text-slate-700 dark:text-slate-200 mb-1'>Extracted Story</p>
                <p className='text-[11px] text-slate-600 dark:text-slate-300'>
                  As a user, I should be able to log in and view my dashboard with today&apos;s execution summary.
                </p>
              </div>

              {/* Scenario */}
              <div className='rounded-lg bg-slate-50 p-3 border border-slate-100 dark:bg-slate-900 dark:border-slate-700'>
                <div className='flex justify-between items-center'>
                  <p className='text-xs font-semibold text-slate-700 dark:text-slate-200'>AI Scenario Draft</p>
                  <span className='rounded-full bg-amber-50 text-amber-700 border border-amber-200 px-2 py-0.5 text-[10px] font-semibold dark:bg-amber-500/10 dark:text-amber-200 dark:border-amber-500/40'>
                    Needs review
                  </span>
                </div>
                <p className='text-[11px] text-slate-600 dark:text-slate-300 mt-1'>
                  Scenario: Login with valid credentials and verify the dashboard summary widget is visible.
                </p>
              </div>

              {/* Generated test */}
              <div className='rounded-xl bg-slate-900 p-4 font-mono text-[11px] text-slate-100 shadow-inner dark:bg-black'>
                <p className='text-violet-400 font-semibold mb-2'># Generated Test (preview)</p>
                <pre className='whitespace-pre leading-relaxed overflow-x-auto'>
{`Step 1: Open application URL
Step 2: Enter username
Step 3: Enter password
Step 4: Click "Sign in"
Step 5: Assert dashboard is visible
Step 6: Verify execution summary widget`}
                </pre>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* WORKFLOW + AGENT PANEL */}
      <section id='how-it-works' className='border-b border-slate-200 bg-white dark:bg-slate-950 dark:border-slate-800'>
        <div className='qs-container py-16 md:py-20 flex'>
          <div className='flex-1'>
            <h2 className='text-3xl md:text-4xl font-bold text-slate-900 dark:text-slate-50'>
              How QA Squad fits into your workflow.
            </h2>
            <p className='mt-3 max-w-2xl text-base text-slate-600 dark:text-slate-300'>
              From captured user journeys to automated cloud executions — with human approvals at every critical step.
            </p>

            <div className='mt-12 grid gap-8 md:grid-cols-2'>
              <div className='rounded-2xl border border-slate-200 bg-slate-50 p-6 shadow-md hover:shadow-lg transition dark:border-slate-700 dark:bg-slate-900'>
                <span className='text-sm font-bold uppercase tracking-wide text-violet-600 dark:text-violet-400'>
                  01. Capture
                </span>
                <h3 className='mt-3 text-xl font-semibold text-slate-900 dark:text-slate-50'>
                  Record user flows
                </h3>
                <p className='mt-2 text-sm text-slate-600 dark:text-slate-300'>
                  Use the recorder to capture authentic user journeys. QA Squad turns them into structured steps and stories.
                </p>
              </div>

              <div className='rounded-2xl border border-slate-200 bg-slate-50 p-6 shadow-md hover:shadow-lg transition dark:border-slate-700 dark:bg-slate-900'>
                <span className='text-sm font-bold uppercase tracking-wide text-violet-600 dark:text-violet-400'>
                  02. Generate
                </span>
                <h3 className='mt-3 text-xl font-semibold text-slate-900 dark:text-slate-50'>
                  AI Scenario generation
                </h3>
                <p className='mt-2 text-sm text-slate-600 dark:text-slate-300'>
                  AI transforms recordings or stories into candidate scenarios. You get drafts ready for review — no manual typing.
                </p>
              </div>

              <div className='rounded-2xl border border-slate-200 bg-slate-50 p-6 shadow-md hover:shadow-lg transition dark:border-slate-700 dark:bg-slate-900'>
                <span className='text-sm font-bold uppercase tracking-wide text-violet-600 dark:text-violet-400'>
                  03. Review
                </span>
                <h3 className='mt-3 text-xl font-semibold text-slate-900 dark:text-slate-50'>
                  Approve or deny scenarios
                </h3>
                <p className='mt-2 text-sm text-slate-600 dark:text-slate-300'>
                  QA engineers remain the gatekeepers. Only approved scenarios are eligible for test generation.
                </p>
              </div>

              <div className='rounded-2xl border border-slate-200 bg-slate-50 p-6 shadow-md hover:shadow-lg transition dark:border-slate-700 dark:bg-slate-900'>
                <span className='text-sm font-bold uppercase tracking-wide text-violet-600 dark:text-violet-400'>
                  04. Automate
                </span>
                <h3 className='mt-3 text-xl font-semibold text-slate-900 dark:text-slate-50'>
                  Generate tests & execute
                </h3>
                <p className='mt-2 text-sm text-slate-600 dark:text-slate-300'>
                  Approved scenarios become runnable test cases you can execute in the cloud. Local runners are next on the roadmap.
                </p>
              </div>
            </div>
          </div>

          <AgentPanel />
        </div>
      </section>

      {/* FEATURES */}
      <section id='features' className='border-b border-slate-200 bg-slate-50 dark:bg-slate-900 dark:border-slate-800'>
        <div className='qs-container py-16 md:py-20'>
          <h2 className='text-3xl md:text-4xl font-bold text-slate-900 dark:text-slate-50'>
            Core capabilities in the MVP.
          </h2>
          <p className='mt-3 max-w-2xl text-base text-slate-600 dark:text-slate-300'>
            Start with a lean, reliable base that grows with your team and workflows.
          </p>

          <div className='mt-12 grid gap-8 md:grid-cols-2'>
            <div className='qs-card p-6'>
              <h3 className='text-xl font-semibold text-slate-900 dark:text-slate-50'>
                AI Test Generator (human-gated)
              </h3>
              <p className='mt-2 text-sm text-slate-600 dark:text-slate-300'>
                Convert approved scenarios into structured, repeatable test cases. Humans stay in control of what gets automated.
              </p>
            </div>

            <div className='qs-card p-6'>
              <h3 className='text-xl font-semibold text-slate-900 dark:text-slate-50'>Cloud execution engine</h3>
              <p className='mt-2 text-sm text-slate-600 dark:text-slate-300'>
                Execute tests in QA Squad&apos;s managed environment — no local setup or infra required.
                <br />
                <span className='text-violet-600 dark:text-violet-300 font-medium'>
                  Local runner support is on the roadmap.
                </span>
              </p>
            </div>

            <div className='qs-card p-6'>
              <h3 className='text-xl font-semibold text-slate-900 dark:text-slate-50'>
                Scenario & test management
              </h3>
              <p className='mt-2 text-sm text-slate-600 dark:text-slate-300'>
                Manage Stories, Scenarios, approvals, and test cases in one place. Always know what&apos;s drafted, under review, and automated.
              </p>
            </div>

            <div className='qs-card p-6'>
              <h3 className='text-xl font-semibold text-slate-900 dark:text-slate-50'>Live execution logs</h3>
              <p className='mt-2 text-sm text-slate-600 dark:text-slate-300'>
                See step-by-step execution output for every run, making it faster to spot issues and confirm coverage.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ROADMAP (Card row) */}
      <section className='border-b border-slate-200 bg-white dark:bg-slate-950 dark:border-slate-800'>
        <div className='qs-container py-16 md:py-20'>
          <h2 className='text-3xl md:text-4xl font-bold text-slate-900 dark:text-slate-50'>On the roadmap.</h2>
          <p className='mt-3 max-w-2xl text-base text-slate-600 dark:text-slate-300'>
            After the MVP, we&apos;re focused on deeper coverage, integrations, and resilience.
          </p>

          <div className='mt-12 grid gap-8 md:grid-cols-3'>
            <div className='p-6 rounded-2xl bg-slate-50 border border-slate-200 shadow-md dark:bg-slate-900 dark:border-slate-700'>
              <h4 className='text-lg font-semibold text-slate-900 dark:text-slate-50'>Local execution runner</h4>
              <p className='text-sm text-slate-600 dark:text-slate-300 mt-1'>
                Run QA Squad test cases on your own machine or CI runners, with results synced back.
              </p>
            </div>

            <div className='p-6 rounded-2xl bg-slate-50 border border-slate-200 shadow-md dark:bg-slate-900 dark:border-slate-700'>
              <h4 className='text-lg font-semibold text-slate-900 dark:text-slate-50'>CI/CD integrations</h4>
              <p className='text-sm text-slate-600 dark:text-slate-300 mt-1'>
                GitHub Actions, GitLab CI, and Bitbucket pipelines integration.
              </p>
            </div>

            <div className='p-6 rounded-2xl bg-slate-50 border border-slate-200 shadow-md dark:bg-slate-900 dark:border-slate-700'>
              <h4 className='text-lg font-semibold text-slate-900 dark:text-slate-50'>Multi-browser execution</h4>
              <p className='text-sm text-slate-600 dark:text-slate-300 mt-1'>
                Extend coverage with Firefox and WebKit, in addition to Chromium.
              </p>
            </div>

            <div className='p-6 rounded-2xl bg-slate-50 border border-slate-200 shadow-md dark:bg-slate-900 dark:border-slate-700'>
              <h4 className='text-lg font-semibold text-slate-900 dark:text-slate-50'>AI self-healing tests</h4>
              <p className='text-sm text-slate-600 dark:text-slate-300 mt-1'>
                Automatically adapt brittle locators when the DOM changes to keep tests running.
              </p>
            </div>

            <div className='p-6 rounded-2xl bg-slate-50 border border-slate-200 shadow-md dark:bg-slate-900 dark:border-slate-700'>
              <h4 className='text-lg font-semibold text-slate-900 dark:text-slate-50'>Visual snapshots</h4>
              <p className='text-sm text-slate-600 dark:text-slate-300 mt-1'>
                Capture screenshots and traces for rich failure analysis.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* PRICING (matches PLAN_LIMITS) */}
      <section id='pricing' className='border-b border-slate-200 bg-slate-50 dark:bg-slate-900 dark:border-slate-800'>
        <div className='qs-container py-16 md:py-20'>
          <h2 className='text-3xl md:text-4xl font-bold text-slate-900 dark:text-slate-50'>
            Start small, grow with your team.
          </h2>
          <p className='mt-3 text-base text-slate-600 dark:text-slate-300 max-w-xl'>
            Usage-based limits that match your team&apos;s stage. Upgrade when you&apos;re ready.
          </p>

          <div className='mt-12 grid gap-8 md:grid-cols-3'>
            {/* Free */}
            <div className='qs-card flex flex-col p-6'>
              <h3 className='text-xl font-semibold text-slate-900 dark:text-slate-50'>Free</h3>
              <p className='text-sm text-slate-600 dark:text-slate-300 mt-1'>For individuals evaluating QA Squad.</p>
              <p className='mt-6 text-4xl font-bold text-slate-900 dark:text-slate-50'>$0</p>
              <p className='text-sm text-slate-500 dark:text-slate-400'>forever</p>
              <ul className='mt-6 space-y-2 text-sm text-slate-700 dark:text-slate-300 flex-1'>
                <li>1 Project</li>
                <li>5 User Stories</li>
                <li>10 Scenarios</li>
                <li>20 Executions / month</li>
                <li>1 Team Member</li>
                <li>3 AI Generations</li>
                <li>10 Basic Testcases</li>
                <li>No Medium or Advanced Tests</li>
              </ul>
              <a
                href='/signup?plan=free'
                className='mt-6 rounded-xl bg-white border border-slate-200 px-4 py-3 text-center text-sm font-semibold text-slate-900 hover:bg-slate-50 shadow-md transition dark:bg-slate-900 dark:border-slate-700 dark:text-slate-100 dark:hover:bg-slate-800'
              >
                Get started free
              </a>
            </div>

            {/* Pro */}
            <div className='relative qs-card flex flex-col p-6 border-4 border-violet-600 dark:border-violet-500 shadow-2xl scale-[1.02]'>
              <span className='absolute -top-3 right-5 bg-violet-600 text-white text-xs font-bold px-3 py-1 rounded-full shadow-md'>
                Most popular
              </span>
              <h3 className='text-xl font-semibold text-slate-900 dark:text-slate-50'>Pro</h3>
              <p className='text-sm text-slate-600 dark:text-slate-300 mt-1'>For growing QA teams.</p>
              <p className='mt-6 text-4xl font-bold text-slate-900 dark:text-slate-50'>$49</p>
              <p className='text-sm text-slate-500 dark:text-slate-400'>per month</p>
              <ul className='mt-6 space-y-2 text-sm text-slate-700 dark:text-slate-300 flex-1'>
                <li>10 Projects</li>
                <li>100 User Stories</li>
                <li>200 Scenarios</li>
                <li>1,000 Executions / month</li>
                <li>5 Team Members</li>
                <li>50 AI Generations</li>
                <li>500 Basic Testcases</li>
                <li>200 Medium Testcases</li>
                <li>100 Advanced Testcases</li>
              </ul>
              <a
                href='/signup?plan=pro'
                className='mt-6 rounded-xl bg-violet-600 px-4 py-3 text-center text-sm font-semibold text-white hover:bg-violet-700 shadow-lg transition dark:bg-violet-500 dark:hover:bg-violet-600'
              >
                Choose Pro
              </a>
            </div>

            {/* Enterprise */}
            <div className='qs-card flex flex-col p-6'>
              <h3 className='text-xl font-semibold text-slate-900 dark:text-slate-50'>Enterprise</h3>
              <p className='text-sm text-slate-600 dark:text-slate-300 mt-1'>For organizations at scale.</p>
              <p className='mt-6 text-4xl font-bold text-slate-900 dark:text-slate-50'>Let&apos;s talk</p>
              <p className='text-sm text-slate-500 dark:text-slate-400'>custom pricing</p>
              <ul className='mt-6 space-y-2 text-sm text-slate-700 dark:text-slate-300 flex-1'>
                <li>1,000+ Projects</li>
                <li>1,000 User Stories</li>
                <li>2,000 Scenarios</li>
                <li>10,000 Executions / month</li>
                <li>20 Team Members</li>
                <li>Unlimited AI Generations</li>
                <li>Unlimited Basic/Medium/Advanced Tests</li>
                <li>Private deployment options</li>
              </ul>
              <a
                href='/contact'
                className='mt-6 rounded-xl bg-white border border-slate-200 px-4 py-3 text-center text-sm font-semibold text-slate-900 hover:bg-slate-50 shadow-md transition dark:bg-slate-900 dark:border-slate-700 dark:text-slate-100 dark:hover:bg-slate-800'
              >
                Contact sales
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer className='bg-white dark:bg-slate-950 py-10 border-t border-slate-200 dark:border-slate-800'>
        <div className='qs-container flex flex-col md:flex-row items-center justify-between gap-3 text-xs text-slate-500 dark:text-slate-400'>
          <p>
            © {currentYear} QA Squad, Inc. All rights reserved.{' '}
            <span className='text-slate-400 dark:text-slate-500'>Built with quality and speed.</span>
          </p>
          <div className='flex gap-4'>
            <a href='/terms' className='hover:text-slate-700 dark:hover:text-slate-200'>
              Terms of Service
            </a>
            <a href='/privacy' className='hover:text-slate-700 dark:hover:text-slate-200'>
              Privacy Policy
            </a>
          </div>
        </div>
      </footer>
    </main>
  );
};

export default HomePage;
