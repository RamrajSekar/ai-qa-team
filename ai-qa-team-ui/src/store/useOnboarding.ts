'use client';

import { create } from 'zustand';

type OnboardingStatus = {
  completed: boolean;
  setCompleted: (value: boolean) => void;
};

export const useOnboarding = create<OnboardingStatus>((set) => ({
  completed: false,
  setCompleted: (value) => set({ completed: value }),
}));
