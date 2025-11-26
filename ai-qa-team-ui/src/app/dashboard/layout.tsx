'use client';

import React from 'react';
import {Sidebar} from '@/components/layout/Sidebar';
import { Topbar } from '@/components/layout/Topbar';

// type DashboardLayoutProps = {
//   children: React.ReactNode;
// };

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen bg-gradient-to-br from-indigo-50 to-indigo-100">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Topbar />
        <main className="p-6">{children}</main>
      </div>
    </div>
  );
}
