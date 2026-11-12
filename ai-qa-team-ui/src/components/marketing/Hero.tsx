import Link from 'next/link';
import { ArrowDown, BookOpen, Layers3 } from 'lucide-react';
import ThemeToggle from '@/components/ThemeToggle';

export default function Hero() {
  return <>
    <a className="lp-skip" href="#product">Skip to content</a>
    <header className="lp-header">
      <a className="lp-brand" href="#"><span>QA</span> AI QA Team</a>
      <nav aria-label="Public navigation">
        <a href="#product">Product</a><a href="#knowledge">Product Knowledge</a>
        <Link href="/pricing">Pricing</Link><a href="#how-it-works">How It Works</a><a href="#roadmap">Progress</a>
      </nav>
      <div className="lp-actions"><ThemeToggle /><Link href="/auth?mode=login">Sign In</Link>
        <Link className="lp-button" href="/auth?mode=signup">Create Account</Link></div>
    </header>
    <section className="lp-hero lp-container" aria-labelledby="hero-title">
      <div>
        <p className="lp-eyebrow">Product knowledge. Clear expectations. Human approval.</p>
        <h1 id="hero-title">From Product Understanding to <span>Tests You Can Trust</span></h1>
        <p className="lp-lead">We’re building a human-supervised AI QA agent that learns your product from narrated recordings, turns stories and acceptance criteria into reviewed tests, and executes approved steps visually.</p>
        <div className="lp-actions"><Link className="lp-button" href="/auth?mode=signup">Create Account</Link>
          <a className="lp-button lp-secondary" href="#how-it-works">Explore the Workflow <span aria-hidden="true">↗</span></a></div>
        <p className="lp-note">Designed for teams to describe workflows and expected results in plain language.</p>
        <p className="lp-status">In development · Story-based test generation and a controlled browser demo are available. Recording-based knowledge and customer-app visual execution are planned.</p>
      </div>
      <figure className="lp-control">
        <figcaption className="lp-eyebrow">Target workflow · Illustrative preview</figcaption>
        <div className="lp-prompt">“Here’s how our product works.”</div>
        <ArrowDown aria-hidden="true" className="lp-arrow" size={18} />
        <div className="lp-control-inner">
          <div className="lp-control-title"><Layers3 size={22} aria-hidden="true" /><strong>AI QA Team</strong><span className="lp-tag">Human supervised</span></div>
          <ol className="lp-flow">{['Review product knowledge', 'Add story and acceptance criteria', 'Generate and approve tests', 'Execute and review evidence'].map((step, index) =>
            <li key={step}><span>{String(index + 1).padStart(2, '0')}</span>{step}</li>)}</ol>
        </div>
        <div className="lp-repo"><BookOpen aria-hidden="true" size={24} /><div><strong>You approve what the agent knows and tests</strong><p>Reviewed corrections create new versions.</p></div></div>
      </figure>
    </section>
  </>;
}
