'use client';

import React, { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Github, Linkedin, Goal } from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL as string;

interface AuthModalProps {
  open: boolean;
  onClose: () => void;
}

export default function AuthModal({ open, onClose }: AuthModalProps) {
  const [mode, setMode] = useState<'login' | 'signup'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  // (Email/password handlers can be wired later)

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-sm rounded-2xl p-6 bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 shadow-2xl">
        <DialogHeader>
          <DialogTitle className="text-xl font-bold text-center text-neutral-900 dark:text-neutral-100">
            {mode === 'login' ? 'Welcome back' : 'Create your account'}
          </DialogTitle>
        </DialogHeader>

        <div className="mt-4 space-y-3">
          {/* OAuth Buttons */}
          <OAuthButton provider="google" label="Continue with Google" icon={Goal} />
          <OAuthButton provider="github" label="Continue with GitHub" icon={Github} />
          <OAuthButton
            provider="linkedin"
            label="Continue with LinkedIn"
            icon={Linkedin}
          />

          <div className="relative py-3 text-center text-xs text-neutral-500 dark:text-neutral-400">
            <span className="bg-white dark:bg-neutral-900 px-2">
              or continue with email
            </span>
          </div>

          <Input
            placeholder="Email"
            type="email"
            className="bg-white dark:bg-neutral-800 border-neutral-300 dark:border-neutral-700 text-neutral-900 dark:text-neutral-100"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />

          <Input
            placeholder="Password"
            type="password"
            className="bg-white dark:bg-neutral-800 border-neutral-300 dark:border-neutral-700 text-neutral-900 dark:text-neutral-100"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />

          <Button className="w-full mt-2" size="lg">
            {mode === 'login' ? 'Log in' : 'Sign up'}
          </Button>
        </div>

        <p className="mt-4 text-center text-sm text-neutral-600 dark:text-neutral-400">
          {mode === 'login' ? (
            <>
              Don&apos;t have an account?{' '}
              <span
                onClick={() => setMode('signup')}
                className="text-primary cursor-pointer"
              >
                Sign up
              </span>
            </>
          ) : (
            <>
              Already have an account?{' '}
              <span
                onClick={() => setMode('login')}
                className="text-primary cursor-pointer"
              >
                Log in
              </span>
            </>
          )}
        </p>
      </DialogContent>
    </Dialog>
  );
}

interface OAuthButtonProps {
  provider: 'google' | 'github' | 'linkedin';
  label: string;
  icon?: React.ComponentType<React.SVGProps<SVGSVGElement>>;
}

function OAuthButton({ provider, label, icon: Icon }: OAuthButtonProps) {
  const handleOAuth = () => {
    if (!API_URL) {
      console.error('Missing NEXT_PUBLIC_API_URL');
      return;
    }
    window.location.href = `${API_URL}/auth/${provider}/login`;
  };

  return (
    <button
      onClick={handleOAuth}
      className="flex items-center gap-2 w-full px-4 py-2 border rounded-md hover:bg-gray-100"
    >
      {Icon && <Icon className="w-5 h-5" />}
      <span>{label}</span>
    </button>
  );
}
