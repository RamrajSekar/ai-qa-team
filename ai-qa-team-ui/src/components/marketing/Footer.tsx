import Link from "next/link";
export default function Footer() {
  return <footer className="lp-footer lp-container"><p>© {new Date().getFullYear()} AI QA Team</p><nav aria-label="Footer navigation"><Link href="/pricing">Pricing</Link>{process.env.PUBLIC_LEGAL_PAGES_ENABLED === "true" && process.env.PUBLIC_LEGAL_OPERATOR_NAME && process.env.PUBLIC_SUPPORT_EMAIL && <><Link href="/privacy">Privacy</Link><Link href="/terms">Terms</Link><Link href="/support">Support</Link></>}<Link href="/auth?mode=login">Sign in</Link><Link href="/auth?mode=signup">Get started</Link></nav></footer>;
}
