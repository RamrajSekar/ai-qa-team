"use client";

import { useParams } from "next/navigation";
import ExecutionHistory from "@/components/projects/ExecutionHistory";

export default function ExecutionHistoryPage() {
  const { projectId } = useParams<{ projectId: string }>();
  return <ExecutionHistory key={projectId} projectId={projectId} />;
}
