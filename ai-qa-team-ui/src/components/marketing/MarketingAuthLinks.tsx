"use client";
import Link from "next/link";
import { useAuth } from "@/components/providers/AuthProvider";

export default function MarketingAuthLinks({ signup = true }: { signup?: boolean }) {
  const { user } = useAuth();
  return user ? <Link className="lp-button" href="/dashboard">Open workspace</Link> : <>
    <Link href="/auth?mode=login">Sign in</Link>
    {signup && <Link className="lp-button" href="/auth?mode=signup">Get started</Link>}
  </>;
}
