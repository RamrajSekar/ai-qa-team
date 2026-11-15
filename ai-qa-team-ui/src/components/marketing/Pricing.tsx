"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/utils/api";

type Offer = { monthly_usd: number | null; managed_ai_credits_limit: number; byok_ai_requests_limit: number };
type Catalog = { stage: string; currency: string; free: Offer & { additional_members_limit: number }; managed: Offer; byok: Offer; enterprise: Offer; pilot: { fixed_usd: number } };

export default function Pricing() {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [error, setError] = useState(false);
  const [reload, setReload] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    apiFetch("/auth/pricing", { signal: controller.signal }).then(response => {
      if (!response.ok || response.data?.stage !== "EXPERIMENTAL") throw new Error("CATALOG_UNAVAILABLE");
      if (!controller.signal.aborted) { setCatalog(response.data); setError(false); }
    }).catch(() => { if (!controller.signal.aborted) setError(true); });
    return () => controller.abort();
  }, [reload]);
  const price = (amount: number | null) => amount === null ? "Let’s discuss" : new Intl.NumberFormat("en-US", {style: "currency", currency: "USD", maximumFractionDigits: 0}).format(amount);
  return <section id="pricing" className="lp-section lp-container">
    <p className="lp-eyebrow">Early-access pricing</p><h1>Choose how you use AI.</h1>
    <p className="lp-intro">Use our AI connection, or bring your own provider key. Both help your team turn product knowledge and stories into reviewed test cases.</p>
    <p className="lp-note">Indicative prices. Paid plans are not yet available for self-service purchase.</p>
    {error ? <div role="alert"><p>Pricing details are temporarily unavailable.</p><button className="lp-button" onClick={() => setReload(value => value + 1)}>Try again</button></div> : !catalog ? <p role="status">Loading pricing details…</p> : <>
      <div className="lp-pricing-grid">
        <article className="lp-pricing-card"><h2>Free Evaluation</h2><p className="lp-pricing-price">{price(catalog.free.monthly_usd)}</p><p>Explore the Test Design workspace.</p><ul><li>{catalog.free.managed_ai_credits_limit} Managed AI Requests / month</li><li>{catalog.free.byok_ai_requests_limit} BYOK AI Requests / month</li><li>Owner + {catalog.free.additional_members_limit} additional members</li></ul><Link className="lp-button lp-secondary" href="/auth?mode=signup">Get started</Link></article>
        <article className="lp-pricing-card"><h2>Managed AI</h2><p className="lp-pricing-price">~{price(catalog.managed.monthly_usd)}<small>/ month · indicative</small></p><p>Use AI without setting up a provider key.</p><ul><li>{catalog.managed.managed_ai_credits_limit} Managed AI Requests / month</li><li>Included supported AI usage</li><li>Shared knowledge and test review</li></ul><Link className="lp-button" href="/auth?mode=signup">Explore Managed</Link></article>
        <article className="lp-pricing-card"><h2>Bring Your Own Key</h2><p className="lp-pricing-price">~{price(catalog.byok.monthly_usd)}<small>/ month · indicative</small></p><p>Use a supported AI provider account you control.</p><ul><li>{catalog.byok.byok_ai_requests_limit} BYOK AI Requests / month</li><li>Same Test Design workspace</li><li>AI provider charges paid separately</li></ul><Link className="lp-button lp-secondary" href="/auth?mode=signup">Explore BYOK</Link></article>
      </div>
      <div className="lp-callout"><h2>Start with a focused pilot</h2><p>Approximately {price(catalog.pilot.fixed_usd)} for an agreed scope. Discuss pilot or enterprise requirements with us during onboarding.</p></div>
    </>}
    <dl className="lp-facts"><div><dt>Which AI option should I choose?</dt><dd>Managed AI requires no customer key. With BYOK, you pay your AI provider separately.</dd></div><div><dt>What is an AI request?</dt><dd>One generation, analysis or question can produce multiple items. Requests are not tokens; human review uses no AI request.</dd></div><div><dt>What is included today?</dt><dd>Test Design is the current focus. Automated browser execution and recording uploads are not included. No payment or upgrade happens on this page.</dd></div></dl>
  </section>;
}
