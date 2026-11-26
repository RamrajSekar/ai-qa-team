"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/components/providers/AuthProvider";
import { apiFetch } from "@/utils/api";

interface BillingStatus {
  hosted_domains: {checkout: string; portal: string};
  checkout_available: boolean; portal_available: boolean; test_mode: boolean; state: string; paid_until?: number;
  pending?: {request_id: string; plan: "team" | "business"; state: string} | null;
}

export default function BillingActions() {
  const { user } = useAuth();
  const [status, setStatus] = useState<BillingStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [requests, setRequests] = useState<Partial<Record<"team" | "business", string>>>({});
  const admin = user?.account_role === "OWNER" || user?.account_role === "ADMIN";
  const read = useCallback((signal?: AbortSignal) => apiFetch("/account/billing", {cache: "no-store", signal}), []);
  const applyStatus = useCallback((response: Awaited<ReturnType<typeof apiFetch>>) => {
    if (response.ok && response.data && typeof response.data.checkout_available === "boolean") setStatus(response.data);
  }, []);
  const load = useCallback(async () => applyStatus(await read()), [read, applyStatus]);
  useEffect(() => { const controller = new AbortController(); void read(controller.signal).then(response => {if (!controller.signal.aborted) applyStatus(response);}).catch(() => {}); return () => controller.abort(); }, [read, applyStatus]);
  async function action(plan?: "team" | "business", resume?: string) {
    setBusy(true); setError("");
    const requestId = plan ? resume || requests[plan] || crypto.randomUUID().replaceAll("-", "") : undefined;
    if (plan && requestId) setRequests(current => ({...current, [plan]: requestId}));
    try {
      const response = await apiFetch(`/account/billing/${plan ? "checkout" : "portal"}`, {method: "POST", retry: true,
        ...(plan ? {body: JSON.stringify({plan, request_id: requestId})} : {})});
      if (!response.ok) throw new Error(typeof response.data?.detail === "string" ? response.data.detail : "Billing could not be confirmed. Refresh status before trying again.");
      const url = new URL(response.data.url);
      if (url.protocol !== "https:" || url.hostname !== (plan ? status?.hosted_domains.checkout : status?.hosted_domains.portal) || url.username || url.password || url.port && url.port !== "443") throw new Error("Billing returned an invalid page.");
      window.location.assign(url.href);
    } catch (failure) { setError(failure instanceof Error ? failure.message : "Billing is temporarily unavailable."); await load().catch(() => {}); }
    finally { setBusy(false); }
  }
  if (!status || !admin || !status.checkout_available && !status.portal_available && !status.pending) return null;
  return <section className="lp-pricing-extras" aria-label="Account billing">
    <h2>Account billing</h2>
    {status.test_mode && <p className="lp-note">Test environment. No live payment is collected.</p>}
    {status.state === "review_required" || status.state === "past_due" ? <p role="status">Billing needs attention. Existing records and manual review remain available.</p> : null}
    <div className="repository-actions">
      {status.pending ? <button className="lp-button lp-secondary" disabled={busy} onClick={() => void action(status.pending!.plan, status.pending!.request_id)}>Resume saved checkout</button>
        : status.checkout_available && (["team", "business"] as const).map(plan => <button key={plan} className="lp-button lp-secondary" disabled={busy} onClick={() => void action(plan)}>{status.test_mode ? "Test " : "Choose "}{plan === "team" ? "Team" : "Business"} checkout</button>)}
      {status.portal_available && <button className="lp-button lp-secondary" disabled={busy} onClick={() => void action()}>Manage billing</button>}
    </div>
    <p className="lp-note">Monthly account subscription. No automatic overages. Plan changes and extra purchases are not available here.</p>
    {error && <div role="alert"><p>{error}</p><button type="button" className="lp-button lp-secondary" disabled={busy} onClick={() => void load()}>Refresh billing status</button></div>}
  </section>;
}
