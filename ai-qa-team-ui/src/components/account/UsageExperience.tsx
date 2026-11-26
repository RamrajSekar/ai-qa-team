"use client";

import { useState } from "react";
import { apiFetch } from "@/utils/api";
import styles from "./SubscriptionUsage.module.css";

export interface AccountUsageExperience {
  billing_attention?: boolean;
  period: {start: string; end: string; timezone: "UTC"; projected: boolean} | null;
  seats: {included: number | null; extra: number; purchasable: false};
  notices: {id: string; metric: string; threshold: 80 | 100; message: string; used: number; limit: number}[];
}

export function resetDate(value: string) {
  return new Intl.DateTimeFormat("en-US", {month: "short", day: "numeric", year: "numeric", timeZone: "UTC"}).format(new Date(value));
}

export default function UsageExperience({experience, onRefresh}: {experience: AccountUsageExperience; onRefresh?: () => void}) {
  const [hidden, setHidden] = useState<string[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState("");
  async function dismiss(id: string) {
    setBusy(id); setError("");
    try {
      const response = await apiFetch(`/account/usage/notices/${encodeURIComponent(id)}/dismiss`, {method: "POST"});
      if (!response.ok) throw new Error("Could not dismiss this notice. Refresh usage and try again.");
      setHidden(current => [...current, id]);
    } catch { setError("Could not dismiss this notice. Refresh usage and try again."); }
    finally { setBusy(null); }
  }
  const notices = experience.notices.filter(notice => !hidden.includes(notice.id));
  return <section className={styles.group} aria-label="Plan and usage updates">
    {experience.billing_attention && <p className="workspace-notice">Billing needs attention. Existing records and manual review remain available. Open View plans to manage billing.</p>}
    {experience.period ? <p className={styles.note}>AI allowance period: {resetDate(experience.period.start)} – {resetDate(experience.period.end)}. Resets {resetDate(experience.period.end)} (UTC).</p> : <p className={styles.note}>AI reset date unavailable.</p>}
    {notices.length > 0 && <ul className={styles.notices} aria-label="Usage notices">{notices.map(notice => <li key={notice.id} className={styles.usageNotice}>
      <div><p>{notice.message}</p><span className={styles.note}>{notice.used.toLocaleString()} / {notice.limit.toLocaleString()} used</span></div>
      <button type="button" className="workspace-button" disabled={busy !== null} aria-label={`Dismiss ${notice.metric} ${notice.threshold}% notice`} onClick={() => void dismiss(notice.id)}>{busy === notice.id ? "Dismissing…" : "Dismiss"}</button>
    </li>)}</ul>}
    {error && <p role="alert" className={styles.warning}>{error}{onRefresh && <button type="button" className="workspace-button" onClick={onRefresh}>Refresh usage</button>}</p>}
  </section>;
}
