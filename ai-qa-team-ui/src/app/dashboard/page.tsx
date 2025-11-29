"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/providers/AuthProvider";
import CreateProjectModal from "@/components/projects/CreateProjectModal";
import OnboardingModal from "@/components/onboarding/OnboardingModal";
import { apiFetch } from "@/utils/api";
import Link from "next/link";

export default function DashboardPage() {
  const { user, setUser } = useAuth();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);

  const [openModal, setOpenModal] = useState(false);
  const [openOnboarding, setOpenOnboarding] = useState(false);

  async function loadProjects() {
    setLoading(true);
    const res = await apiFetch(`${process.env.NEXT_PUBLIC_API_URL}/projects`);
    if (res.ok) setProjects(await res.json());
    setLoading(false);
  }

  // Refresh user
  async function refreshUser() {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/auth/me`, {
        credentials: "include",
      });

      if (res.ok) {
        const data = await res.json();
        setUser(data.user);
      }
    } catch (e) {
      console.error("refreshUser failed", e);
    }
  }

  useEffect(() => {
    loadProjects();
  }, []);

  useEffect(() => {
    if (user?.onboarding?.onboarding_status !== "completed") {
      setOpenOnboarding(true);
    }
  }, [user]);

  if (!user) return <p className="p-6">Loading...</p>;

  return (
    <div className="relative p-6 space-y-10">

      {openOnboarding && (
        <OnboardingModal
          user={user}
          refreshUser={refreshUser}
          onClose={() => setOpenOnboarding(false)}
        />
      )}

      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Dashboard</h2>

        <button
          onClick={() => setOpenModal(true)}
          className="bg-purple-600 text-white px-4 py-2 rounded-md hover:bg-purple-700"
        >
          + Create Project
        </button>
      </div>

      {/* CHARTS AREA */}
      <div className="grid grid-cols-2 gap-4 mb-10">
        <div className="border p-4 rounded-lg bg-white shadow">Project Chart 1</div>
        <div className="border p-4 rounded-lg bg-white shadow">Project Chart 2</div>
      </div>

      {/* PROJECT LIST */}
      ...
    </div>
  );
}
