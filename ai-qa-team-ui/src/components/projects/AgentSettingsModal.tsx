"use client";

import { useState } from "react";
import { apiFetch } from "@/utils/api";

interface AgentSettingsModalProps {
  open: boolean;
  onClose: () => void;
  projectId: string;
  initialAgents: Record<string, any>;
  onUpdated: () => void;
}

export default function AgentSettingsModal({
  open,
  onClose,
  projectId,
  initialAgents,
  onUpdated,
}: AgentSettingsModalProps) {
  const [agents, setAgents] = useState(initialAgents || {});
  const [loading, setLoading] = useState(false);

  if (!open) return null;

  const handleSave = async () => {
    try {
      setLoading(true);

      const res = await apiFetch(`/projects/${projectId}/agents`, {
        method: "PATCH",
        body: JSON.stringify(agents),
      });

      if (res.ok) {
        onUpdated();
        onClose();
      }
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (agent: string, field: string, value: string) => {
    setAgents((prev) => ({
      ...prev,
      [agent]: {
        ...prev[agent],
        [field]: value,
      },
    }));
  };

  const AGENT_TYPES = ["recorder", "builder", "executor"];

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-white p-6 rounded-xl shadow-lg w-[420px]">
        <h2 className="text-lg font-semibold mb-4">Agent Settings</h2>

        <div className="space-y-4 max-h-[60vh] overflow-y-auto pr-2">
          {AGENT_TYPES.map((agent) => (
            <div key={agent} className="border rounded-lg p-3">
              <h3 className="text-sm font-semibold capitalize mb-2">
                {agent} Agent
              </h3>

              <input
                type="text"
                placeholder="API Key"
                value={agents?.[agent]?.api_key || ""}
                onChange={(e) =>
                  handleChange(agent, "api_key", e.target.value)
                }
                className="w-full border rounded-md p-2 text-sm mb-2"
              />

              <input
                type="text"
                placeholder="Base URL"
                value={agents?.[agent]?.base_url || ""}
                onChange={(e) =>
                  handleChange(agent, "base_url", e.target.value)
                }
                className="w-full border rounded-md p-2 text-sm"
              />
            </div>
          ))}
        </div>

        <div className="flex justify-end gap-2 mt-5">
          <button
            onClick={onClose}
            className="px-4 py-2 border rounded-md"
            disabled={loading}
          >
            Cancel
          </button>

          <button
            onClick={handleSave}
            className="px-4 py-2 bg-purple-600 text-white rounded-md"
            disabled={loading}
          >
            {loading ? "Saving..." : "Save Changes"}
          </button>
        </div>
      </div>
    </div>
  );
}
