"use client";

import { useParams } from "next/navigation";
import AIConfigurationManager from "@/components/ai/AIConfigurationManager";

export default function AIConfigurationPage() {
  const { projectId } = useParams<{ projectId: string }>();
  return <div><div className="workspace-page-header"><div><p className="workspace-eyebrow">Project settings</p><h1>AI Configuration</h1><p className="workspace-description">Choose managed AI or connect a project-owned provider credential.</p></div></div><AIConfigurationManager projectId={projectId} /></div>;
}
