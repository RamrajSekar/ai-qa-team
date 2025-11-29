import { redirect } from "next/navigation";
import getUserServer from "./lib/getUserServer";

export default async function StepGuard({ children }: { children: React.ReactNode }) {
  const user = await getUserServer();

  if (!user) redirect("/?auth=login-required");

  // NEW IMPORTANT CHECK
  if (!user.onboarding_complete) {
    // User must go through onboarding
    return <>{children}</>;
  }

  // If somehow onboarding_complete=true but no projects exist, still redirect
  if (user.onboarding_complete && user.projects?.length === 0) {
    redirect("/onboarding/step-1");
  }

  return <>{children}</>;
}
