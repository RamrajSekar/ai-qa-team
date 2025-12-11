import type { Metadata } from 'next';
import './globals.css';
import RootProviders from '@/components/providers/RootProviders';

export const metadata: Metadata = {
  title: 'QA Squad',
  description: 'AI-powered test-automation companion',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[var(--qs-bg)] text-[var(--qs-text)]">
        {/* ✅ All routes (marketing, app, auth) now share the same providers */}
        <RootProviders>{children}</RootProviders>
      </body>
    </html>
  );
}
