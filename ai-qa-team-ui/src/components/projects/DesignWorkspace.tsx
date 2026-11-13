import type { ReactNode } from "react";
import { Search } from "lucide-react";

export function DesignStats({ items }: { items: { label: string; value: number | string }[] }) {
  return <div className="design-stats" aria-label="Current view summary">{items.map(item =>
    <div key={item.label}><span>{item.label}</span><strong>{item.value}</strong></div>)}</div>;
}

export function DesignToolbar({ query, onQuery, placeholder, children }: {
  query: string; onQuery: (value: string) => void; placeholder: string; children?: ReactNode;
}) {
  return <div className="design-toolbar"><label className="design-search"><Search size={17} aria-hidden="true" />
    <span className="sr-only">{placeholder}</span><input type="search" value={query} placeholder={placeholder} onChange={event => onQuery(event.target.value)} />
  </label>{children}</div>;
}

export function DesignState({ title, children, error = false }: { title: string; children?: ReactNode; error?: boolean }) {
  return <div className={`design-state${error ? " design-state-error" : ""}`} role={error ? "alert" : "status"}>
    <strong>{title}</strong>{children && <div>{children}</div>}
  </div>;
}

export function designStatusLabel(value?: string | null): string {
  const key = (value || "draft").toLowerCase().replaceAll(" ", "_");
  const labels: Record<string, string> = { draft: "Draft", in_review: "In Review", pending_review: "In Review", pending_approval: "In Review", pending: "In Review", approved_version_available: "Approved", approved: "Approved", review_required: "Needs Review", needs_review: "Needs Review", rejected: "Rejected", archived: "Archived" };
  return labels[key] || key.split("_").map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(" ");
}

export function DesignBadge({ children, tone }: { children: ReactNode; tone?: "neutral" | "positive" | "warning" | "negative" }) {
  const key = typeof children === "string" ? children.toLowerCase().replaceAll(" ", "_") : "";
  const inferred = ["approved", "pass", "passed", "completed"].includes(key) ? "positive" : ["fail", "failed", "rejected"].includes(key) ? "negative" : ["in_review", "pending_approval", "blocked", "needs_review", "in_progress", "running", "queued"].includes(key) ? "warning" : "neutral";
  return <span className={`design-badge design-badge-${tone || inferred}`}>{children}</span>;
}
