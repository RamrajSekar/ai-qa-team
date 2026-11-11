const stages = [
  ['Train product knowledge', 'Upload narrated recordings of a bounded product workflow. The target training pipeline links extracted knowledge to its source.'],
  ['Review, clarify and approve', 'Correct knowledge and resolve unknowns before approval. Teach-back is optional within this review.'],
  ['Add a story and acceptance criteria', 'Describe the behavior to test. The planned knowledge checks surface conflicts for review before generating tests.'],
  ['Generate, review and approve tests', 'Review natural-language steps and explicit expected results. The target versioning workflow links each case to its story, acceptance criteria and approved knowledge.'],
  ['Execute and review evidence', 'Run approved steps within defined limits. Compare observed behavior with the approved expectations and review uncertain results.'],
  ['Approve corrections', 'Review proposed changes and create successor versions. Preserve earlier approvals and the evidence for historical runs.'],
];

export default function Workflow() {
  return <section id="how-it-works" className="lp-section lp-container">
    <p className="lp-eyebrow">How it works · Target workflow</p>
    <h2>From Product Knowledge to Reviewed Evidence</h2>
    <div className="lp-grid lp-three">{stages.map(([title, body], index) =>
      <article className="lp-card" key={title}><p className="lp-eyebrow">{String(index + 1).padStart(2, '0')}</p><h3>{title}</h3><p>{body}</p></article>)}</div>
    <h3 className="lp-subheading">You Decide What the Agent Should Know and Verify</h3>
    <p className="lp-intro">The full journey is our delivery target. Human approval governs business knowledge, test expectations and material corrections.</p>
    <div className="lp-grid lp-two">
      <article className="lp-card"><h4>AI proposes</h4><p>Knowledge extraction, clarification, test drafts, visual targets and explanations.</p></article>
      <article className="lp-card"><h4>The platform enforces</h4><p>Project access, approval gates, allowed actions, budgets, evidence handling and exact comparisons.</p></article>
    </div>
  </section>;
}
