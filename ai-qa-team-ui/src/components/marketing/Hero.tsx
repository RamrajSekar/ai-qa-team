import Link from 'next/link';
import { ArrowDown, GitBranch, Layers3 } from 'lucide-react';
import ThemeToggle from '@/components/ThemeToggle';

export default function Hero() {
  return <>
    <a className="lp-skip" href="#product">Skip to content</a>
    <header className="lp-header"><a className="lp-brand" href="#"><span>QA</span> AI QA Team</a>
      <nav aria-label="Public navigation"><a href="#product">Product</a><a href="#bug-reproduction">Bug Reproduction</a><a href="#test-data">Test Data</a><a href="#how-it-works">How It Works</a><a href="#roadmap">Roadmap</a></nav>
      <div className="lp-actions"><ThemeToggle /><Link href="/auth?mode=login">Sign In</Link><Link className="lp-button" href="/auth?mode=signup">Get Started</Link></div>
    </header>
    <section className="lp-hero lp-container" aria-labelledby="hero-title">
      <div><p className="lp-eyebrow">Your automation. A new way to use it.</p>
        <h1 id="hero-title">Turn Your Existing Test Automation Into an <span>AI-Powered QA Engine</span></h1>
        <p className="lp-lead">Give AI QA Team a bug to reproduce or a scenario to explore. We’re building a way to find your existing automation, resolve the data it needs, and prepare or orchestrate the run—without rewriting your test suite.</p>
        <div className="lp-actions"><Link className="lp-button" href="/auth?mode=signup">Get Started</Link><a className="lp-button lp-secondary" href="#how-it-works">See How It Works <span aria-hidden="true">↗</span></a></div>
        <p className="lp-note">Built around your existing automation. Robot Framework first. Playwright and Selenium planned.</p>
        <p className="lp-status">Product preview · The workflows below are planned, not live capabilities.</p>
      </div>
      <figure className="lp-control"><figcaption className="lp-eyebrow">Planned workflow / illustrative preview</figcaption>
        <div className="lp-prompt">“Reproduce this bug” <span>or</span> “Explore this scenario”</div>
        <ArrowDown aria-hidden="true" className="lp-arrow" size={18}/>
        <div className="lp-control-inner"><div className="lp-control-title"><Layers3 size={22} aria-hidden="true"/><strong>AI QA Team</strong><span className="lp-tag">Control plane</span></div>
          <ol className="lp-flow">{['Find existing automation','Resolve test data','Prepare / execute','Evidence & results'].map((step,i)=><li key={step}><span>{String(i+1).padStart(2,'0')}</span>{step}</li>)}</ol>
        </div>
        <div className="lp-repo"><GitBranch aria-hidden="true" size={24}/><div><strong>Your existing automation</strong><p>Robot Framework · Your repository stays yours</p></div><span aria-label="Two-way connection">↕</span></div>
      </figure>
    </section>
  </>;
}
