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

interface APIOptions extends RequestInit {
  retry?: boolean; // used internally
}

async function apiFetch(url: string, options: APIOptions = {}) {
  const opts: RequestInit = {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  };

  let res = await fetch(url, opts);

  // If unauthorized -> try silent refresh once
  if (res.status === 401 && !options.retry) {
    console.log("🔄 Access token expired, trying refresh...");

    const refresh = await fetch(`${API_URL}/auth/refresh`, {
      method: "POST",
      credentials: "include",
    });

    if (refresh.ok) {
      console.log("🔐 Refresh successful. Retrying original request...");
      return apiFetch(url, { ...options, retry: true });
    }

    console.log("❌ Refresh failed.");
    return res;
  }

  return res;
}

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

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();

  const [user, setUser] = useState<User | null>(null);
  const [authOpen, setAuthOpen] = useState(false);
  const [mode, setMode] = useState<AuthMode>("login");
  const [loading, setLoading] = useState(false);
  const [pendingPlan, setPendingPlan] = useState<string | null>(null);
  /* ------------- Modal Controls ------------- */
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

  /* ------------- LOGIN ------------- */
  async function loginWithEmail(email: string, password: string) {
  setLoading(true);
  try {
    const res = await fetch(`${API_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
      credentials: 'include', // cookie-based
    });

    const data = await res.json();
    setLoading(false);

    if (!res.ok) {
      toast.error(data.detail || 'Login failed');
      return { ok: false };
    }

    const userData = data.user ?? data;
    setUser(userData);

    const status = userData.onboarding_status ?? 'not_started';
    if (status === 'completed') {
      router.push('/dashboard');
    } else {
      router.push('/onboarding');
    }

    toast.success('Logged in successfully!');
    closeAuth();
    return { ok: true };
  } catch (err) {
    console.error(err);
    setLoading(false);
    return { ok: false, message: 'Network error' };
  }
}

  /* ------------- SIGNUP ------------- */
  async function signupWithEmail(name: string, email: string, password: string) {
  setLoading(true);
  try {
    const res = await fetch(`${API_URL}/auth/signup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, password }),
      credentials: 'include',
    });

    const data = await res.json();
    setLoading(false);

    if (!res.ok) {
      toast.error(data.detail || 'Signup failed');
      return { ok: false };
    }

    const userData = data.user ?? data;
    setUser(userData);

    // New users always start onboarding
    router.push('/onboarding');
    toast.success('Account created!');
    closeAuth();

    return { ok: true };
  } catch (err) {
    console.error(err);
    setLoading(false);
    return { ok: false, message: 'Network error' };
  }
}

  /* ------------- OAUTH ------------- */
  function loginWithGoogle() {
    window.location.href = `${API_URL}/auth/google/login`;
  }

  /* ------------- SUBSCRIPTION REFRESH ------------- */
  async function refreshSubscription() {
  if (!user) return;

  // 🚫 Prevent spamming check-plan repeatedly
  if (user.subscription && Object.keys(user.subscription).length > 0) {
      return; // already have subscription
    }

    try {
      const res = await apiFetch(`${API_URL}/auth/check-plan`);
      if (!res.ok) return;

      const data = await res.json();
      setUser((prev) =>
        prev ? { ...prev, subscription: data.subscription } : prev
      );
    } catch (err) {
      console.error("Failed to refresh subscription", err);
    }
  }

  /* ------------- USER LOGOUT ------------- */
  async function logout() {
  try {
    await apiFetch(`${API_URL}/auth/logout`, {
      method: "POST",
      retry: false,
    });
  } catch (err) {
    console.warn("Logout request failed, forcing local logout.");
  }

  setUser(null);
  toast.success("Logged out");
  router.push("/");
}

  /* ------------- RESTORE SESSION ------------- */
  useEffect(() => {
  async function loadSession() {
      try {
        const res = await fetch(`${API_URL}/auth/me`, {
          credentials: 'include',
        });
        if (res.ok) {
          const data = await res.json();
          const userData = data.user ?? data;
          setUser(userData);
        }
      } catch (err) {
        console.error('Failed to load session', err);
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

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
