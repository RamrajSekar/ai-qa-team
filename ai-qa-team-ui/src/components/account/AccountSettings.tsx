"use client";

import { useCallback, useEffect, useState } from "react";
import { useFeatures } from "@/components/providers/FeatureFlagsProvider";
import { useAuth } from "@/components/providers/AuthProvider";
import Link from "next/link";
import SubscriptionUsage, { type AccountSubscription } from "./SubscriptionUsage";
import TeamManager from "@/components/team/TeamManager";
import { apiFetch } from "@/utils/api";

interface Account { account_id: string; name: string | null; current_user_role: string; setup_status: string }
interface Member { email: string; name?: string; account_role: string }
interface Invitation { invitation_id: string; email: string; role: string; expires_at: string }

export default function AccountSettings({ team = false }: { team?: boolean }) {
  const { user } = useAuth();
  const { enabled } = useFeatures();
  const emailEnabled = enabled("account_invitation_email");
  const admin = user?.account_role === "OWNER" || user?.account_role === "ADMIN";
  const [projects, setProjects] = useState<{project_id: string; name: string}[]>([]);
  const [projectId, setProjectId] = useState("");
  const [billing, setBilling] = useState<{ billing_scope?: string; subscription?: AccountSubscription } | null>(null);
  const [account, setAccount] = useState<Account | null>(null);
  const [members, setMembers] = useState<Member[]>([]);
  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const [name, setName] = useState(""); const [email, setEmail] = useState("");
  const [role, setRole] = useState("MEMBER"); const [link, setLink] = useState("");
  const [busy, setBusy] = useState(false); const [error, setError] = useState(""); const [message, setMessage] = useState("");

  const request = useCallback(async (path: string, options?: RequestInit) => {
    const response = await apiFetch(path, { cache: "no-store", ...options });
    if (!response.ok) throw new Error(typeof response.data?.detail === "string" ? response.data.detail : "Could not complete this account request.");
    return response.data;
  }, []);
  const load = useCallback(async (signal?: AbortSignal) => {
    const [current, people, pending, managed, subscription] = await Promise.all([
      request("/account", { signal }), request("/account/members", { signal }), admin && team ? request("/account/invitations", { signal }) : Promise.resolve([]),
      admin && team ? request("/account/projects", { signal }) : Promise.resolve([]),
      !team ? request("/account/subscription", { signal }) : Promise.resolve(null),
    ]);
    if (!signal?.aborted) { setAccount(current); setName(current.name || ""); setMembers(people); setInvitations(pending); setProjects(managed); setBilling(subscription); }
  }, [request, admin, team]);
  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal).catch(failure => { if (!controller.signal.aborted) setError(failure instanceof Error ? failure.message : "Could not load account."); });
    return () => controller.abort();
  }, [load]);

  async function action(work: () => Promise<void>) {
    setBusy(true); setError(""); setMessage("");
    try { await work(); } catch (failure) { setError(failure instanceof Error ? failure.message : "Could not complete request."); }
    finally { setBusy(false); }
  }
  return <div className="design-page">
    <header><p className="workspace-eyebrow">Customer workspace</p><h1>{team ? "Account team" : "Account"}</h1><p className="workspace-description">One customer account for your team and projects. Project permissions remain separate.</p></header>
    {error && <p role="alert" className="repository-error">{error}</p>}
    <nav className="repository-actions" aria-label="Account settings"><Link className="workspace-button" href="/settings/account">Account details</Link><Link className="workspace-button" href="/settings/account/team">Team & project access</Link></nav>
    {!account ? <button className="workspace-button" disabled={busy} onClick={() => void action(load)}>Reload account</button> : <>
      {!team && <section className="space-y-4"><h2>Customer details</h2><p className="workspace-metadata">Your account role: {account.current_user_role}</p>
        <label>Customer / account name<input value={name} maxLength={160} disabled={!admin || busy} onChange={event => setName(event.target.value)} /></label>
        {admin && <button className="workspace-button workspace-primary" disabled={busy || name.trim().length < 2} onClick={() => void action(async () => {
          await request("/account", { method: "PATCH", body: JSON.stringify({ name: name.trim() }) }); await load(); setMessage("Account name saved.");
        })}>Save account name</button>}
        <p className="workspace-description">{billing?.billing_scope === "ACCOUNT" ? "Your subscription and usage are shared across this customer account." : "Account subscription migration is required before shared billing is enabled."}</p>
      </section>}
      {!team && billing?.subscription && <SubscriptionUsage subscription={billing.subscription} />}
      {team && <section><h2>Account members</h2>{members.map(member => <div className="workspace-row" key={member.email}><div><strong>{member.name || member.email}</strong><p className="workspace-row-subtitle">{member.email}</p></div><span className="workspace-badge">{member.account_role}</span></div>)}</section>}
      {team && admin && <section className="space-y-4"><h2>Invite a new account member</h2><p className="workspace-description">{emailEnabled ? "Send a seven-day invitation by email." : "Create a seven-day invitation link and share it privately. Email delivery can be enabled later."} Existing members are added to projects under Project assignments below.</p>
        <label>New member email<input type="email" value={email} disabled={busy} onChange={event => setEmail(event.target.value)} /></label>
        {user?.account_role === "OWNER" && <label>Account role<select value={role} disabled={busy} onChange={event => setRole(event.target.value)}><option value="MEMBER">Member</option><option value="ADMIN">Account administrator</option></select></label>}
        <button className="workspace-button workspace-primary" disabled={busy || !email.includes("@")} onClick={() => void action(async () => {
          try {
            setLink("");
            const created = await request("/account/invitations", { method: "POST", body: JSON.stringify({ email: email.trim(), role, delivery: emailEnabled ? "EMAIL" : "LINK" }) });
            if (!emailEnabled) setLink(`${window.location.origin}/auth?mode=signup#invite=${encodeURIComponent(created.token)}`);
            setEmail(""); setMessage(emailEnabled ? "Invitation email sent." : "Invitation created. Copy the link now; it is not available again.");
          } finally { await load(); }
        })}>{emailEnabled ? "Send Invitation" : "Create invitation link"}</button>
        {link && <div className="workspace-notice"><label>Private invitation link<input readOnly value={link} onFocus={event => event.target.select()} /></label><button className="workspace-button" onClick={() => void action(async () => { await navigator.clipboard.writeText(link); setMessage("Invitation link copied. Share it only with the invited person."); })}>Copy invitation link</button><button className="workspace-button" onClick={() => setLink("")}>Hide link</button></div>}
        <h3>Pending invitations</h3>{invitations.map(invitation => <div className="workspace-row" key={invitation.invitation_id}><div><strong>{invitation.email}</strong><p className="workspace-row-subtitle">{invitation.role} · expires {new Date(invitation.expires_at).toLocaleDateString()}</p></div><button className="workspace-button" disabled={busy} onClick={() => void action(async () => { await request(`/account/invitations/${invitation.invitation_id}`, { method: "DELETE" }); setLink(""); await load(); setMessage("Invitation revoked."); })}>Revoke invitation</button></div>)}
      </section>}
      {team && admin && <section><h2>Project assignments</h2><p>Assign account members to projects. Account administration does not grant access to project content.</p><label>Project<select aria-label="Project" value={projectId} onChange={event => setProjectId(event.target.value)}><option value="">Select a project</option>{projects.map(project => <option key={project.project_id} value={project.project_id}>{project.name} ({project.project_id})</option>)}</select></label>{projectId && <TeamManager key={projectId} projectId={projectId} />}</section>}
    </>}
    {message && <p role="status">{message}</p>}
  </div>;
}
