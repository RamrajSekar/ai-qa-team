"use client";

import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
} from "react";
import { apiFetch } from "@/utils/api";

interface AuthContextValue {
  user: any;
  setUser: (u: any) => void;

  authOpen: boolean;
  openAuth: (mode?: "login" | "signup") => void;
  closeAuth: () => void;

  mode: "login" | "signup";
  switchMode: (m: "login" | "signup") => void;

  loginWithEmail: (email: string, password: string) => Promise<any>;
  signupWithEmail: (name: string, email: string, password: string) => Promise<any>;
  loginWithGoogle: () => void;

  logout: () => Promise<void>;
  refreshSubscription: () => Promise<void>;

  pendingPlan: string | null;
  setPendingPlan: (p: string | null) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<any>(null);
  const [authOpen, setAuthOpen] = useState(false);
  const openAuth = (mode?: "login" | "signup") => {
    if (mode) switchMode(mode);
    setAuthOpen(true);
  };
  const closeAuth = () => setAuthOpen(false);

  const [mode, setMode] = useState<"login" | "signup">("login");
  const switchMode = (m: "login" | "signup") => setMode(m);

  const [pendingPlan, setPendingPlan] = useState<string | null>(null);

  const loginWithGoogle = () => {
    // const redirect = `${window.location.origin}/oauth/callback`;
    window.location.href =`${process.env.NEXT_PUBLIC_API_URL}/auth/google/login`;
  };

  const refreshSubscription = useCallback(async () => {
    try {
      const res = await apiFetch("/auth/me");
      if (res.ok && res.data?.user) setUser(res.data.user);
    } catch (_) {}
  }, []);

  const logout = async () => {
    await apiFetch("/auth/logout", { method: "POST" });
    setUser(null);
    window.location.href = "/";
  };

  const loginWithEmail = async (email: string, password: string) => {
    const res = await apiFetch("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    if (res.ok) {
      setUser(res.data.user);
      closeAuth();
    }
    return res;
  };

  const signupWithEmail = async (name: string, email: string, password: string) => {
    const res = await apiFetch("/auth/signup", {
      method: "POST",
      body: JSON.stringify({ name, email, password }),
    });
    if (res.ok) {
      setUser(res.data.user);
      closeAuth();
    }
    return res;
  };

  // Load user at startup
  useEffect(() => {
    apiFetch("/auth/me").then((res) => {
      if (res.ok) setUser(res.data.user);
    });
  }, []);

  // FINAL FIX — Properly closed function now
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
        loginWithEmail,
        signupWithEmail,
        loginWithGoogle,
        logout,
        refreshSubscription,
        pendingPlan,
        setPendingPlan,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be inside AuthProvider");
  return ctx;
}
