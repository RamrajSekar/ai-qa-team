"use client";

import EnvironmentCard from "./EnvironmentCard";
import type { Environment } from "@/types/environment";

interface Props {
  environments: Environment[];
  refresh: () => void;
  onEdit: (env: Environment) => void;
}

export default function EnvironmentList({ environments, refresh, onEdit }: Props) {
  if (environments.length === 0) {
    return <p className="text-gray-500 text-sm">No environments added yet.</p>;
  }

  return (
    <div className="grid grid-cols-1 gap-3">
      {environments.map((env) => (
        <EnvironmentCard
          key={env.env_id}
          env={env}
          refresh={refresh}
          onEdit={onEdit}
        />
      ))}
    </div>
  );
}
