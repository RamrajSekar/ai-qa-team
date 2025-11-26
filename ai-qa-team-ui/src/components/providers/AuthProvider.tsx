"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from "react";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import { User } from "@/types/user";

const API_URL = process.env.NEXT_PUBLIC_API_URL as string;

export type AuthMode = "login" | "signup";

export interface AuthContextType {
  user: User | null;
  authOpen: boolean;

  openAuth: (mode?: AuthMode) => void;
  closeAuth: () => void;

  mode: AuthMode;
  switchMode: (m: AuthMode) => void;

  loginWithEmail: (
    email: string,
    password: string
  ) => Promise<{ ok: boolean; message?: string }>;

  signupWithEmail: (
    name: string,
    email: string,
    password: string
  ) => Promise<{ ok: boolean; message?: string }>;

  loginWithGoogle: () => void;

  pendingPlan: string | null;
  setPendingPlan: (p: string | null) => void;

  setUser: (u: User | null) => void;

  refreshSubscription: () => Promise<void>;

  loading: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();

  const [user, setUser] = useState<User | null>(null);
  const [authOpen, setAuthOpen] = useState(false);
  const [mode, setMode] = useState<AuthMode>("login");
  const [pendingPlan, setPendingPlan] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  /* ---------------- MODAL ---------------- */
  function openAuth(reqMode?: AuthMode) {
    if (reqMode) setMode(reqMode);
    setAuthOpen(true);
  }

  function closeAuth() {
    setAuthOpen(false);
  }

  function switchMode(m: AuthMode) {
    setMode(m);
  }

  /* ---------------- EMAIL LOGIN ---------------- */
  async function loginWithEmail(email: string, password: string) {
    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/auth/login`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const data = await res.json();
      setLoading(false);

      if (!res.ok)
        return { ok: false, message: data.detail || "Invalid credentials" };

      setUser(data.user);
      console.log("AUTHPROVIDER: Logged in user =>", data.user);
      closeAuth();
      toast.success("Logged in successfully!");

      router.push("/dashboard");
      return { ok: true };
    } catch (err) {
      setLoading(false);
      return { ok: false, message: "Network error" };
    }
  }

  /* ---------------- EMAIL SIGNUP ---------------- */
  async function signupWithEmail(name: string, email: string, password: string) {
    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/auth/signup`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, password }),
      });

      const data = await res.json();
      setLoading(false);

      if (!res.ok)
        return { ok: false, message: data.detail || "Signup failed" };

      setUser(data.user);

      toast.success("Account created!");
      closeAuth();

      router.push("/dashboard");

      return { ok: true };
    } catch (err) {
      setLoading(false);
      return { ok: false, message: "Network error" };
    }
  }

  /* ---------------- GOOGLE OAUTH ---------------- */
  function loginWithGoogle() {
    window.location.href = `${API_URL}/auth/google/login`;
  }

  /* ---------------- SUBSCRIPTION REFRESH ---------------- */
  async function refreshSubscription() {
    if (!user?.email) return;

    try {
      const res = await fetch(`${API_URL}/auth/check-plan`, {
        credentials: "include",
      });
      const data = await res.json();

      if (data.subscription) {
        setUser((u) => (u ? { ...u, subscription: data.subscription } : u));
      }
    } catch (err) {
      console.log("Subscription refresh error:", err);
    }
  }

  /* ---------------- RESTORE SESSION ---------------- */
  useEffect(() => {
    async function loadSession() {
      try {
        const res = await fetch(`${API_URL}/auth/me`, {
          credentials: "include",
        });

        if (res.ok) {
          const data = await res.json();
          if (data.user) {
            console.log("AUTHPROVIDER LOAD SESSION =>", data.user);
            setUser(data.user);
          }
        }
      } catch {}
    }

    loadSession();
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        authOpen,
        openAuth,
        closeAuth,
        mode,
        switchMode,
        loginWithEmail,
        signupWithEmail,
        loginWithGoogle,
        pendingPlan,
        setPendingPlan,
        setUser,
        refreshSubscription,
        loading,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be in AuthProvider");
  return ctx;
}
