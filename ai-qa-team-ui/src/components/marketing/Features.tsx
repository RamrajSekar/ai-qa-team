import { Bug, Database, ScanSearch } from 'lucide-react';

const strategies = [
  ['Happy', '2'],
  ['Boundary', '4'],
  ['Negative', '2'],
  ['Cross-field', '2'],
];

const dataLayers = [
  ['Schema', 'Types, required fields, formats, and bounds'],
  ['Field intelligence', 'Valid, boundary, invalid, and synthetic values'],
  ['Cross-field rules', 'Related values that stay logically consistent'],
  ['Relational state', 'Data and application state across connected records'],
];

export default function Features() {
  return (
    <>
      <section id="product" className="lp-section lp-tint">
        <div className="lp-container">
          <p className="lp-eyebrow">Two entry points. The same foundation.</p>
          <h2>
            One QA Control Plane.
            <br />
            Two Powerful Workflows.
          </h2>
          <p className="lp-intro">
            Designed to make the automation you already own easier to find, prepare, and use.
          </p>

          <div className="lp-grid lp-two">
            <article id="bug-reproduction" className="lp-card lp-workflow-card">
              <Bug aria-hidden="true" />
              <span className="lp-tag">Planned workflow</span>
              <h3>Reproduce a Bug</h3>
              <p>
                Paste a bug and its Steps to Reproduce. AI QA Team is designed to match it to
                existing automation, resolve only the bug-specific data, and prepare the clearest
                path to reproduction.
              </p>
              <ol className="lp-mini-flow">
                {[
                  'Paste a bug',
                  'Match existing automation',
                  'Resolve bug data',
                  'Prepare / run',
                  'Collect evidence',
                ].map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ol>
              <strong>
                See whether coverage is full, partial, or missing—without inventing automation that
                does not exist.
              </strong>
            </article>

            <article className="lp-card lp-workflow-card">
              <ScanSearch aria-hidden="true" />
              <span className="lp-tag">Planned workflow</span>
              <h3>Explore QA Coverage</h3>
              <p>
                Describe what you want to test. AI QA Team is designed to match existing tests,
                propose a focused strategy, and create the validated datasets needed to explore it.
              </p>
              <ol className="lp-mini-flow">
                {[
                  'Describe the goal',
                  'Match an existing test',
                  'Plan focused cases',
                  'Generate data',
                  'Preview / run',
                ].map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ol>
              <div className="lp-strategies" aria-label="Example test strategy">
                {strategies.map(([name, count]) => (
                  <div key={name}>
                    <span>{name}</span>
                    <strong>{count}</strong>
                  </div>
                ))}
              </div>
              <p className="lp-note">
                Example: 10 data cases. The strategy selects what to test; the data engine creates
                the rows.
              </p>
            </article>
          </div>

          <p className="lp-banner">
            Use the automation you already own. Resolve or generate only what the testing intent
            requires.
          </p>
        </div>
      </section>

      <section id="test-data" className="lp-section lp-container">
        <div className="lp-compact-heading">
          <div>
            <p className="lp-eyebrow">Compact, context-aware test data</p>
            <h2>Test Data That Understands More Than Field Types</h2>
          </div>
          <Database aria-hidden="true" size={30} />
        </div>
        <p className="lp-intro">
          Building toward validated data that respects schemas, field behavior, business rules,
          and related application state.
        </p>
        <div className="lp-grid lp-four">
          {dataLayers.map(([title, description]) => (
            <article className="lp-card lp-compact-card" key={title}>
              <h3>{title}</h3>
              <p>{description}</p>
            </article>
          ))}
        </div>
        <p className="lp-note">
          Planned capability. Existing automation remains responsible for the setup and data it
          already handles.
        </p>
      </section>
    </>
  );
}
