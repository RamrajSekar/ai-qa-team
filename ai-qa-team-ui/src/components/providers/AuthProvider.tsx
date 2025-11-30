"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
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

  loginWithEmail: (email: string, password: string) => Promise<{ ok: boolean }>;
  signupWithEmail: (
    name: string,
    email: string,
    password: string
  ) => Promise<{ ok: boolean }>;
  loginWithGoogle: () => void;

  logout: () => Promise<void>;
  refreshSubscription: () => Promise<void>;

  pendingPlan: string | null;
  setPendingPlan: (p: string | null) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

// ---------------------------------------------------------------------
// PROVIDER
// ---------------------------------------------------------------------
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<any>(null);

  const [authOpen, setAuthOpen] = useState(false);
  const [mode, setMode] = useState<"login" | "signup">("login");

  const [pendingPlan, setPendingPlan] = useState<string | null>(null);

  // ---------------------------------------------------------------------
  // AUTH MODAL CONTROL
  // ---------------------------------------------------------------------
  const openAuth = (desiredMode?: "login" | "signup") => {
    if (desiredMode) setMode(desiredMode);
    setAuthOpen(true);
  };

  const closeAuth = () => setAuthOpen(false);

  const switchMode = (m: "login" | "signup") => setMode(m);

  // ---------------------------------------------------------------------
  // LOGIN WITH EMAIL
  // ---------------------------------------------------------------------
  const loginWithEmail = async (email: string, password: string) => {
    try {
      const res = await apiFetch("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });

      if (!res.ok) return { ok: false };

      // backend returns { ok: true, user }
      setUser(res.data.user);

      // fetch latest user + subscription
      await refreshSubscription();

      closeAuth();
      return { ok: true };
    } catch (err) {
      console.error("loginWithEmail failed:", err);
      return { ok: false };
    }
  };

  // ---------------------------------------------------------------------
  // SIGNUP WITH EMAIL
  // ---------------------------------------------------------------------
  const signupWithEmail = async (
    name: string,
    email: string,
    password: string
  ) => {
    try {
      const res = await apiFetch("/auth/signup", {
        method: "POST",
        body: JSON.stringify({ name, email, password }),
      });

      if (!res.ok) return { ok: false };

      setUser(res.data.user);
      await refreshSubscription();

      closeAuth();
      return { ok: true };
    } catch (err) {
      console.error("signupWithEmail failed:", err);
      return { ok: false };
    }
  };

  // ---------------------------------------------------------------------
  // GOOGLE LOGIN
  // ---------------------------------------------------------------------
  const loginWithGoogle = () => {
    if (typeof window === "undefined") return;
    const cb = `${window.location.origin}/oauth/callback`;
    window.location.href =
      `${process.env.NEXT_PUBLIC_API_URL}/auth/google?callback=` +
      encodeURIComponent(cb);
  };

  // ---------------------------------------------------------------------
  // LOGOUT
  // ---------------------------------------------------------------------
  const logout = async () => {
    try {
      await apiFetch("/auth/logout", { method: "POST" });
    } catch (e) {
      console.error("Logout failed", e);
    }
    setUser(null);
    window.location.href = "/";
  };

  // ---------------------------------------------------------------------
  // REFRESH SUBSCRIPTION + USER
  // ---------------------------------------------------------------------
  const refreshSubscription = useCallback(async () => {
    try {
      const res = await apiFetch("/auth/me");

      if (res.ok && res.data?.user) {
        setUser(res.data.user);
      }
    } catch (err) {
      console.error("refreshSubscription failed:", err);
    }
  }, []);

  // ---------------------------------------------------------------------
  // LOAD USER ON PAGE START
  // ---------------------------------------------------------------------
  useEffect(() => {
    (async () => {
      try {
        const res = await apiFetch("/auth/me");
        if (res.ok && res.data?.user) setUser(res.data.user);
      } catch {
        /* not logged in */
      }
    })();
  }, []);

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

// ---------------------------------------------------------------------
// HOOK
// ---------------------------------------------------------------------
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
