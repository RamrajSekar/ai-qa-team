import AgentPanel from './AgentPanel';

export default function Workflow() {
  return (
    <section
      id="how-it-works"
      className="border-b border-[var(--qs-border)] bg-[var(--qs-bg)]"
    >
      <div className="mx-auto flex max-w-6xl flex-col gap-10 px-4 py-16 md:px-6 lg:flex-row">
        <div className="flex-1">
          <h2 className="text-3xl font-semibold tracking-tight text-[var(--qs-text)] md:text-4xl">
            How QA Squad fits into your workflow.
          </h2>
          <p className="mt-3 max-w-2xl text-sm text-[var(--qs-text-soft)] md:text-base">
            From captured user journeys to automated cloud executions — with human approvals at every
            critical step.
          </p>

          <div className="mt-10 grid gap-6 md:grid-cols-2">
            {[
              {
                step: '01. Capture',
                title: 'Record user flows',
                body: 'Use the recorder to capture authentic user journeys. QA Squad turns them into structured steps and stories.',
              },
              {
                step: '02. Generate',
                title: 'AI Scenario generation',
                body: 'AI transforms recordings or stories into candidate scenarios. You get drafts ready for review — no manual typing.',
              },
              {
                step: '03. Review',
                title: 'Approve or deny scenarios',
                body: 'QA engineers remain the gatekeepers. Only approved scenarios are eligible for test generation.',
              },
              {
                step: '04. Automate',
                title: 'Generate tests & execute',
                body: 'Approved scenarios become runnable test cases you can execute in the cloud. Local runners are on the roadmap.',
              },
            ].map((card) => (
              <div
                key={card.step}
                className="rounded-2xl border border-[var(--qs-border)] bg-[var(--qs-bg-soft)] p-5 shadow-sm"
              >
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-violet-600">
                  {card.step}
                </p>
                <h3 className="mt-2 text-lg font-semibold text-[var(--qs-text)]">{card.title}</h3>
                <p className="mt-2 text-sm text-[var(--qs-text-soft)]">{card.body}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="lg:w-auto lg:flex-none">
          <AgentPanel />
        </div>
      </div>
    </section>
  );
}
