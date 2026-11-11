import Link from 'next/link';

export default function Footer() {
  return <>
    <section className="lp-section lp-container lp-final">
      <p className="lp-eyebrow">Build shared understanding before execution</p>
      <h2>Your Product Knowledge.<br />Your Approved Expectations.</h2>
      <p className="lp-intro">Start with projects, stories and acceptance criteria. Follow our progress toward recording-trained knowledge and supervised visual QA.</p>
      <div className="lp-actions"><Link className="lp-button" href="/auth?mode=signup">Create Account</Link>
        <a className="lp-button lp-secondary" href="#how-it-works">Explore the Workflow</a></div>
      <p className="lp-note">Account creation opens the existing workspace. See delivery progress for current capabilities.</p>
    </section>
    <footer className="lp-footer lp-container"><p>© {new Date().getFullYear()} AI QA Team</p>
      <nav aria-label="Footer navigation"><a href="#product">Product</a><a href="#roadmap">Progress</a><Link href="/auth?mode=login">Sign In</Link></nav>
    </footer>
  </>;
}
