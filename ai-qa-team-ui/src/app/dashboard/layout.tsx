import ThemeToggle from "@/components/ThemeToggle";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      
      {/* SIDEBAR */}
      <aside className="w-64 border-r border-[var(--qs-border)] bg-[var(--qs-bg-soft)] p-6">
        <h2 className="text-xl font-semibold mb-6">QA Squad</h2>

        <nav className="space-y-2 text-sm">
          <a className="block px-3 py-2 rounded-lg hover:bg-[var(--qs-bg)]" href="/dashboard">
            Overview
          </a>
          <a className="block px-3 py-2 rounded-lg hover:bg-[var(--qs-bg)]" href="/dashboard/projects">
            Projects
          </a>
          <a className="block px-3 py-2 rounded-lg hover:bg-[var(--qs-bg)]" href="/dashboard/stories">
            Stories
          </a>
          <a className="block px-3 py-2 rounded-lg hover:bg-[var(--qs-bg)]" href="/dashboard/scenarios">
            Scenarios
          </a>
          <a className="block px-3 py-2 rounded-lg hover:bg-[var(--qs-bg)]" href="/dashboard/executions">
            Executions
          </a>
          <a className="block px-3 py-2 rounded-lg hover:bg-[var(--qs-bg)]" href="/dashboard/settings">
            Settings
          </a>
        </nav>
      </aside>

      {/* MAIN */}
      <div className="flex-1 flex flex-col">
        {/* TOPBAR */}
        <header className="border-b border-[var(--qs-border)] px-6 py-3 flex items-center justify-between bg-[var(--qs-bg)]">
          <h1 className="font-semibold text-lg">Dashboard</h1>

          <div className="flex items-center gap-3">
            <ThemeToggle />
            <div className="h-8 w-8 rounded-full bg-violet-500"></div>
          </div>
        </header>

        {/* CONTENT */}
        <main className="p-6">{children}</main>
      </div>
    </div>
  );
}
