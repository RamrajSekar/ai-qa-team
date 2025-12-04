"use client";

import EnvironmentList from "./EnvironmentList";
import EnvironmentModal from "./EnvironmentModal";
import { useState } from "react";
import { Plus } from "lucide-react";
import type { Environment } from "@/types/environment";

interface Props {
  projectId: string;
  environments: Environment[];
  refresh: () => void;
}

export default function EnvironmentTab({ projectId, environments, refresh }: Props) {
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Environment | null>(null);

  return (
    <div className="space-y-4">
      <button
        onClick={() => {
          setEditing(null);
          setOpen(true);
        }}
        className="bg-purple-600 text-white px-3 py-2 rounded-md flex items-center gap-1"
      >
        <Plus size={18} /> Add Environment
      </button>

      <EnvironmentList
        environments={environments}
        refresh={refresh}
        onEdit={(env) => {
          setEditing(env);
          setOpen(true);
        }}
      />

      <EnvironmentModal
        open={open}
        mode={editing ? "edit" : "create"}
        projectId={projectId}
        env={editing}
        onSaved={refresh}
        onClose={() => setOpen(false)}
      />
    </div>
  );
}
