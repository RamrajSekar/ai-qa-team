"use client";

import { createContext, useContext, useState, ReactNode } from "react";

export interface User {
  name?: string;
  email?: string;
  subscription?: any;
}

interface AuthContextType {
  user: User | null;
  setUser: (u: User | null) => void;

  authOpen: boolean;
  openAuth: () => void;
  closeAuth: () => void;

  mode: "login" | "signup";
  switchMode: (m: "login" | "signup") => void;

  pendingPlan: string | null;
  setPendingPlan: (p: string | null) => void;

  loginWithEmail: (email: string, password: string) => Promise<void>;
  signupWithEmail: (email: string, password: string, name: string) => Promise<void>;
  loginWithGoogle: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);

  const [authOpen, setAuthOpen] = useState(false);
  const [mode, setMode] = useState<"login" | "signup">("login");

  const [pendingPlan, setPendingPlan] = useState<string | null>(null);

  function openAuth() {
    setAuthOpen(true);
  }
  function closeAuth() {
    setAuthOpen(false);
  }
  function switchMode(m: "login" | "signup") {
    setMode(m);
  }

  /* ---------- Email login ---------- */
  async function loginWithEmail(email: string, password: string) {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/auth/login`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    if (res.ok) {
      const data = await res.json();
      setUser(data.user);
      closeAuth();
    } else {
      throw new Error("Login failed");
    }
  }

  /* ---------- Email signup ---------- */
  async function signupWithEmail(email: string, password: string, name: string) {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/auth/signup`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, email, password }),
    });

    if (res.ok) {
      const data = await res.json();
      setUser(data.user);
      closeAuth();
    } else {
      throw new Error("Signup failed");
    }
  }

  /* ---------- Google OAuth ---------- */
  function loginWithGoogle() {
    window.location.href = `${process.env.NEXT_PUBLIC_API_URL}/auth/google/login`;
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        setUser,

        authOpen,
        openAuth,
        closeAuth,

        mode,
        switchMode,

        pendingPlan,
        setPendingPlan,

        loginWithEmail,
        signupWithEmail,
        loginWithGoogle,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
