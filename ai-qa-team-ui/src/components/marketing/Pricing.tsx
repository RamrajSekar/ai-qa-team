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
    <p className="lp-eyebrow">Pricing exploration · Not a checkout</p><h1>Choose how your team uses AI.</h1>
    <p className="lp-intro">Managed AI includes model usage. Bring your own key (BYOK) keeps provider billing with you. Both use the same platform for knowledge review, story analysis and approved test design.</p>
    <div className="lp-banner">Prices and allowances are experimental hypotheses, subject to pilot validation. Paid subscriptions are not available for self-service purchase.</div>
    {error ? <div role="alert"><p>Pricing details are temporarily unavailable.</p><button className="lp-button" onClick={() => setReload(value => value + 1)}>Try again</button></div> : !catalog ? <p role="status">Loading pricing details…</p> : <>
      <div className="lp-pricing-grid">
        <article className="lp-pricing-card"><h2>Free Evaluation</h2><p className="lp-pricing-price">{price(catalog.free.monthly_usd)}</p><p>Controlled evaluation, not unrestricted browser execution.</p><ul><li>{catalog.free.managed_ai_credits_limit} Managed AI Requests / month</li><li>{catalog.free.byok_ai_requests_limit} BYOK AI Requests / month</li><li>Account owner + {catalog.free.additional_members_limit} additional members</li><li>Review stories, scenarios and test cases</li></ul><Link className="lp-button lp-secondary" href="/auth?mode=signup">Create an evaluation account</Link></article>
        <article className="lp-pricing-card"><h2>Managed AI</h2><p className="lp-pricing-price">~{price(catalog.managed.monthly_usd)}<small>/ month hypothesis</small></p><p>Platform subscription with supported model usage included.</p><ul><li>{catalog.managed.managed_ai_credits_limit} Managed AI Requests / month</li><li>Platform-managed provider credentials</li><li>Shared knowledge, approvals and team access</li><li>No separate customer model-provider bill for included requests</li></ul><Link className="lp-button" href="/auth?mode=signup">Explore the pilot</Link></article>
        <article className="lp-pricing-card"><h2>Bring Your Own Key</h2><p className="lp-pricing-price">~{price(catalog.byok.monthly_usd)}<small>/ month hypothesis</small></p><p>Platform subscription; you pay your AI provider directly.</p><ul><li>{catalog.byok.byok_ai_requests_limit} BYOK AI Requests / month</li><li>Supported provider/model combinations only</li><li>Same knowledge and test-design workflow</li><li>Provider charges are additional and separate</li></ul><Link className="lp-button lp-secondary" href="/auth?mode=signup">Explore BYOK</Link></article>
      </div>
      <div className="lp-callout"><h2>Fixed-scope pilot</h2><p>~{price(catalog.pilot.fixed_usd)} pricing hypothesis for an agreed scope. Enterprise allowances are configurable and capped; contact the platform team during onboarding to discuss a suitable scope. No automatic plan upgrade or charge occurs here.</p></div>
    </>}
    <section className="lp-roadmap"><h2>What does an allowance cover?</h2><dl className="lp-facts"><div><dt>Managed AI Requests · Managed</dt><dd>Supported requests use the platform’s credentials and model budget. One request may generate multiple scenarios or test cases.</dd></div><div><dt>BYOK AI Requests · BYOK</dt><dd>The platform limits requests; the customer separately pays their provider for tokens. Switching modes does not replenish either allowance.</dd></div><div><dt>Credits are not tokens</dt><dd>Credits count supported requests, not model tokens or a fixed dollar value. Token usage and provider charges vary by model and request size.</dd></div><div><dt>Enterprise BYOK is optional</dt><dd>Managed AI requires no customer key. BYOK requires your organization’s approval for this platform to use a scoped provider key; procurement and security review still apply. Do not submit an unrestricted master key.</dd></div><div><dt>Human review and correction</dt><dd>Editing or approving content is separate from asking AI to generate or analyze it.</dd></div><div><dt>Execution and delivery scope</dt><dd>Test Design is the current priority. Recording upload/transcription and customer-app automated execution remain gated. Future execution AI requires a separate bounded budget; these prices do not promise unlimited execution or production readiness.</dd></div></dl></section>
  </section>;
}
