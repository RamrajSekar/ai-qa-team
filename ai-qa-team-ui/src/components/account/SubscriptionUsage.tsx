"use client";
import Link from "next/link";
import AIPoolUsage from "./AIPoolUsage";
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
    <dl className={styles.meterLine}><dt>{label}</dt><dd>{limit === 0 ? "Not included" : limit === undefined ? "Unavailable" : `${used} / ${limit === null ? "Unlimited" : limit}`}</dd></dl>
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
      <div><Link href="/settings/account/plans" className="workspace-button">View plans</Link><p className={styles.note}>Paid upgrades are not yet available online.</p></div>
      <dl className={styles.plan}><div><dt>Plan</dt><dd><strong>{title(subscription.plan)}</strong></dd></div><div><dt>Status</dt><dd><strong className={styles.status}>{title(subscription.status)}</strong></dd></div></dl>
    </header>

    {subscription.ai_allowance_version === 1 ? <section className={styles.group} aria-labelledby="ai-credit-title">
      <h3 id="ai-credit-title">AI Usage</h3><p className={styles.description}>Usage is shared across the account. One request uses one unit; switching modes keeps both balances.</p>
      <AIPoolUsage usage={subscription.usage} limits={subscription.limits} />
      <p className={styles.note}>Browser-execution AI usage is excluded.</p>
    </section> : <section className={styles.ai} aria-labelledby="ai-credit-title">
      <div><h3 id="ai-credit-title">AI Requests</h3><p className={styles.description}>Shared monthly allowance for knowledge, story analysis, test design and bug drafts.</p></div>
      {meter("AI Requests", "ai_gen_used")}
      <p className={styles.note}>One request may create multiple items. Timed-out attempts may still use credits.</p>
      <p className={styles.note}>Browser-execution AI usage is excluded.</p>
    </section>}

    <section className={styles.group} aria-labelledby="workspace-capacity-title">
      <h3 id="workspace-capacity-title">Workspace Capacity</h3><p className={styles.description}>Resource limits across all projects.</p>
      <div className={`${styles.grid} ${styles.resources}`}>
        {[["Projects", "projects_used"], ["Stories", "stories_used"]].map(([label, key]) => <div className={styles.card} key={key}>{meter(label, key)}</div>)}
        <div className={`${styles.card} ${styles.testCases}`}>
          {meter("Scenarios", "scenarios_used")}
          <div className={styles.tiers} role="group" aria-label="Scenario usage by complexity">
            {["basic", "medium", "advanced"].map(tier => <div key={tier} className={styles.compactMeter}>
              <dl className={styles.meterLine}><dt>{title(tier)}</dt><dd>{subscription.usage[`scenarios_${tier}_used`] ?? "Unavailable"}</dd></dl>
            </div>)}
          </div>
        </div>
        <div className={`${styles.card} ${styles.testCases}`}>{meter("Test Cases", "testcases_used")}<div className={styles.tiers} role="group" aria-label="Test case usage by complexity">{["basic", "medium", "advanced"].map(tier => <div key={tier}>{meter(title(tier), `testcases_${tier}_used`, true)}</div>)}</div></div>
      </div>
    </section>

    <div className={styles.grid}>
      <section className={styles.card} aria-labelledby="team-capacity-title"><h3 id="team-capacity-title">Team Capacity</h3><Meter label="Team Members" used={(subscription.usage.team_members_used ?? 0) + 1} limit={subscription.limits.team_members_limit == null ? subscription.limits.team_members_limit : subscription.limits.team_members_limit + 1} /><p className={styles.note}>Includes owner, members and pending invitations. Each person counts once.</p></section>
      {enabled("automation_execution_ui") && <section className={styles.card} aria-labelledby="execution-usage-title"><h3 id="execution-usage-title">Execution Usage</h3>{meter("Executions", "executions_used")}<p className={styles.note}>Separate from AI usage. Synthetic runs are unbilled.</p></section>}
    </div>
  </section>;
}
