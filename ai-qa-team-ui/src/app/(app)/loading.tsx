export default function WorkspaceLoading() {
  return <div className="space-y-4 p-6" role="status" aria-live="polite">
    <p>Loading page…</p>
    <div className="h-8 w-48 rounded bg-[var(--qs-border)]" aria-hidden="true" />
    <div className="h-40 rounded bg-[var(--qs-border)]" aria-hidden="true" />
  </div>;
}
