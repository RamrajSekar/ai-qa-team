"use client";

import { Eye, Trash2, PlayCircle } from "lucide-react";
import type { Recording } from "@/types/recorder";

interface Props {
  recordings: Recording[];
  onView: (recording: Recording) => void;
  onDelete?: (recording: Recording) => void; // optional for future use
  onReplay?: (recording: Recording) => void; // optional for future use
}

export default function RecordingsTable({
  recordings,
  onView,
  onDelete,
  onReplay,
}: Props) {
  return (
    <div className="border rounded-lg bg-white shadow-sm overflow-hidden">
      <div className="p-4 border-b bg-gray-50">
        <h2 className="text-lg font-semibold">Recordings</h2>
      </div>

      {recordings.length === 0 ? (
        <div className="p-4 text-gray-500">No recordings created yet.</div>
      ) : (
        <table className="min-w-full text-sm">
          <thead className="bg-gray-100 text-left">
            <tr>
              <th className="px-4 py-2">Recording ID</th>
              <th className="px-4 py-2">Created At</th>
              <th className="px-4 py-2">Steps</th>
              <th className="px-4 py-2">Actions</th>
            </tr>
          </thead>

          <tbody>
            {recordings.map((rec) => (
              <tr key={rec.recording_id} className="border-t">
                <td className="px-4 py-2 font-medium">{rec.recording_id}</td>
                <td className="px-4 py-2">
                  {new Date(rec.created_at).toLocaleString()}
                </td>
                <td className="px-4 py-2">{rec.steps?.length || 0}</td>

                <td className="px-4 py-2">
                  <div className="flex items-center gap-3">

                    {/* VIEW */}
                    <button
                      onClick={() => onView(rec)}
                      className="flex items-center gap-1 text-blue-600 hover:text-blue-800"
                    >
                      <Eye size={16} /> View
                    </button>

                    {/* REPLAY (future) */}
                    {onReplay && (
                      <button
                        onClick={() => onReplay(rec)}
                        className="flex items-center gap-1 text-green-600 hover:text-green-800"
                      >
                        <PlayCircle size={16} /> Replay
                      </button>
                    )}

                    {/* DELETE (future) */}
                    {onDelete && (
                      <button
                        onClick={() => onDelete(rec)}
                        className="flex items-center gap-1 text-red-600 hover:text-red-800"
                      >
                        <Trash2 size={16} /> Delete
                      </button>
                    )}

                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
