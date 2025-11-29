"use client";

import { useState, useEffect } from "react";
import { StepContainer } from "@/components/onboarding/StepContainer";
import { StepHeader } from "@/components/onboarding/StepHeader";
import StepFooter from "@/components/onboarding/StepFooter";

import EnvironmentList from "@/components/environment/EnvironmentList";
import EnvironmentModal from "@/components/environment/EnvironmentModal";
import { Environment } from "@/types/environment";
import { apiFetch } from "@/utils/api";

export default function Step2() {
  const [projectId, setProjectId] = useState<string>("");
  const [environments, setEnvironments] = useState<Environment[]>([]);
  const [loading, setLoading] = useState(true);

  // Modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [editMode, setEditMode] = useState<"create" | "edit">("create");
  const [selectedEnv, setSelectedEnv] = useState<Environment | null>(null);

  /* -----------------------------------------------
   *  LOAD PROJECT CREATED IN STEP 1
   * --------------------------------------------- */
  useEffect(() => {
    const stored = localStorage.getItem("onboarding_project_id");
    if (!stored) return;
    setProjectId(stored);
  }, []);

  /* -----------------------------------------------
   *  LOAD ENVIRONMENTS FOR THIS PROJECT
   * --------------------------------------------- */
  async function loadEnvironments() {
    if (!projectId) return;

    setLoading(true);
    const res = await apiFetch(
      `${process.env.NEXT_PUBLIC_API_URL}/environments?project_id=${projectId}`
    );

    if (res.ok) {
      const data: Environment[] = await res.json();
      setEnvironments(data);
    }
    setLoading(false);
  }

  useEffect(() => {
    loadEnvironments();
  }, [projectId]);

  /* -----------------------------------------------
   *  OPEN MODAL (CREATE)
   * --------------------------------------------- */
  function openCreate() {
    setSelectedEnv(null);
    setEditMode("create");
    setModalOpen(true);
  }

  /* -----------------------------------------------
   *  OPEN MODAL (EDIT)
   * --------------------------------------------- */
  function openEdit(env: Environment) {
    setSelectedEnv(env);
    setEditMode("edit");
    setModalOpen(true);
  }

  return (
    <StepContainer>
      <StepHeader
        title="Add Environments"
        subtitle="Configure your QA, staging, dev or production environments."
      />

      {/* CREATE BUTTON */}
      <div className="flex justify-end mb-4">
        <button
          onClick={openCreate}
          className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-md"
        >
          + Add Environment
        </button>
      </div>

      {/* ENV LIST */}
      <EnvironmentList
        environments={environments}
        loading={loading}
        onEdit={openEdit}
        refresh={loadEnvironments}
      />

      {/* MODAL */}
      <EnvironmentModal
        open={modalOpen}
        mode={editMode}
        projectId={projectId}
        env={selectedEnv}
        onClose={() => setModalOpen(false)}
        onSaved={loadEnvironments}
      />

      <StepFooter
        next="/onboarding/step-3"
        back="/onboarding/step-1"
        disableNext={environments.length === 0}
      />
    </StepContainer>
  );
}
