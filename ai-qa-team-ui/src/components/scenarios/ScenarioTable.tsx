"use client";

import { IconAction } from "@/components/ui/icon-action";
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
    <div className="workspace-table-scroll design-table" role="region" aria-label="Story scenarios" tabIndex={0}>
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
              <td className="p-3">{s.requirements_review_required ? `Needs review (${s.requirements_review_release})` : s.approved ? "Approved" : "Pending approval"}{["story_only_provisional","approved_story_only"].includes(s.design_basis || "") && <p>Provisional · story-only</p>}{s.target_release && <p>{s.target_release}</p>}</td>
              <td className="p-3 text-center">
                <div className="flex items-center justify-center gap-3">
                  <IconAction action="view" label="View" onClick={() => onView(s)} />

                  <IconAction action="edit" label="Edit" onClick={() => onEdit(s)} />

                  <IconAction action="delete" label="Delete" onClick={() => onDelete(s)} />
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
