"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { apiFetch } from "@/utils/api";
import { useAuth } from "@/components/providers/AuthProvider";

export default function CreateProjectPage() {
  const router = useRouter();
  const { user } = useAuth();

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  // Redirect if not logged in
  useEffect(() => {
    if (!user) {
      toast.error("You must be logged in to create a project");
      router.push("/login");
    }
  }, [user, router]);

  async function createProject() {
    if (!user) {
      toast.error("You must be logged in");
      return;
    }

    if (!name.trim()) {
      toast.error("Project name is required");
      return;
    }

    const payload = {
      name,
      description,
      created_by: user.email,
    };

    const res = await apiFetch("/projects", {
      method: "POST",
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      console.error("Project creation failed", res.data);
      toast.error(res.data?.detail || "Project creation failed");
      return;
    }

    toast.success("Project created!");
    router.push("/projects/${res.data.project_id}");
  }

  if (!user) {
    return (
      <div className="p-10 text-center text-gray-500">
        Redirecting to login...
      </div>
    );
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
