"use client";

import { useState } from "react";
import { X } from "lucide-react";
import { apiFetch } from "@/utils/api";

interface Props {
  open: boolean;
  onClose: () => void;
  onCreated: () => Promise<void>; // reload project list
  createdBy: string; // user email
}

export default function CreateProjectModal({
  open,
  onClose,
  onCreated,
  createdBy,
}: Props) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  if (!open) return null;

  async function submit() {
    setError("");
    if (!name.trim()) {
      setError("Project name is required.");
      return;
    }

    setLoading(true);

    const body = {
      name,
      description,
      created_by: createdBy,
    };

    const res = await apiFetch(
      `${process.env.NEXT_PUBLIC_API_URL}/projects`,
      {
        method: "POST",
        body: JSON.stringify(body),
      }
    );

    setLoading(false);

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      setError(err.detail || "Could not create project.");
      return;
    }

    setName("");
    setDescription("");

    await onCreated();
    onClose();
  }

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center">
      <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-lg relative">
        
        {/* Close */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-500 hover:text-gray-700"
        >
          <X size={20} />
        </button>

        {/* Title */}
        <h2 className="text-xl font-semibold mb-4">
          Create New Project
        </h2>

        {/* Name */}
        <label className="text-sm font-medium">Project Name</label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full mt-1 mb-4 p-2 rounded-md border"
          placeholder="My Website Automation"
        />

        {/* Description */}
        <label className="text-sm font-medium">Description</label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="w-full mt-1 p-2 h-24 rounded-md border"
          placeholder="Short description about this project"
        />

        {error && (
          <p className="text-red-500 text-sm mt-3">{error}</p>
        )}

        {/* Footer */}
        <div className="mt-6 flex justify-end gap-3">
          <button
            className="px-4 py-2 bg-gray-200 rounded-md"
            onClick={onClose}
          >
            Cancel
          </button>

          <button
            onClick={submit}
            disabled={loading}
            className="px-5 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700"
          >
            {loading ? "Creating..." : "Create Project"}
          </button>
        </div>
      </div>
    </div>
  );
}
