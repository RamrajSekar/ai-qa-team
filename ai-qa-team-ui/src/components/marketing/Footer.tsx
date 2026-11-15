import Link from "next/link";
export default function Footer() {
  return <footer className="lp-footer lp-container"><p>© {new Date().getFullYear()} AI QA Team</p><nav aria-label="Footer navigation"><Link href="/pricing">Pricing</Link><Link href="/auth?mode=login">Sign in</Link><Link href="/auth?mode=signup">Get started</Link></nav></footer>;
}
