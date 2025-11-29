"use client";

import { useState } from "react";
import StepLayout from "./StepLayout";

export default function Step1Project() {
  const [name, setName] = useState("");

  return (
    <StepLayout
      title="Create Your First Project"
      description="Name your QA project to get started."
    >
      <input
        className="w-full border rounded p-2"
        placeholder="Project Name"
        value={name}
        onChange={(e) => setName(e.target.value)}
      />
    </StepLayout>
  );
}
