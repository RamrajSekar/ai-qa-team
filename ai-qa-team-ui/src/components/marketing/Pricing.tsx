"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/utils/api";
import { useAuth } from "@/components/providers/AuthProvider";

type Capacity = "users_limit" | "projects_limit" | "stories_limit" | "scenarios_limit" | "testcases_limit" | "managed_ai_credits_limit" | "byok_ai_requests_limit";
type Offer = { monthly_usd: number; availability: "available" | "planned" } & Record<Capacity, number>;
type Catalog = {
  catalog_version: 2; stage: "EXPERIMENTAL"; currency: "USD"; billing_enabled: false;
  offers: {free: Offer; team: Offer; business: Offer; enterprise: {monthly_usd: null; availability: "planned"}};
  contact_url: string | null;
  add_ons: {availability: "planned"; additional_user_monthly_usd: number; managed_pack: {requests:number;usd:number}; byok_pack: {requests:number;usd:number}};
};
const rows: {key:Capacity;label:string}[] = [
  {key:"users_limit",label:"Users, including owner"}, {key:"projects_limit",label:"Projects"},
  {key:"stories_limit",label:"Stories"}, {key:"scenarios_limit",label:"Scenarios"},
  {key:"testcases_limit",label:"Test cases"}, {key:"managed_ai_credits_limit",label:"Managed AI requests / month"},
  {key:"byok_ai_requests_limit",label:"BYOK requests / month"},
];
const whole = (value:unknown) => typeof value === "number" && Number.isSafeInteger(value) && value >= 0;
function validCatalog(value:Catalog) {
  if (!value || value.catalog_version !== 2 || value.stage !== "EXPERIMENTAL" || value.currency !== "USD" || value.billing_enabled !== false) return false;
  for (const key of ["free","team","business"] as const) {
    const offer=value.offers?.[key];
    if (!offer || !whole(offer.monthly_usd) || rows.some(row=>!whole(offer[row.key])) || offer.users_limit < 1 || offer.availability !== (key === "free" ? "available" : "planned")) return false;
  }
  if (value.offers?.enterprise?.monthly_usd !== null || value.offers.enterprise.availability !== "planned" || value.add_ons?.availability !== "planned" || !whole(value.add_ons.additional_user_monthly_usd)) return false;
  for (const pack of [value.add_ons.managed_pack,value.add_ons.byok_pack]) if (!pack || !whole(pack.usd) || !whole(pack.requests) || pack.requests < 1) return false;
  if (value.contact_url) {
    try { const url=new URL(value.contact_url);if(url.protocol!=="https:"||url.username||url.password)return false; } catch { return false; }
  }
  return true;
}

export default function Pricing({ workspace = false }: { workspace?: boolean }) {
  const { user } = useAuth();
  const signedIn = workspace || !!user;
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [error, setError] = useState(false);
  const [reload, setReload] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    apiFetch("/auth/pricing", { signal: controller.signal }).then(response => {
      if (!response.ok || !validCatalog(response.data)) throw new Error("CATALOG_UNAVAILABLE");
      if (!controller.signal.aborted) { setCatalog(response.data); setError(false); }
    }).catch(() => { if (!controller.signal.aborted) setError(true); });
    return () => controller.abort();
  }, [reload]);
  const price = (amount:number) => new Intl.NumberFormat("en-US", {style:"currency",currency:"USD",maximumFractionDigits:0}).format(amount);
  const count = (amount:number) => new Intl.NumberFormat("en-US").format(amount);
  function contact(plan:string) {
    return catalog?.contact_url ? <a className="lp-button lp-secondary" href={catalog.contact_url} aria-label={`Contact us about ${plan}`}>Contact us</a> : <button type="button" className="lp-button lp-secondary" disabled aria-label={`${plan} coming soon`}>Coming soon</button>;
  }
  return <section id="pricing" className="lp-section lp-container lp-pricing-v2">
    <p className="lp-eyebrow">Test Design pricing</p><h1>Plans for your QA team.</h1>
    <p className="lp-intro">Turn product knowledge and stories into reviewed scenarios and test cases.</p>
    <p className="lp-note">USD per account, billed monthly. Paid plans and add-ons are planned; online purchasing is not available yet.</p>
    {error ? <div role="alert" className="lp-pricing-state"><p>Pricing details are temporarily unavailable.</p><button className="lp-button lp-secondary" onClick={() => {setError(false);setReload(value => value + 1);}}>Try again</button></div> : !catalog ? <p role="status">Loading pricing details...</p> : <>
      <div className="lp-pricing-grid">
        {(["free","team","business"] as const).map(key=>{
          const offer=catalog.offers[key];const name=key === "free" ? "Free" : key === "team" ? "Team" : "Business";
          return <article key={key} className={`lp-pricing-card ${key === "team" ? "lp-pricing-featured" : ""}`} aria-label={`${name} plan`}>
            <div className="lp-pricing-card-head"><h2>{name}</h2>{key !== "free" && <span className="lp-plan-label">Early access</span>}</div>
            <p className="lp-pricing-price">{price(offer.monthly_usd)}<small>per account / month</small></p>
            <p className="lp-pricing-summary">{key === "free" ? "Explore the full Test Design journey." : key === "team" ? "For small teams building shared coverage." : "More capacity for growing QA teams."}</p>
            <ul><li>{count(offer.users_limit)} users, including owner</li><li>{count(offer.projects_limit)} {offer.projects_limit === 1 ? "project" : "projects"}</li><li>{count(offer.testcases_limit)} saved test cases</li><li>{count(offer.managed_ai_credits_limit)} Managed requests / month</li><li>{count(offer.byok_ai_requests_limit)} BYOK requests / month</li></ul>
            {key === "free" ? !workspace && <Link className="lp-button lp-secondary" href={signedIn ? "/settings/account" : "/auth?mode=signup"}>{signedIn ? "Open account" : "Get started"}</Link> : contact(name)}
          </article>;
        })}
        <article className="lp-pricing-card" aria-label="Enterprise plan"><div className="lp-pricing-card-head"><h2>Enterprise</h2><span className="lp-plan-label">Planned</span></div><p className="lp-pricing-price lp-pricing-custom">Custom<small>for agreed requirements</small></p><p className="lp-pricing-summary">Discuss larger teams and specialized needs.</p><ul><li>Agreed user and project capacity</li><li>Agreed AI allowances</li><li>Scope and support defined together</li></ul>{contact("Enterprise")}</article>
      </div>
      <section className="lp-pricing-comparison" aria-labelledby="compare-plans"><h2 id="compare-plans">Compare capacity</h2><p className="lp-note">Shared across account projects. All test-case complexities use the same allowance.</p>
        <div className="lp-pricing-table-scroll" role="region" aria-label="Plan comparison; scroll for all plans" tabIndex={0}><table><thead><tr><th scope="col">Included capacity</th><th scope="col">Free</th><th scope="col">Team</th><th scope="col">Business</th><th scope="col">Enterprise</th></tr></thead><tbody>{rows.map(row=><tr key={row.key}><th scope="row">{row.label}</th>{(["free","team","business"] as const).map(key=><td key={key}>{count(catalog.offers[key][row.key])}</td>)}<td>Custom</td></tr>)}</tbody></table></div>
        <p className="lp-note">Saved-item capacity does not reset monthly. AI allowances reset monthly and remain separate for Managed and BYOK.</p>
      </section>
      <section className="lp-pricing-extras" aria-labelledby="planned-extras"><div><p className="lp-eyebrow">Planned add-ons</p><h2 id="planned-extras">Room to grow</h2><p className="lp-note">Proposed pricing, subject to validation. Add-ons cannot be purchased yet.</p></div><div className="lp-pricing-extra-grid">
        <article><h3>Additional users</h3><p className="lp-extra-price">{price(catalog.add_ons.additional_user_monthly_usd)}<small>per user / month on paid plans</small></p><p>AI and saved-item capacity stay shared.</p></article>
        <article><h3>Managed AI pack</h3><p className="lp-extra-price">{price(catalog.add_ons.managed_pack.usd)}<small>for {count(catalog.add_ons.managed_pack.requests)} requests</small></p><p>Optional extra allowance. No automatic overages.</p></article>
        <article><h3>BYOK request pack</h3><p className="lp-extra-price">{price(catalog.add_ons.byok_pack.usd)}<small>for {count(catalog.add_ons.byok_pack.requests)} requests</small></p><p>Your AI provider bills you separately.</p></article>
      </div></section>
    </>}
    <dl className="lp-facts">
      <div><dt>Managed or BYOK?</dt><dd>Managed uses our AI connection. BYOK uses your supported provider key, with provider charges paid separately. They are choices within an account plan.</dd></div>
      <div><dt>What counts as an AI request?</dt><dd>One generation, analysis or question can produce multiple items. Requests are not tokens; manual editing and human review use no AI request.</dd></div>
      <div><dt>Is automation included?</dt><dd>Automated browser execution is a future optional add-on. Recording uploads are not included.</dd></div>
      <div><dt>Can I upgrade now?</dt><dd>Paid plans are in preparation. This page does not collect payment, change your subscription or update existing account limits.</dd></div>
    </dl>
  </section>;
}
