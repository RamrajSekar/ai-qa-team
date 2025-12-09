"use client";

import { X, Trash2 } from "lucide-react";

interface ConfirmDeleteModalProps {
  open: boolean;
  title?: string;
  message?: string;
  onCancel: () => void;
  onConfirm: () => Promise<void>;
}

export default function DeleteStoryModal({
  open,
  title = "Delete Story",
  message = "Are you sure you want to delete this story? This action cannot be undone.",
  onCancel,
  onConfirm,
}: ConfirmDeleteModalProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center">
      <div className="bg-white p-6 rounded-lg w-full max-w-md shadow-lg relative">

        <button onClick={onCancel} className="absolute right-4 top-4 text-gray-500">
          <X size={20} />
        </button>

        <div className="flex items-center gap-3 mb-4">
          <Trash2 size={22} className="text-red-600" />
          <h2 className="text-lg font-semibold">{title}</h2>
        </div>

        <p className="text-gray-600 mb-6">{message}</p>

        <div className="flex justify-end gap-3">
          <button onClick={onCancel} className="px-4 py-2 border rounded">
            Cancel
          </button>

          <button
            onClick={onConfirm}
            className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
          >
            Delete
          </button>
        </div>

      </div>
    </div>
  );
}
