// components/marketing/Features.tsx
const Features = () => {
  return (
    <section
      id='features'
      className='border-b border-[var(--qs-border)] bg-[var(--qs-bg-soft)]'
    >
      <div className='max-w-6xl mx-auto px-6 py-16 md:py-20'>
        <h2 className='text-3xl md:text-4xl font-bold text-[var(--qs-text)]'>
          Core capabilities in the MVP.
        </h2>
        <p className='mt-3 max-w-2xl text-base text-[var(--qs-text-soft)]'>
          Start with a lean, reliable base that grows with your team and workflows.
        </p>

        <div className='mt-12 grid gap-8 md:grid-cols-2'>
          <div className='rounded-2xl border border-[var(--qs-border)] bg-[var(--qs-bg)] p-6 shadow'>
            <h3 className='text-xl font-semibold text-[var(--qs-text)]'>
              AI Test Generator (human-gated)
            </h3>
            <p className='mt-2 text-sm text-[var(--qs-text-soft)]'>
              Convert approved scenarios into structured, repeatable test cases. Humans decide what gets automated, keeping quality and intent aligned.
            </p>
          </div>

          <div className='rounded-2xl border border-[var(--qs-border)] bg-[var(--qs-bg)] p-6 shadow'>
            <h3 className='text-xl font-semibold text-[var(--qs-text)]'>Cloud execution engine</h3>
            <p className='mt-2 text-sm text-[var(--qs-text-soft)]'>
              Run tests in QA Squad&apos;s managed environment — no local setup or infrastructure to maintain.
              <br />
              <span className='text-violet-600 font-medium'>
                Local execution runner is on the roadmap.
              </span>
            </p>
          </div>

          <div className='rounded-2xl border border-[var(--qs-border)] bg-[var(--qs-bg)] p-6 shadow'>
            <h3 className='text-xl font-semibold text-[var(--qs-text)]'>
              Scenario & test management
            </h3>
            <p className='mt-2 text-sm text-[var(--qs-text-soft)]'>
              Track Stories, Scenarios, approvals, and tests in one place. See what&apos;s drafted, under review, and automated at a glance.
            </p>
          </div>

          <div className='rounded-2xl border border-[var(--qs-border)] bg-[var(--qs-bg)] p-6 shadow'>
            <h3 className='text-xl font-semibold text-[var(--qs-text)]'>Live execution logs</h3>
            <p className='mt-2 text-sm text-[var(--qs-text-soft)]'>
              View step-by-step execution output, including what passed and where failures occurred, to speed up debugging and triage.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Features;
