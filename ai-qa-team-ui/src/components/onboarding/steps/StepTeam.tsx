"use client";

import TeamManager from "@/components/team/TeamManager";
import { apiFetch } from "@/utils/api";
import StepLayout from "../StepLayout";

export default function StepTeam({ projectId, next, back }: { projectId: string | null; next: () => void; back: () => void }) {
  async function finishTeamStep() {
    await apiFetch("/onboarding/progress", { method: "PUT", body: JSON.stringify({ step_key: "add_users", current_step: 4 }) });
    next();
  }
  return <StepLayout title="Build your project team" description="You are already the Project Admin. Invite teammates now, or continue on your own.">
    {projectId ? <TeamManager projectId={projectId} onboarding onContinue={finishTeamStep} /> : <p className="repository-error">Create a project before adding team members.</p>}
    <button className="workspace-button" onClick={back}>Back</button>
  </StepLayout>;
}
