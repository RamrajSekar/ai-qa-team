'use client';

import ThemeToggle from '@/components/ThemeToggle';
import AuthTrigger from '@/components/auth/AuthTrigger';

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
            {/* ✅ These open the AuthModal via context, no SSR errors now */}
            <AuthTrigger>Log in</AuthTrigger>
            <AuthTrigger>Sign up</AuthTrigger>
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
            {/* CTA also opens the modal, focused on signup */}
            <AuthTrigger>Get started free</AuthTrigger>
            <a
              href="/demo"
              className="rounded-xl border border-[var(--qs-border)] bg-[var(--qs-bg)] px-6 py-3 text-sm font-semibold text-[var(--qs-text)] shadow-sm hover:bg-[var(--qs-bg-soft)] transition"
            >
              Request demo
            </a>
          </div>
        </div>

        {/* RIGHT – cards, same as you had */}
        {/* ... keep your existing right-hand cards here ... */}
      </div>
    </section>
  );
}
