"use client";

import { useState } from "react";
import AIConfigurationManager from "@/components/ai/AIConfigurationManager";
import { useProjects } from "@/hooks/useProjects";

export default function WorkspaceAIConfigurationPage() {
  const { projects, loading, failed, reload } = useProjects();
  const [selected, setSelected] = useState("");
  const manageable = projects.filter(project => project.current_user_role === "ADMIN");
  const projectId = manageable.find(project => project.project_id === selected)?.project_id || manageable[0]?.project_id;
  return <div className="space-y-6">
    <div className="workspace-page-header"><div><p className="workspace-eyebrow">Workspace settings</p><h1>AI Configuration</h1>
      <p className="workspace-description">Manage provider settings for projects you administer. Each project keeps its own credentials and active provider.</p></div></div>
    {loading ? <p role="status">Loading projects…</p> : failed ? <div role="alert">Could not load projects. <button onClick={() => void reload()}>Try again</button></div>
      : projectId ? <>
        <label>Project<select className="border rounded p-2 ml-3" value={projectId} onChange={event => setSelected(event.target.value)}>
          {manageable.map(project => <option key={project.project_id} value={project.project_id}>{project.name}</option>)}
        </select></label>
        <AIConfigurationManager key={projectId} projectId={projectId} />
      </> : <p>A project administrator can configure AI after creating or joining a project.</p>}
  </div>;
}
