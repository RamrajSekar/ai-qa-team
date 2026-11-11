'use client';

import React from 'react';
import { AuthProvider } from '@/components/providers/AuthProvider';
import AuthModal from '@/components/auth/AuthModal';

export default function RootProviders({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthProvider>
      {children}

      {/* ✅ Modal is available on ALL pages, but controlled by context */}
      <AuthModal />
    </AuthProvider>
  );
}
