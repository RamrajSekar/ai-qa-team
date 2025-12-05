"use client";

import { useEffect, useState } from "react";
import { X, Download } from "lucide-react";
import { apiFetch } from "@/utils/api";

interface RepoImportModalProps {
  open: boolean;
  onClose: () => void;
  provider: string;          // github | gitlab | bitbucket
  projectId: string;
}

export default function RepoImportModal({
  open,
  onClose,
  provider,
  projectId,
}: RepoImportModalProps) {
  const [repos, setRepos] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedRepo, setSelectedRepo] = useState<string | null>(null);
  const [branch, setBranch] = useState("main");
  const [importing, setImporting] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");

  // Load user repos after OAuth
  async function loadRepos() {
    setLoading(true);
    const res = await apiFetch(`/integrations/${provider}/repos`);
    setLoading(false);

    if (res.ok) {
      setRepos(res.data || []);
    } else {
      console.error("Failed to fetch repos:", res.data || 'Unknown Error');
    }
  }

  useEffect(() => {
    if (open) loadRepos();
  }, [open]);

  async function handleImport() {
    if (!selectedRepo) return;

    setImporting(true);

    const payload = {
      repo_url: selectedRepo,
      branch,
      project_id: projectId,
    };

    const res = await apiFetch(`/integrations/${provider}/import`, {
      method: "POST",
      body: JSON.stringify(payload),
    });

    setImporting(false);

    if (res.ok) {
      setSuccessMessage("Testcases imported successfully!");
    } else {
      alert("Import failed: " + JSON.stringify(res.data));
    }
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-30">
      <div className="bg-white rounded-lg shadow-lg w-full max-w-2xl p-6 relative">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-3 right-3 text-gray-500 hover:text-gray-800"
        >
          <X size={20} />
        </button>

        <h2 className="text-xl font-semibold">
          Import Playwright Tests from {provider.toUpperCase()}
        </h2>

        <p className="text-gray-500 text-sm mt-1">
          Select a repo and branch to import test cases.
        </p>

        {/* REPO LIST */}
        <div className="mt-4 border rounded-md p-3 h-64 overflow-y-auto bg-gray-50">
          {loading ? (
            <p>Loading repositories...</p>
          ) : repos.length === 0 ? (
            <p className="text-gray-500 text-sm">No repositories found.</p>
          ) : (
            repos.map((repo: any) => (
              <div
                key={repo.full_name || repo.id}
                onClick={() => setSelectedRepo(repo.clone_url || repo.http_url || repo.links?.clone?.href)}
                className={`p-3 border rounded mb-2 cursor-pointer ${
                  selectedRepo ===
                  (repo.clone_url ||
                    repo.http_url ||
                    repo.links?.clone?.href)
                    ? "border-purple-600 bg-purple-50"
                    : "border-gray-300"
                }`}
              >
                <p className="font-medium">{repo.name}</p>
                <p className="text-xs text-gray-500">{repo.full_name}</p>
              </div>
            ))
          )}
        </div>

        {/* BRANCH */}
        <div className="mt-4">
          <label className="text-sm font-medium">Branch</label>
          <input
            value={branch}
            onChange={(e) => setBranch(e.target.value)}
            className="border rounded w-full p-2 mt-1"
            placeholder="main"
          />
        </div>

        {/* SUCCESS MESSAGE */}
        {successMessage && (
          <div className="mt-4 p-3 bg-green-100 border border-green-300 text-green-700 rounded">
            {successMessage}
          </div>
        )}

        {/* ACTION BUTTONS */}
        <div className="mt-6 flex justify-end gap-3">
          <button
            className="px-4 py-2 border rounded"
            onClick={onClose}
          >
            Cancel
          </button>

          <button
            disabled={!selectedRepo || importing}
            onClick={handleImport}
            className={`px-4 py-2 rounded text-white flex items-center gap-2 ${
              selectedRepo
                ? "bg-purple-600 hover:bg-purple-700"
                : "bg-gray-300 cursor-not-allowed"
            }`}
          >
            <Download size={18} />
            {importing ? "Importing..." : "Import Tests"}
          </button>
        </div>
      </div>
    </div>
  );
}
