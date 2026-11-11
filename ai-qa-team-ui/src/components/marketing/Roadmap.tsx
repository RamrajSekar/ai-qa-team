const milestones = [
  ['Available foundations', 'Projects, environments, stories, scenario review and test-case generation provide the existing authoring workflow. Feature availability depends on deployment configuration.'],
  ['Current development', 'One approved synthetic sequence can run through the project UI with browser evidence. Visual targeting experiments and reliability qualification continue.'],
  ['Next delivery gates', 'Recording ingestion, source-linked approved knowledge, versioned test traceability and authorized staging execution complete the next parts of the journey.'],
];

export default function Roadmap() {
  return <section id="roadmap" className="lp-section lp-tint"><div className="lp-container">
    <p className="lp-eyebrow">Delivery progress</p><h2>A Focused Path to a Supervised QA Pilot</h2>
    <p className="lp-intro">We’re working toward one application module, a small set of workflows and reviewed cases, with evidence and human control at each stage.</p>
    <div className="lp-grid lp-three">{milestones.map(([title, copy]) =>
      <article className="lp-card" key={title}><h3>{title}</h3><p>{copy}</p></article>)}</div>
    <p className="lp-note">Parallel execution remains in the MVP plan. Browser reliability and concurrency qualification are ongoing.</p>
  </div></section>;
}
