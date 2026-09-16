"use client";

import { Globe, Pencil, Trash2, Shield } from "lucide-react";
import type { Environment } from "@/types/environment";
import { apiFetch } from "@/utils/api";

interface Props {
  env: Environment;
  refresh: () => void;
  onEdit: (env: Environment) => void;
  canManage?: boolean;
}

export default function EnvironmentCard({ env, refresh, onEdit, canManage = true }: Props) {
  async function handleDelete() {
    if (!confirm(`Delete environment "${env.env_type}"?`)) return;

    const res = await apiFetch(`/environments/${env.env_id}`, {
      method: "DELETE",
    });

    if (res.ok) refresh();
  }

  return (
    <div className="border rounded-lg p-4 shadow-sm bg-white">
      <div className="flex justify-between items-start">
        <div>
          <h3 className="font-semibold text-lg flex items-center gap-2">
            <Globe size={18} /> {env.env_type}
          </h3>
          <p className="text-xs text-gray-500">{env.base_url}</p>
        </div>

        {canManage && <div className="flex gap-2">
          <button
            onClick={() => onEdit(env)}
            className="p-2 rounded-md hover:bg-gray-100"
          >
            <Pencil size={16} />
          </button>
          <button
            onClick={handleDelete}
            className="p-2 rounded-md hover:bg-red-100 text-red-500"
          >
            <Trash2 size={16} />
          </button>
        </div>}
      </div>

      {env.credentials.length > 0 && (
        <div className="mt-3 text-xs text-gray-600 flex items-center gap-1">
          <Shield size={14} /> {env.credentials.length} credential set(s)
        </div>
      )}
    </div>
  );
}
