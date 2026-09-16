"use client";

import { useCallback, useEffect, useState } from "react";
import { MailPlus, ShieldCheck, Trash2, UserRound } from "lucide-react";
import { apiFetch } from "@/utils/api";
import type { ProjectMembership, ProjectRole, ProjectTeam } from "@/types/team";
import { useAuth } from "@/components/providers/AuthProvider";

interface Props {
  projectId: string;
  onboarding?: boolean;
  onContinue?: () => void;
}

export default function TeamManager({ projectId, onboarding = false, onContinue }: Props) {
  const { user } = useAuth();
  const [team, setTeam] = useState<ProjectTeam | null>(null);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<ProjectRole>("TESTER");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const response = await apiFetch(`/projects/${projectId}/team`);
    if (response.ok) setTeam(response.data as ProjectTeam);
    else setError(response.data?.detail || "Unable to load the project team.");
  }, [projectId]);

  useEffect(() => {
    async function initialLoad() { await load(); }
    initialLoad();
  }, [load]);

  async function invite() {
    setSaving(true); setError(null);
    const response = await apiFetch(`/projects/${projectId}/team`, {
      method: "POST", body: JSON.stringify({ email, role }),
    });
    if (response.ok) { setEmail(""); await load(); }
    else setError(response.data?.detail || "Unable to invite this team member.");
    setSaving(false);
  }

  async function changeRole(member: ProjectMembership, nextRole: ProjectRole) {
    setError(null);
    const response = await apiFetch(`/projects/${projectId}/team/${member.membership_id}`, {
      method: "PATCH", body: JSON.stringify({ role: nextRole }),
    });
    if (response.ok) await load();
    else setError(response.data?.detail || "Unable to change this role.");
  }

  async function remove(member: ProjectMembership) {
    setError(null);
    const response = await apiFetch(`/projects/${projectId}/team/${member.membership_id}`, { method: "DELETE" });
    if (response.ok) await load();
    else setError(response.data?.detail || "Unable to remove this team member.");
  }

  const admin = team?.current_user_role === "ADMIN";
  return <div className="team-manager">
    <div className="team-list">
      {(team?.members || []).map((member) => <div className="team-row" key={member.membership_id}>
        <div className="team-identity"><span><UserRound size={17} /></span><div><strong>{member.email === user?.email ? "You" : member.name || member.email}</strong><small>{member.email === user?.email || member.name ? member.email : member.status === "INVITED" ? "Invitation pending" : "Project member"}</small></div></div>
        <div className="team-controls">
          {admin ? <select aria-label={`Role for ${member.email}`} value={member.role} onChange={(event) => changeRole(member, event.target.value as ProjectRole)}><option value="ADMIN">Project Admin</option><option value="TESTER">Tester</option></select> : <span className="workspace-badge">{member.role === "ADMIN" ? "Project Admin" : "Tester"}</span>}
          <span className="workspace-badge">{member.status === "ACTIVE" ? "Active" : "Invited"}</span>
          {admin && <button className="team-remove" aria-label={`Remove ${member.email}`} onClick={() => remove(member)}><Trash2 size={15} /></button>}
        </div>
      </div>)}
    </div>
    {admin && <section className="team-invite"><div><MailPlus size={19} /><div><strong>Invite team member</strong><p>Pending invitations count toward the project owner&apos;s team-member limit.</p></div></div><div className="team-invite-fields"><input type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="teammate@example.com" aria-label="Team member email" /><select value={role} onChange={(event) => setRole(event.target.value as ProjectRole)} aria-label="Team member role"><option value="TESTER">Tester</option><option value="ADMIN">Project Admin</option></select><button className="workspace-button workspace-primary" onClick={invite} disabled={saving || !email.includes("@")}><ShieldCheck size={15} />{saving ? "Adding…" : "Add member"}</button></div></section>}
    {error && <p className="repository-error" role="alert">{error}</p>}
    {onboarding && <div className="repository-actions"><button className="workspace-button" onClick={onContinue}>Skip for now</button><button className="workspace-button workspace-primary" onClick={onContinue}>Continue</button></div>}
  </div>;
}
