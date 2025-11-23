import "./globals.css";
import type { ReactNode } from "react";

export const metadata = {
  title: "QA Squad",
  description: "AI-assisted, human-approved test automation.",
};

export default function RootLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <html lang="en" className="theme-transition">
      <body>{children}</body>
    </html>
  );
}
