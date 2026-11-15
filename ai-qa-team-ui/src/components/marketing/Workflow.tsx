const steps = [
  ["Teach your product", "Add product notes and review what the QA Agent learned."],
  ["Check your stories", "Find ambiguity, missing details and conflicts with approved knowledge."],
  ["Review your tests", "Generate scenarios and test cases with clear steps and expected results."],
];
export default function Workflow() {
  return <section id="how-it-works" className="lp-section lp-container"><p className="lp-eyebrow">How it works</p><h2>From product knowledge to test cases.</h2><div className="lp-grid lp-three">{steps.map(([title,body],index)=><article className="lp-card" key={title}><p className="lp-eyebrow">0{index+1}</p><h3>{title}</h3><p>{body}</p></article>)}</div><p className="lp-note">Test Design beta. Recording uploads and general automated browser execution are not included.</p></section>;
}
