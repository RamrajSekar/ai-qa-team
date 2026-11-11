import { create } from "zustand";

interface OnboardingStore {
  open: boolean;
  step: number;
  start: () => void;
  next: () => void;
  back: () => void;
  close: () => void;
}

export const useOnboarding = create<OnboardingStore>((set) => ({
  open: false,
  step: 1,

  start: () => set({ open: true, step: 1 }),
  next: () => set((s) => ({ step: s.step + 1 })),
  back: () => set((s) => ({ step: Math.max(1, s.step - 1) })),
  close: () => set({ open: false }),
}));
