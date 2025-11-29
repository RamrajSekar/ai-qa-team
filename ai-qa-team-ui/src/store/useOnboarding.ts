"use client";

import { create } from "zustand";

export interface OnboardingStore {
  completed: boolean;
  currentStep: number;
  setStep: (step: number) => void;
  setCompleted: () => void;
}

export const useOnboarding = create<OnboardingStore>((set) => ({
  completed: false,
  currentStep: 0,

  setStep: (step) => set({ currentStep: step }),

  setCompleted: () => set({ completed: true }),
}));
