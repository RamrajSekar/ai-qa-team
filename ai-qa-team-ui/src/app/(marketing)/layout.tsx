import type { ReactNode } from 'react';
import '../globals.css';

export default function MarketingLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-[var(--qs-bg)] text-[var(--qs-text)]">
      {children}
    </div>
  );
}
