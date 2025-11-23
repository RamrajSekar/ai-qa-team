'use client';

import { useEffect, useState } from 'react';

type Theme = 'light' | 'dark';

const STORAGE_KEY = 'qa-squad-theme';

export default function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>('light');
  const [mounted, setMounted] = useState(false);

  // Initialize from system preference + localStorage
  useEffect(() => {
    let initial: Theme = 'light';

    if (typeof window !== 'undefined') {
      const stored = window.localStorage.getItem(STORAGE_KEY) as Theme | null;
      if (stored === 'light' || stored === 'dark') {
        initial = stored;
      } else if (window.matchMedia?.('(prefers-color-scheme: dark)').matches) {
        initial = 'dark';
      }
      setTheme(initial);
      document.documentElement.classList.toggle('dark', initial === 'dark');
      setMounted(true);
    }
  }, []);

  const toggleTheme = () => {
    const next: Theme = theme === 'light' ? 'dark' : 'light';
    setTheme(next);
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(STORAGE_KEY, next);
      document.documentElement.classList.toggle('dark', next === 'dark');
    }
  };

  if (!mounted) return null;

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className="flex items-center gap-1 rounded-full border border-[var(--qs-border)] bg-[var(--qs-bg-soft)] px-3 py-1 text-xs font-medium text-[var(--qs-text-soft)] hover:bg-[var(--qs-bg)] transition"
    >
      <span>{theme === 'light' ? '☀️ Light' : '🌙 Dark'}</span>
    </button>
  );
}
