// components/marketing/Roadmap.tsx
const Roadmap = () => {
  return (
    <section className='border-b border-[var(--qs-border)] bg-[var(--qs-bg)]'>
      <div className='max-w-6xl mx-auto px-6 py-16 md:py-20'>
        <h2 className='text-3xl md:text-4xl font-bold text-[var(--qs-text)]'>
          On the roadmap.
        </h2>
        <p className='mt-3 max-w-2xl text-base text-[var(--qs-text-soft)]'>
          After the MVP, we&apos;re focused on deeper coverage, integrations, and test resilience.
        </p>

        <div className='mt-12 grid gap-8 md:grid-cols-3'>
          <div className='rounded-2xl border border-[var(--qs-border)] bg-[var(--qs-bg-soft)] p-6 shadow'>
            <h4 className='text-lg font-semibold text-[var(--qs-text)]'>Local execution runner</h4>
            <p className='mt-1 text-sm text-[var(--qs-text-soft)]'>
              Run QA Squad test cases on your own machine or CI runners and sync results back to the platform.
            </p>
          </div>

          <div className='rounded-2xl border border-[var(--qs-border)] bg-[var(--qs-bg-soft)] p-6 shadow'>
            <h4 className='text-lg font-semibold text-[var(--qs-text)]'>CI/CD integrations</h4>
            <p className='mt-1 text-sm text-[var(--qs-text-soft)]'>
              GitHub Actions, GitLab CI, and Bitbucket pipelines to trigger executions as part of your delivery workflow.
            </p>
          </div>

          <div className='rounded-2xl border border-[var(--qs-border)] bg-[var(--qs-bg-soft)] p-6 shadow'>
            <h4 className='text-lg font-semibold text-[var(--qs-text)]'>Multi-browser execution</h4>
            <p className='mt-1 text-sm text-[var(--qs-text-soft)]'>
              Extend coverage beyond Chromium with Firefox and WebKit support.
            </p>
          </div>

          <div className='rounded-2xl border border-[var(--qs-border)] bg-[var(--qs-bg-soft)] p-6 shadow'>
            <h4 className='text-lg font-semibold text-[var(--qs-text)]'>AI self-healing tests</h4>
            <p className='mt-1 text-sm text-[var(--qs-text-soft)]'>
              Automatically adapt brittle locators when the DOM changes to keep runs stable.
            </p>
          </div>

          <div className='rounded-2xl border border-[var(--qs-border)] bg-[var(--qs-bg-soft)] p-6 shadow'>
            <h4 className='text-lg font-semibold text-[var(--qs-text)]'>Visual snapshots</h4>
            <p className='mt-1 text-sm text-[var(--qs-text-soft)]'>
              Capture screenshots and traces for rich failure analysis and debugging.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Roadmap;
