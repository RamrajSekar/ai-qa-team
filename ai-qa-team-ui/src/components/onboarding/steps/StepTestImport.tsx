"use client";
import { useFeatures } from "@/components/providers/FeatureFlagsProvider";

import { useState } from "react";
import RepoImportModal from "@/components/integrations/RepoImportModal";
import { Github, Gitlab, GitBranch } from "lucide-react";

interface StepTestImportProps {
  next: () => void;
  projectId: string | null;
}

export default function StepTestImport({ next, projectId }: StepTestImportProps) {
  const { enabled, ready } = useFeatures();
  const canImport = enabled("playwright_repo_adapter", "story_management", "scenario_generation", "test_generation");
  const [provider, setProvider] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  const providers = [
    { id: "github", name: "GitHub", icon: <Github size={20} /> },
    { id: "gitlab", name: "GitLab", icon: <Gitlab size={20} /> },
    { id: "bitbucket", name: "Bitbucket", icon: <GitBranch size={20} /> },
  ];

  // ---------------------------------------------
  // If user reached this step without a project
  // ---------------------------------------------
  if (!ready) return <p role="status">Loading features...</p>;
  if (!canImport) return (
    <div className="p-6 space-y-4">
      <p>Test import is currently disabled. You can continue setting up your project.</p>
      <button onClick={next} className="underline">Continue</button>
    </div>
  );

  if (!projectId) {
    return (
      <div className="p-6 space-y-4">
        <h2 className="text-xl font-semibold">Import Tests</h2>

        <p className="text-gray-500 text-sm">
          A project must be created before importing test cases.
        </p>

        <button
          onClick={next}
          className="mt-4 w-full py-3 rounded bg-purple-600 text-white hover:bg-purple-700"
        >
          Continue →
        </button>
      </div>
    );
  }

  // ---------------------------------------------
  // OAuth redirect
  // ---------------------------------------------
  function startOAuth() {
    if (!provider) return;

    window.location.href =
      `${process.env.NEXT_PUBLIC_API_URL}/auth/${provider}/login` +
      `?callback=${window.location.origin}/oauth/callback`;
  }

  return (
    <div className="p-6 space-y-6">
      <h2 className="font-bold text-xl">Import Tests (Optional)</h2>

      <p className="text-gray-500 text-sm">
        Connect your Git provider to import Playwright test cases.
      </p>

      {/* Provider List */}
      <div className="grid grid-cols-3 gap-4">
        {providers.map((p) => (
          <button
            key={p.id}
            onClick={() => setProvider(p.id)}
            className={`p-4 border rounded-lg flex flex-col items-center gap-2 ${
              provider === p.id ? "border-purple-600 bg-purple-50" : "border-gray-300"
            }`}
          >
            {p.icon}
            <span>{p.name}</span>
          </button>
        ))}
      </div>

      {/* OAuth Button */}
      <button
        disabled={!provider}
        onClick={startOAuth}
        className={`w-full py-3 rounded text-white ${
          provider ? "bg-purple-600 hover:bg-purple-700" : "bg-gray-300 cursor-not-allowed"
        }`}
      >
        Connect {provider?.toUpperCase()} Account
      </button>

      {/* Repo Import Modal (opens after OAuth) */}
      <RepoImportModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        provider={provider ?? ""}
        projectId={projectId}
      />

      {/* Skip Option */}
      <button onClick={next} className="text-gray-500 text-sm underline">
        Skip this step →
      </button>
    </div>
  );
}
