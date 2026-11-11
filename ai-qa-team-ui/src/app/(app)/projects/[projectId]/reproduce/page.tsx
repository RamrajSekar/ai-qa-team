"use client";

import { useParams } from "next/navigation";
import BugInterpreter from "@/components/bugs/BugInterpreter";

export default function ReproduceBugPage() {
  const { projectId } = useParams<{ projectId: string }>();
  return <div><div className="workspace-page-header"><div><p className="workspace-eyebrow">Testing intent</p><h1>Reproduce Bug</h1><p className="workspace-description">Turn a bug report into a structured review of what should be tested.</p></div></div><BugInterpreter projectId={projectId} /></div>;
}
