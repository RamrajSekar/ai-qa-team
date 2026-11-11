"use client";

export default function AgentPanel() {
  return (
    <aside className="mt-10 w-full max-w-xs rounded-2xl border border-[var(--qs-border)] bg-[var(--qs-bg)] p-6 shadow-sm lg:mt-0 lg:w-72">
      <h3 className="text-sm font-semibold text-[var(--qs-text)]">Meet your AI Squad</h3>
      <p className="mt-2 text-xs text-[var(--qs-text-soft)]">
        Four specialized agents power each stage of your testing workflow. Rename them to match your team.
      </p>

      <ul className="mt-5 space-y-3 text-xs text-[var(--qs-text-soft)]">
        <li className="flex items-start gap-2">
          <span className="mt-1 h-2 w-2 rounded-full bg-blue-500" />
          <div>
            <p className="font-semibold text-[var(--qs-text)]">Recorder Agent</p>
            <p>Captures real user interactions and step-by-step flows.</p>
          </div>
        </li>
        <li className="flex items-start gap-2">
          <span className="mt-1 h-2 w-2 rounded-full bg-emerald-500" />
          <div>
            <p className="font-semibold text-[var(--qs-text)]">Scenario Builder</p>
            <p>Converts recordings or stories into clear, testable scenarios.</p>
          </div>
        </li>
        <li className="flex items-start gap-2">
          <span className="mt-1 h-2 w-2 rounded-full bg-amber-500" />
          <div>
            <p className="font-semibold text-[var(--qs-text)]">Test Generator</p>
            <p>Turns approved scenarios into structured, runnable test cases.</p>
          </div>
        </li>
        <li className="flex items-start gap-2">
          <span className="mt-1 h-2 w-2 rounded-full bg-violet-500" />
          <div>
            <p className="font-semibold text-[var(--qs-text)]">Executor Agent</p>
            <p>Executes tests in the cloud and streams logs back to QA Squad.</p>
          </div>
        </li>
      </ul>
    </aside>
  );
}
