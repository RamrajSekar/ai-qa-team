"use client";
import { useFeatures } from "@/components/providers/FeatureFlagsProvider";
import styles from "./SubscriptionUsage.module.css";

export interface AccountSubscription {
  ai_allowance_version?: number | null;
  ai_allowance_migration?: {unknown_units?: number};
  plan: string;
  status: string;
  usage: Record<string, number>;
  limits: Record<string, number | null>;
}

function title(value: string) { return value.split(/[_ -]+/).map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(" "); }

function allowance(subscription: AccountSubscription, key: string): number | null | undefined {
  const limit = subscription.limits[key.replace(/_used$/, "_limit")];
  if (key === "testcases_used" && limit === 0) {
    return ["basic", "medium", "advanced"].reduce((total, tier) => total + (subscription.limits[`testcases_${tier}_limit`] || 0), 0);
  }
  return limit;
}

function Meter({ label, used, limit, compact = false }: { label: string; used: number; limit: number | null | undefined; compact?: boolean }) {
  const bounded = typeof limit === "number" && limit > 0;
  const note = limit === null ? "Unlimited allowance" : limit === undefined ? "Allowance not configured" : used > limit ? "Over limit" : limit === 0 ? "Not included in this plan" : used === limit ? "At limit" : `${limit - used} remaining`;
  return <div className={compact ? styles.compactMeter : styles.meter}>
    <dl className={styles.meterLine}><dt>{label}</dt><dd>{used} / {limit === null ? "Unlimited" : limit ?? "—"}</dd></dl>
    {bounded && <progress className={styles.progress} aria-label={`${label} usage`} value={Math.min(Math.max(used, 0), limit)} max={limit} />}
    <p className={used > (limit ?? Infinity) ? styles.warning : styles.note}>{note}</p>
  </div>;
}

export default function SubscriptionUsage({ subscription }: { subscription: AccountSubscription }) {
  const { enabled } = useFeatures();
  const meter = (label: string, key: string, compact = false) => <Meter label={label} used={subscription.usage[key] ?? 0} limit={allowance(subscription, key)} compact={compact} />;
  return <section className={styles.section} aria-labelledby="subscription-usage-title">
    <header className={styles.header}>
      <div><p className="workspace-eyebrow">Account subscription</p><h2 id="subscription-usage-title">Subscription &amp; usage</h2><p className={styles.description}>One shared allowance for your account’s users and projects.</p></div>
      <dl className={styles.plan}><div><dt>Plan</dt><dd><strong>{title(subscription.plan)}</strong></dd></div><div><dt>Status</dt><dd><strong className={styles.status}>{title(subscription.status)}</strong></dd></div></dl>
    </header>

    {subscription.ai_allowance_version === 1 ? <section className={styles.group} aria-labelledby="ai-credit-title">
      <h3 id="ai-credit-title">AI Usage</h3><p className={styles.description}>Separate monthly allowances shared across your account. Switching AI mode does not reset either balance.</p>
      <div className={styles.grid}>
        <div className={styles.ai}>{meter("Included AI Credits", "managed_ai_credits_used")}<p className={styles.note}>Managed AI uses platform credentials. Model usage is included within this allowance.</p></div>
        <div className={styles.ai}>{meter("AI Request Allowance", "byok_ai_requests_used")}<p className={styles.note}>BYOK uses your provider credentials. You pay the provider separately; this allowance limits platform requests.</p></div>
      </div>
      {(subscription.ai_allowance_migration?.unknown_units ?? 0) > 0 && <p className={styles.note}>{subscription.ai_allowance_migration?.unknown_units} earlier AI units could not be attributed to a mode and were conservatively counted against both allowances during migration.</p>}
      <p className={styles.note}>Credits count requests, not tokens or a fixed provider cost. Token usage is tracked separately.</p>
      <p className={styles.note}>Knowledge extraction, story analysis, scenario design, AI test case design and optional bug analysis use the resolved mode’s allowance. A request can generate multiple items. Some timed-out attempts still count.</p>
      <p className={styles.note}>AI used during browser execution is not included in these counters yet.</p>
    </section> : <section className={styles.ai} aria-labelledby="ai-credit-title">
      <div><h3 id="ai-credit-title">AI Credits</h3><p className={styles.description}>Monthly allowance shared by product knowledge extraction, story analysis, scenario design and AI test case design. Optional bug analysis also uses this allowance.</p></div>
      {meter("AI Credits", "ai_gen_used")}
      <p className={styles.note}>Usually one credit per supported AI request. One request can create multiple scenarios or test cases. Some timed-out provider attempts can still consume credits.</p>
      <p className={styles.note}>AI used during browser execution is not included in this counter yet.</p>
    </section>}

    <section className={styles.group} aria-labelledby="workspace-capacity-title">
      <h3 id="workspace-capacity-title">Workspace Capacity</h3><p className={styles.description}>Resource allowances across all projects. These counts are separate from AI credits.</p>
      <div className={`${styles.grid} ${styles.resources}`}>
        {[["Projects", "projects_used"], ["Stories", "stories_used"], ["Scenarios", "scenarios_used"]].map(([label, key]) => <div className={styles.card} key={key}>{meter(label, key)}</div>)}
        <div className={`${styles.card} ${styles.testCases}`}>{meter("Test Cases", "testcases_used")}<div className={styles.tiers} role="group" aria-label="Test case usage by complexity">{["basic", "medium", "advanced"].map(tier => <div key={tier}>{meter(title(tier), `testcases_${tier}_used`, true)}</div>)}</div></div>
      </div>
    </section>

    <div className={styles.grid}>
      <section className={styles.card} aria-labelledby="team-capacity-title"><h3 id="team-capacity-title">Team Capacity</h3>{meter("Additional Team Members", "team_members_used")}<p className={styles.note}>The owner is excluded. Other account members and pending invitations count once, regardless of project assignments.</p></section>
      {enabled("automation_execution_ui") && <section className={styles.card} aria-labelledby="execution-usage-title"><h3 id="execution-usage-title">Execution Usage</h3>{meter("Executions", "executions_used")}<p className={styles.note}>The recorded execution counter is separate from AI credits. Synthetic development runs are not commercially billed.</p></section>}
    </div>
  </section>;
}
