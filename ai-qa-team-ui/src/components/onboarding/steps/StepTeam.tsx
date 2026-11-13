"use client";

import TeamManager from "@/components/team/TeamManager";
import { apiFetch } from "@/utils/api";
import StepLayout from "../StepLayout";

export default function StepTeam({ projectId, next, back }: { projectId: string | null; next: () => void; back: () => void }) {
  async function finishTeamStep() {
    await apiFetch("/onboarding/progress", { method: "PUT", body: JSON.stringify({ step_key: "add_users", current_step: 5 }) });
    next();
  }
  return <StepLayout title="Build your project team" description="The project creator starts as Project Admin. Account owners and administrators can update project assignments and roles in Account → Team. Add another admin before changing the last admin's role.">
    {projectId ? <TeamManager projectId={projectId} onboarding onContinue={finishTeamStep} /> : <p className="repository-error">Create a project before adding team members.</p>}
    <button className="workspace-button" onClick={back}>Back</button>
  </StepLayout>;
}
