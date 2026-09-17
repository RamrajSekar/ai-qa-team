"use client";

import { useParams } from "next/navigation";
import PlatformAdminGuard from "@/components/platform/PlatformAdminGuard";
import PromptManager from "@/components/platform/PromptManager";

export default function PromptPage() {
  const { promptKey } = useParams<{ promptKey: string }>();
  return <PlatformAdminGuard><PromptManager promptKey={promptKey} /></PlatformAdminGuard>;
}
