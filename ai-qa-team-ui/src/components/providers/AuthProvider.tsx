// src/components/providers/AuthProvider.tsx
'use client';

import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react';
import AuthModal from '@/components/auth/AuthModal';
import type { User } from '@/types/user';

const API_URL = process.env.NEXT_PUBLIC_API_URL as string;

interface AuthContextType {
  user: User | null;
  loading: boolean;
  openAuth: () => void;
  closeAuth: () => void;
  setAuth: (user: User | null) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}

interface AuthProviderProps {
  children: ReactNode;
}

export default function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const syncUser = async () => {
      try {
        const res = await fetch(`${API_URL}/auth/me`, {
          method: 'GET',
          credentials: 'include', // send httpOnly cookies
        });

        if (!res.ok) {
          setLoading(false);
          return;
        }

        const data = await res.json();

        if (data?.email) {
          setUser({
            id: data.id ?? data._id,
            _id: data._id,
            name: data.name ?? data.full_name ?? data.email,
            email: data.email,
            provider: data.provider,
            role: data.role,
            subscription: data.subscription, // ✅ keep full subscription object
          });
        }
      } catch (err) {
        console.error('Failed to sync auth state', err);
      } finally {
        setLoading(false);
      }
    };

    syncUser();
  }, []);

  const openAuth = () => setOpen(true);
  const closeAuth = () => setOpen(false);

  const value: AuthContextType = {
    user,
    loading,
    openAuth,
    closeAuth,
    setAuth: setUser,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
      <AuthModal open={open} onClose={closeAuth} />
    </AuthContext.Provider>
  );
}
