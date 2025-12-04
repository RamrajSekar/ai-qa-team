"use client";

import { useState } from "react";
import StepFooter from "../StepFooter";
import { Github, Gitlab, GitBranch, ArrowRight } from "lucide-react";

interface StepTestImportProps {
  next: () => void;
  back: () => void;
}

export default function StepTestImport({ next, back }: StepTestImportProps) {
  const [provider, setProvider] = useState<string | null>(null);

  const providers = [
    { id: "github", name: "GitHub", icon: <Github size={20} /> },
    { id: "gitlab", name: "GitLab", icon: <Gitlab size={20} /> },
    { id: "bitbucket", name: "Bitbucket", icon: <GitBranch size={20} /> },
  ];

  const handleConnect = () => {
    if (!provider) return;

    // Placeholder until OAuth is added
    alert(`OAuth redirect for: ${provider.toUpperCase()}`);

    // Skip now — import is optional
    next();
  };

  return (
    <div className="p-6 space-y-6">
      <h2 className="font-bold text-xl mb-2">Import Existing Tests (Optional)</h2>
      <p className="text-gray-500 text-sm">
        Connect your GitHub, GitLab, or Bitbucket repository to automatically import testcases, scenarios, and automation files.
      </p>

      {/* Provider Selection */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-4">
        {providers.map((p) => (
          <button
            key={p.id}
            onClick={() => setProvider(p.id)}
            className={`
              flex flex-col items-center gap-2 border p-4 rounded-lg cursor-pointer
              ${provider === p.id ? "border-purple-600 bg-purple-50" : "border-gray-300 hover:bg-gray-100"}
            `}
          >
            {p.icon}
            <span className="font-medium">{p.name}</span>
          </button>
        ))}
      </div>

      <div className="mt-6">
        <button
          disabled={!provider}
          onClick={handleConnect}
          className={`
            w-full py-3 rounded-md flex items-center justify-center gap-2 text-white
            ${provider ? "bg-purple-600 hover:bg-purple-700" : "bg-gray-300 cursor-not-allowed"}
          `}
        >
          Connect {provider ? provider.toUpperCase() : ""} Repo
          <ArrowRight size={18} />
        </button>

        <button
          onClick={next}
          className="mt-4 w-full text-sm text-gray-500 hover:text-gray-700"
        >
          Skip This Step →
        </button>
      </div>

      <StepFooter onNext={next} onBack={back} />
    </div>
  );
}
