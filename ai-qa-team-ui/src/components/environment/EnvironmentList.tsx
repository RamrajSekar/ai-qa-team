"use client";

import EnvironmentCard from "./EnvironmentCard";
import { Environment } from "@/types/environment";

interface Props {
  environments: Environment[];
  loading: boolean;
  onEdit: (env: Environment) => void;
  refresh: () => Promise<void>;
}

export default function EnvironmentList({
  environments,
  loading,
  onEdit,
  refresh,
}: Props) {
  if (loading)
    return <p className="text-gray-400">Loading environments...</p>;

  if (environments.length === 0)
    return (
      <p className="text-gray-500 border rounded-md p-4 text-center">
        No environments found.
      </p>
    );

  return (
    <div className="grid grid-cols-1 gap-4">
      {environments.map((env) => (
        <EnvironmentCard
          key={env.id}
          env={env}
          onEdit={() => onEdit(env)}
          refresh={refresh}   // ✔ valid placement
        />
      ))}
    </div>
  );
}
