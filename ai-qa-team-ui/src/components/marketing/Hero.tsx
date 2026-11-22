import MarketingAuthLinks from "@/components/marketing/MarketingAuthLinks";
import Link from "next/link";
import ThemeToggle from "@/components/ThemeToggle";

export default function Hero() {
  return <>
    <a className="lp-skip" href="#product">Skip to content</a>
    <header className="lp-header"><Link className="lp-brand" href="/"><span>QA</span> AI QA Team</Link>
      <nav aria-label="Public navigation"><a href="#how-it-works">How it works</a><Link href="/pricing">Pricing</Link></nav>
      <div className="lp-actions"><ThemeToggle /><MarketingAuthLinks /></div>
    </header>
    <section id="product" className="lp-hero lp-container" aria-labelledby="hero-title">
      <div><p className="lp-eyebrow">AI-assisted test design</p><h1 id="hero-title">Clearer stories.<br /><span>Better test cases.</span></h1>
        <p className="lp-lead">Give your QA team an assistant that understands your product, finds gaps in stories and drafts tests for your review.</p>
        <div className="lp-actions"><Link className="lp-button" href="/auth?mode=signup">Try the workspace</Link><Link className="lp-button lp-secondary" href="/pricing">View pricing</Link></div>
        <p className="lp-note">You review the knowledge. You approve the tests.</p>
      </div>
      <figure className="lp-control"><figcaption className="lp-eyebrow">Illustrative workflow</figcaption><div className="lp-prompt">“Only managers can approve a refund.”</div><ol className="lp-flow"><li><span>01</span>Capture the product rule</li><li><span>02</span>Check the story for missing details</li><li><span>03</span>Draft scenarios and test steps</li><li><span>04</span>Your team reviews and approves</li></ol></figure>
    </section>
  </>;
}
