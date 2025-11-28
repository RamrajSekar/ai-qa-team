"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

export default function CreateProjectPage() {
  const API_URL = process.env.NEXT_PUBLIC_API_URL as string;
  const router = useRouter();

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  async function createProject() {
    const res = await fetch(`${API_URL}/projects`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, description }),
    });

    if (!res.ok) return toast.error("Failed to create project");

    const data = await res.json();
    toast.success("Project created!");
    router.push(`/projects/${data.project_id}`);
  }

  return (
    <div className="max-w-xl mx-auto p-10">
      <h1 className="text-2xl font-semibold mb-6">Create Project</h1>

      <div className="space-y-4">
        <input
          className="w-full border rounded-md px-3 py-2"
          placeholder="Project Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />

        <textarea
          className="w-full border rounded-md px-3 py-2"
          placeholder="Description (optional)"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />

        <button
          onClick={createProject}
          className="w-full bg-purple-600 text-white py-2 rounded-md hover:bg-purple-700"
        >
          Create Project
        </button>
      </div>
    </div>
  );
}
