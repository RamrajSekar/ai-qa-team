'use client';

import ThemeToggle from '@/components/ThemeToggle';

const CloudIcon = () => (
  <svg
    width="18"
    height="18"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    className="text-violet-500"
  >
    <path d="M17.5 19a4.5 4.5 0 0 0 0-9h-1.26A8 8 0 1 0 4 15" />
  </svg>
);

const LaptopIcon = () => (
  <svg
    width="18"
    height="18"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    className="text-[var(--qs-text-soft)]"
  >
    <path d="M3 4h18v12H3z" />
    <path d="M2 20h20" />
  </svg>
);

export default function Hero() {
  return (
    <section className="border-b border-[var(--qs-border)] bg-gradient-to-b from-[var(--qs-bg)] to-[var(--qs-bg-soft)]">
      {/* NAVBAR */}
      <header className="sticky top-0 z-30 border-b border-[var(--qs-border)] bg-[var(--qs-bg)]/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 md:px-6">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-2xl bg-gradient-to-tr from-violet-600 to-indigo-500 shadow-lg" />
            <span className="text-lg font-semibold tracking-tight">QA Squad</span>
          </div>

          <nav className="hidden items-center gap-6 text-sm text-[var(--qs-text-soft)] md:flex">
            <a href="#how-it-works" className="hover:text-[var(--qs-text)] transition">
              Workflow
            </a>
            <a href="#features" className="hover:text-[var(--qs-text)] transition">
              Features
            </a>
            <a href="#pricing" className="hover:text-[var(--qs-text)] transition">
              Pricing
            </a>
          </nav>

          <div className="flex items-center gap-3">
            <ThemeToggle />
            <a
              href="/login"
              className="hidden text-sm font-medium text-[var(--qs-text-soft)] hover:text-[var(--qs-text)] md:inline-block"
            >
              Log in
            </a>
            <a
              href="/signup"
              className="rounded-xl bg-[var(--qs-text)] px-4 py-2 text-sm font-semibold text-[var(--qs-bg)] shadow hover:opacity-90 transition"
            >
              Get started
            </a>
          </div>
        </div>
      </header>

      {/* HERO CONTENT */}
      <div className="mx-auto flex max-w-6xl flex-col gap-12 px-4 py-14 md:flex-row md:items-center md:px-6 md:py-20">
        {/* LEFT */}
        <div className="flex-1 max-w-xl">
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--qs-text-soft)]">
            Recording → Scenario → Review → Test Generation
          </p>

          <h1 className="mt-4 text-4xl font-semibold tracking-tight text-[var(--qs-text)] md:text-5xl lg:text-6xl">
            Your AI-powered
            <span className="block bg-gradient-to-r from-violet-500 to-indigo-500 bg-clip-text text-transparent">
              test automation companion.
            </span>
          </h1>

          <p className="mt-5 text-base text-[var(--qs-text-soft)] md:text-lg">
            Capture real user flows, let AI draft scenarios, keep humans in control of approvals, and
            generate runnable tests in minutes.
          </p>

          {/* Cloud vs Local toggle */}
          <div className="mt-6 inline-flex items-center gap-2 rounded-2xl border border-[var(--qs-border)] bg-[var(--qs-bg)] p-1 shadow-sm">
            <div className="inline-flex items-center gap-2 rounded-xl border border-violet-200 bg-violet-50 px-3 py-1 text-xs font-semibold text-violet-700">
              <CloudIcon />
              <span>Cloud (default)</span>
            </div>
            <div className="inline-flex items-center gap-2 rounded-xl border border-[var(--qs-border)] bg-[var(--qs-bg-soft)] px-3 py-1 text-xs font-medium text-[var(--qs-text-soft)] opacity-70">
              <LaptopIcon />
              <span>Local (coming soon)</span>
            </div>
          </div>

          <div className="mt-7 flex flex-wrap items-center gap-4">
            <a
              href="/signup"
              className="rounded-xl bg-[var(--qs-text)] px-6 py-3 text-sm font-semibold text-[var(--qs-bg)] shadow-lg hover:opacity-90 transition"
            >
              Get started free
            </a>
            <a
              href="/demo"
              className="rounded-xl border border-[var(--qs-border)] bg-[var(--qs-bg)] px-6 py-3 text-sm font-semibold text-[var(--qs-text)] shadow-sm hover:bg-[var(--qs-bg-soft)] transition"
            >
              Request demo
            </a>
          </div>
        </div>

        {/* RIGHT – compact stacked cards */}
        <div className="flex-1">
          <div className="space-y-4">
            {/* Recording */}
            <div className="rounded-2xl border border-[var(--qs-border)] bg-[var(--qs-bg-soft)] p-4 shadow-sm">
              <div className="mb-2 flex items-center justify-between text-xs text-[var(--qs-text-soft)]">
                <span>Recording · 12 steps captured</span>
                <span className="rounded-full border border-blue-200 bg-blue-50 px-2 py-0.5 text-[10px] font-semibold text-blue-700">
                  Recorder agent
                </span>
              </div>
              <ul className="list-disc pl-5 text-[11px] text-[var(--qs-text-soft)] leading-relaxed">
                <li>Click &quot;Login&quot;</li>
                <li>Type username</li>
                <li>Type password</li>
                <li>Click &quot;Sign in&quot;</li>
                <li>Navigate to dashboard</li>
                <li>View execution summary</li>
              </ul>
            </div>

            {/* Story */}
            <div className="rounded-2xl border border-[var(--qs-border)] bg-[var(--qs-bg)] p-4 shadow-sm">
              <div className="mb-1 flex items-center justify-between text-xs text-[var(--qs-text-soft)]">
                <span>Extracted Story</span>
                <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-700">
                  Scenario builder
                </span>
              </div>
              <p className="text-[11px] text-[var(--qs-text-soft)]">
                As a user, I should be able to log in and view my dashboard with today&apos;s execution
                summary.
              </p>
            </div>

            {/* Scenario */}
            <div className="rounded-2xl border border-[var(--qs-border)] bg-[var(--qs-bg)] p-4 shadow-sm">
              <div className="mb-1 flex items-center justify-between text-xs text-[var(--qs-text-soft)]">
                <span>AI Scenario Draft</span>
                <span className="rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[10px] font-semibold text-amber-700">
                  Needs review
                </span>
              </div>
              <p className="text-[11px] text-[var(--qs-text-soft)]">
                Scenario: Login with valid credentials and verify that the dashboard execution summary widget
                is visible.
              </p>
            </div>

            {/* Test preview */}
            <div className="rounded-2xl border border-slate-900 bg-slate-950 p-4 font-mono text-[11px] text-slate-100 shadow-lg">
              <div className="mb-2 flex items-center justify-between text-[10px] text-slate-400">
                <span># Generated Test (preview)</span>
                <span className="rounded-full border border-emerald-500/40 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-300">
                  Test generator
                </span>
              </div>
              <pre className="whitespace-pre-wrap leading-relaxed">
{`Step 1: Open application URL
Step 2: Enter username
Step 3: Enter password
Step 4: Click "Sign in"
Step 5: Assert dashboard is visible
Step 6: Verify execution summary widget`}
              </pre>
              <div className="mt-3 flex items-center justify-between text-[10px] text-slate-400">
                <span>Executor agent ready · Cloud</span>
                <span>~4.5s est. runtime</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
