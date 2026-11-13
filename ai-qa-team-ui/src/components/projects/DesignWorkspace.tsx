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

export function DesignBadge({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "positive" | "warning" }) {
  return <span className={`design-badge design-badge-${tone}`}>{children}</span>;
}
