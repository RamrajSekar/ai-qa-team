"use client";

import { Eye, Pencil, Trash2 } from "lucide-react";
import type { Scenario } from "@/types/scenario";

interface Props {
  scenarios: Scenario[];
  onEdit: (scenario: Scenario) => void;
  onDelete: (scenario: Scenario) => void;
  onView: (scenario: Scenario) => void;
}

export default function ScenarioTable({ scenarios, onEdit, onDelete, onView }: Props) {
  if (!scenarios || scenarios.length === 0) {
    return (
      <div className="border rounded-md p-4 text-gray-500 bg-gray-50">
        No scenarios created yet.
      </div>
    );
  }

  return (
    <div className="overflow-hidden border rounded-md bg-white shadow-sm">
      <table className="w-full text-sm">
        <thead className="bg-gray-100 text-gray-600 uppercase text-xs">
          <tr>
            <th className="p-3 text-left">Scenario ID</th>
            <th className="p-3 text-left">Title</th>
            <th className="p-3 text-left">Status</th>
            <th className="p-3 text-center w-36">Actions</th>
          </tr>
        </thead>

        <tbody>
          {scenarios.map((s) => (
            <tr key={s.scenario_id} className="border-t hover:bg-gray-50">
              <td className="p-3">{s.scenario_id}</td>
              <td className="p-3">{s.title}</td>
              <td className="p-3">{s.approved ? "Approved" : "Pending approval"}</td>
              <td className="p-3 text-center">
                <div className="flex items-center justify-center gap-3">
                  <button
                    onClick={() => onView(s)}
                    className="text-blue-600 hover:text-blue-800"
                    title="View"
                  >
                    <Eye size={16} />
                  </button>

                  <button
                    onClick={() => onEdit(s)}
                    className="text-purple-600 hover:text-purple-800"
                    title="Edit"
                  >
                    <Pencil size={16} />
                  </button>

                  <button
                    onClick={() => onDelete(s)}
                    className="text-red-600 hover:text-red-800"
                    title="Delete"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
