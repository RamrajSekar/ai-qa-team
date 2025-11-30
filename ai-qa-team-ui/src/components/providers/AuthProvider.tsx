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
import { apiFetch } from "@/utils/api";
const API_URL = process.env.NEXT_PUBLIC_API_URL as string;

export type AuthMode = "login" | "signup";

/* -----------------------------------------------------
   Auth Context Types
----------------------------------------------------- */
export interface AuthContextType {
  user: User | null;
  loading: boolean;
  authOpen: boolean;

  openAuth: (mode?: AuthMode) => void;
  closeAuth: () => void;
  mode: AuthMode;
  switchMode: (m: AuthMode) => void;

  loginWithEmail: (email: string, password: string) => Promise<any>;
  signupWithEmail: (name: string, email: string, password: string) => Promise<any>;
  loginWithGoogle: () => void;

  refreshSubscription: () => Promise<void>;
  setUser: (u: User | null) => void;
  logout: () => void;
  pendingPlan: string | null;
  setPendingPlan: (plan: string | null) => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

/* -----------------------------------------------------
   Auth Provider Component
----------------------------------------------------- */
export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();

  const [user, setUser] = useState<User | null>(null);
  const [authOpen, setAuthOpen] = useState(false);
  const [mode, setMode] = useState<AuthMode>("login");
  const [loading, setLoading] = useState(false);
  const [pendingPlan, setPendingPlan] = useState<string | null>(null);

  /* ------------------ Modal Controls ------------------ */
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

  /* ---------------------- LOGIN ----------------------- */
  async function loginWithEmail(email: string, password: string) {
    setLoading(true);
    try {
      const res = await apiFetch(`${API_URL}/auth/login`, {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });

      setLoading(false);

      if (!res.ok) {
        toast.error(res.data?.detail || "Invalid login credentials");
        return { ok: false };
      }

      const userData = res.data.user ?? res.data;
      setUser(userData);

      router.push(
        userData.onboarding_status === "completed"
          ? "/dashboard"
          : "/onboarding"
      );

      toast.success("Logged in successfully!");
      closeAuth();
      return { ok: true };
    } catch (err) {
      console.error(err);
      setLoading(false);
      toast.error("Network error");
      return { ok: false };
    }
  }

  /* ---------------------- SIGNUP ---------------------- */
  async function signupWithEmail(name: string, email: string, password: string) {
    setLoading(true);
    try {
      const res = await apiFetch(`${API_URL}/auth/signup`, {
        method: "POST",
        body: JSON.stringify({ name, email, password }),
      });

      setLoading(false);

      if (!res.ok) {
        toast.error(res.data?.detail || "Signup failed");
        return { ok: false };
      }

      const userData = res.data.user ?? res.data;
      setUser(userData);

      router.push("/onboarding");
      toast.success("Account created!");
      closeAuth();

      return { ok: true };
    } catch (err) {
      console.error(err);
      setLoading(false);
      toast.error("Network error");
      return { ok: false };
    }
  }

  /* ---------------------- GOOGLE LOGIN ---------------------- */
  function loginWithGoogle() {
    window.location.href = `${API_URL}/auth/google/login`;
  }

  /* ------------------ SUBSCRIPTION CHECK ------------------ */
  async function refreshSubscription() {
    if (!user) return;

    if (user.subscription && Object.keys(user.subscription).length > 0) {
      return; // already loaded
    }

    try {
      const res = await apiFetch(`${API_URL}/auth/check-plan`);
      if (!res.ok) return;

      const result = res.data;
      setUser((prev) =>
        prev ? { ...prev, subscription: result.subscription } : prev
      );
    } catch (err) {
      console.error("Failed to refresh subscription", err);
    }
  }

  /* ---------------------- LOGOUT ---------------------- */
  async function logout() {
    try {
      await apiFetch(`${API_URL}/auth/logout`, { method: "POST" });
    } catch {
      console.warn("Logout request failed — forcing local logout.");
    }

    setUser(null);
    toast.success("Logged out");
    router.push("/");
  }

  /* ------------------- RESTORE SESSION ------------------- */
  useEffect(() => {
    async function loadSession() {
      try {
        const res = await apiFetch(`${API_URL}/auth/me`);

        if (res.ok) {
          const userData = res.data.user ?? res.data;
          setUser(userData);
        }
      } catch (err) {
        console.error("Session restore failed", err);
      }
    }

    loadSession();
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        authOpen,
        openAuth,
        closeAuth,
        mode,
        switchMode,
        loginWithEmail,
        signupWithEmail,
        loginWithGoogle,
        refreshSubscription,
        setUser,
        logout,
        pendingPlan,
        setPendingPlan,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

/* -----------------------------------------------------
   Hook
----------------------------------------------------- */
export function useAuth() {
  // console.log("useAuth executed at:", new Error().stack);
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
