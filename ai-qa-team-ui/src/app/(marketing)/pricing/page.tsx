import MarketingAuthLinks from "@/components/marketing/MarketingAuthLinks";
import type { Metadata } from "next";
import Link from "next/link";
import "@/components/marketing/marketing.css";
import Pricing from "@/components/marketing/Pricing";

export const metadata: Metadata = {title: "Plans and pricing | AI QA Team", description: "Compare Free, Team, Business and Enterprise account plans for Test Design. Paid plans are planned; no online checkout."};

export default function PricingPage() {
  return <main className="public-landing"><header className="lp-header"><Link className="lp-brand" href="/">AI QA Team</Link><nav aria-label="Pricing navigation"><Link href="/">Product</Link><MarketingAuthLinks signup={false} /></nav></header><Pricing /></main>;
}
