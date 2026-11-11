"use client"
import { create } from "zustand"

type AuthModalState = {
  isOpen: boolean
  mode: "login" | "signup"
  open: (mode: "login" | "signup") => void
  close: () => void
}

export const useAuthModal = create<AuthModalState>((set) => ({
  isOpen: false,
  mode: "login",
  open: (mode) => set({ isOpen: true, mode }),
  close: () => set({ isOpen: false }),
}))
