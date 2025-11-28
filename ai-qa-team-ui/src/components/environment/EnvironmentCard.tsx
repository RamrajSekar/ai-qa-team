"use client";

import { Globe, Pencil, Trash } from "lucide-react";
import { apiFetch } from "@/utils/api";
import type { Environment } from "@/types/environment";

const API_URL = process.env.NEXT_PUBLIC_API_URL as string;

interface EnvironmentCardProps {
  env: Environment;
  refresh: () => Promise<void>;
  onEdit: (env: Environment) => void;
}

export default function EnvironmentCard({
  env,
  refresh,
  onEdit,
}: EnvironmentCardProps) {
  async function remove() {
    if (!confirm("Delete this environment?")) return;

    const res = await apiFetch(`${API_URL}/environments/${env.id}`, {
      method: "DELETE",
    });

    if (res.ok) {
      await refresh();
    }
  }

  return (
    <div className="border rounded-lg p-4 flex flex-col gap-3 bg-white shadow-sm">
      {/* HEADER */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Globe className="text-gray-500" size={18} />
          <div>
            <div className="font-semibold">
              {env.env_id} · {env.env_type.toUpperCase()}
            </div>
            <div className="text-xs text-gray-500">{env.base_url}</div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-600">
            {env.default_browser}
          </span>
          {env.default_headed && (
            <span className="px-2 py-0.5 text-xs rounded-full bg-blue-50 text-blue-600">
              headed
            </span>
          )}
        </div>
      </div>

      {/* DETAILS */}
      <div className="text-xs text-gray-600 flex flex-wrap gap-2">
        {env.api_base_url && (
          <span className="px-2 py-0.5 rounded bg-gray-100">
            API: {env.api_base_url}
          </span>
        )}
        <span className="px-2 py-0.5 rounded bg-gray-100">
          auth: {env.auth_type}
        </span>
        <span className="px-2 py-0.5 rounded bg-gray-100">
          timeout: {env.default_timeout_ms}ms
        </span>
        <span className="px-2 py-0.5 rounded bg-gray-100">
          creds: {env.credentials.length}
        </span>
        <span className="px-2 py-0.5 rounded bg-gray-100">
          vars: {Object.keys(env.variables || {}).length}
        </span>
      </div>

      {/* ACTIONS */}
      <div className="flex justify-end gap-2 mt-2">
        <button
          onClick={() => onEdit(env)}
          className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded border border-gray-300 hover:bg-gray-50"
        >
          <Pencil size={14} />
          Edit
        </button>
        <button
          onClick={remove}
          className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded border border-red-200 text-red-600 hover:bg-red-50"
        >
          <Trash size={14} />
          Delete
        </button>
      </div>
    </div>
  );
}
