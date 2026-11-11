import { BookOpen, FileText, ScanSearch } from 'lucide-react';

const features = [
  { title: 'Teach Product Knowledge', icon: BookOpen, body: 'The planned training workflow extracts terminology, roles, rules and exceptions from narrated screen recordings. Review source-linked claims, answer questions and approve the knowledge the agent can use.', status: 'Planned', id: 'knowledge' },
  { title: 'Design Tests from Stories', icon: FileText, body: 'Add a story and acceptance criteria, review scenarios and generate test cases. Keep purpose, steps and explicit expected results visible during human review.', status: 'Existing workflow', id: 'test-design' },
  { title: 'Execute with Evidence', icon: ScanSearch, body: 'The target visual executor follows approved steps and evaluates expected results. A controlled synthetic browser demo is available during development; customer-app execution is a later delivery gate.', status: 'Controlled demo', id: 'visual-execution' },
];

export default function Features() {
  return <section id="product" className="lp-section lp-tint">
    <div className="lp-container">
      <p className="lp-eyebrow">A connected QA workflow</p>
      <h2>Understand the Product.<br />Define What Should Happen.</h2>
      <p className="lp-intro">Recordings supply product knowledge. Stories and acceptance criteria define what a test must verify.</p>
      <div className="lp-grid lp-three">{features.map(({ title, icon: Icon, body, status, id }) =>
        <article id={id} className="lp-card lp-workflow-card" key={id}>
          <Icon aria-hidden="true" /><span className="lp-tag">{status}</span><h3>{title}</h3><p>{body}</p>
        </article>)}</div>
      <p className="lp-banner">Human review connects each stage, from approved knowledge to expected results and corrections.</p>
    </div>
  </section>;
}
