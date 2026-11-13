"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { usePathname } from "next/navigation";
import { apiFetch } from "@/utils/api";

export type FeatureName =
  | "knowledge_uploads" | "knowledge_media_processing" | "knowledge_image_interpretation"
  | "manual_test_results" | "automation_execution_ui" | "separate_ai_allowances" | "test_execution_ui" | "account_invitation_email" | "customer_accounts" | "account_subscriptions" | "story_management" | "scenario_generation" | "test_generation" | "recorder"
  | "native_execution" | "visual_runner_lab" | "visual_runner_batches" | "jira_trigger" | "failure_diagnostics" | "self_healing"
  | "approved_visual_run_admission" | "approved_visual_run_execution" | "approved_workflow_worker" | "bug_reproduction_ui" | "repository_ui" | "reusable_workflows" | "product_knowledge" | "story_analysis"
  | "playwright_repo_adapter" | "selenium_repo_adapter"
  | "repository_discovery" | "test_registry" | "test_data_generation";

type FeatureState = {
  flags: Partial<Record<FeatureName, boolean>>;
  ready: boolean;
  failed: boolean;
};

const FeatureContext = createContext<FeatureState>({ flags: {}, ready: false, failed: false });

export function FeatureFlagsProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<FeatureState>({ flags: {}, ready: false, failed: false });

  useEffect(() => {
    let active = true;
    apiFetch("/features", { cache: "no-store", signal: AbortSignal.timeout(10000) }).then((response) => {
      if (!response.ok || !response.data || Array.isArray(response.data) ||
          typeof response.data !== "object" ||
          !Object.values(response.data).every((value) => typeof value === "boolean")) {
        throw new Error("Invalid feature map");
      }
      if (active) setState({ flags: response.data, ready: true, failed: false });
    }).catch(() => {
      if (active) setState({ flags: {}, ready: true, failed: true });
    });
    return () => { active = false; };
  }, []);

  return <FeatureContext.Provider value={state}>{children}</FeatureContext.Provider>;
}

export function useFeatures() {
  const state = useContext(FeatureContext);
  return {
    ...state,
    enabled: (...names: FeatureName[]) => names.every((name) => state.flags[name] === true),
  };
}

export function FeatureGate({ names, children }: { names: FeatureName[]; children: ReactNode }) {
  const { enabled } = useFeatures();
  return enabled(...names) ? children : null;
}

// Stop disabled page trees mounting, rather than hiding them after their effects run.
export function FeatureRouteGuard({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { enabled, ready, failed } = useFeatures();
  const segment = pathname.split("/")[1] === "projects"
    ? pathname.split("/")[3]
    : pathname.split("/")[1];
  const required: Partial<Record<string, FeatureName>> = {
    knowledge: "product_knowledge", stories: "story_management", scenarios: "scenario_generation", testcases: "test_generation",
    account: "customer_accounts", recorder: "recorder", reproduce: "bug_reproduction_ui", repositories: "repository_ui",
    "visual-lab": "visual_runner_lab", "test-execution": "test_execution_ui",
  };
  const feature = pathname === "/settings/account" || pathname.startsWith("/settings/account/") ? "customer_accounts" : required[segment];
  if (segment === "test-execution" && ready && enabled("manual_test_results", "test_generation")) return children;
  if (["visual-lab", "test-execution", "execution-history"].includes(segment)) {
    if (!ready) return <p role="status">Loading features...</p>;
    if (!enabled("automation_execution_ui")) return <p role="status">Automation execution is hidden.</p>;
  }
  if (!feature) return children;
  if (!ready) return <p role="status">Loading features...</p>;
  if (failed) return <p role="alert">Feature availability could not be loaded. Reload to try again.</p>;
  if (!enabled(feature)) return <p role="status">This feature is disabled.</p>;
  return children;
}
