// components/marketing/Pricing.tsx
const Pricing = () => {
  return (
    <section
      id='pricing'
      className='border-b border-[var(--qs-border)] bg-[var(--qs-bg-soft)]'
    >
      <div className='max-w-6xl mx-auto px-6 py-16 md:py-20'>
        <h2 className='text-3xl md:text-4xl font-bold text-[var(--qs-text)]'>
          Start small, grow with your team.
        </h2>
        <p className='mt-3 text-base text-[var(--qs-text-soft)] max-w-xl'>
          Usage-based limits that match your team&apos;s stage. Upgrade when you&apos;re ready.
        </p>

        <div className='mt-12 grid gap-8 md:grid-cols-3'>
          {/* Free */}
          <div className='rounded-2xl border border-[var(--qs-border)] bg-[var(--qs-bg)] p-6 shadow flex flex-col'>
            <h3 className='text-xl font-semibold text-[var(--qs-text)]'>Free</h3>
            <p className='mt-1 text-sm text-[var(--qs-text-soft)]'>
              For individuals or small teams evaluating QA Squad.
            </p>
            <p className='mt-6 text-4xl font-bold text-[var(--qs-text)]'>$0</p>
            <p className='text-sm text-[var(--qs-text-soft)]'>forever</p>
            <ul className='mt-6 space-y-2 text-sm text-[var(--qs-text-soft)] flex-1'>
              <li>1 Project</li>
              <li>5 User Stories</li>
              <li>10 Scenarios</li>
              <li>20 Executions / month</li>
              <li>1 Team Member</li>
              <li>3 AI Generations</li>
              <li>10 Basic Testcases</li>
              <li>No Medium or Advanced Tests</li>
            </ul>
            <a
              href='/signup?plan=free'
              className='mt-6 rounded-xl border border-[var(--qs-border)] bg-[var(--qs-bg)] px-4 py-3 text-center text-sm font-semibold text-[var(--qs-text)] hover:bg-[var(--qs-bg-soft)] shadow'
            >
              Get started free
            </a>
          </div>

          {/* Pro */}
          <div className='relative rounded-2xl border-4 border-violet-600 bg-[var(--qs-bg)] p-6 shadow-2xl flex flex-col scale-[1.02]'>
            <span className='absolute -top-3 right-5 rounded-full bg-violet-600 px-3 py-1 text-xs font-bold text-white shadow'>
              Most popular
            </span>
            <h3 className='text-xl font-semibold text-[var(--qs-text)]'>Pro</h3>
            <p className='mt-1 text-sm text-[var(--qs-text-soft)]'>
              For growing QA teams that need more volume.
            </p>
            <p className='mt-6 text-4xl font-bold text-[var(--qs-text)]'>$49</p>
            <p className='text-sm text-[var(--qs-text-soft)]'>per month</p>
            <ul className='mt-6 space-y-2 text-sm text-[var(--qs-text-soft)] flex-1'>
              <li>10 Projects</li>
              <li>100 User Stories</li>
              <li>200 Scenarios</li>
              <li>1,000 Executions / month</li>
              <li>5 Team Members</li>
              <li>50 AI Generations</li>
              <li>500 Basic Testcases</li>
              <li>200 Medium Testcases</li>
              <li>100 Advanced Testcases</li>
            </ul>
            <a
              href='/signup?plan=pro'
              className='mt-6 rounded-xl bg-violet-600 px-4 py-3 text-center text-sm font-semibold text-white hover:bg-violet-700 shadow-lg'
            >
              Choose Pro
            </a>
          </div>

          {/* Enterprise */}
          <div className='rounded-2xl border border-[var(--qs-border)] bg-[var(--qs-bg)] p-6 shadow flex flex-col'>
            <h3 className='text-xl font-semibold text-[var(--qs-text)]'>Enterprise</h3>
            <p className='mt-1 text-sm text-[var(--qs-text-soft)]'>
              For organizations needing custom workflows and support.
            </p>
            <p className='mt-6 text-4xl font-bold text-[var(--qs-text)]'>Let&apos;s talk</p>
            <p className='text-sm text-[var(--qs-text-soft)]'>custom pricing</p>
            <ul className='mt-6 space-y-2 text-sm text-[var(--qs-text-soft)] flex-1'>
              <li>1,000+ Projects</li>
              <li>1,000 User Stories</li>
              <li>2,000 Scenarios</li>
              <li>10,000 Executions / month</li>
              <li>20 Team Members</li>
              <li>Unlimited AI Generations</li>
              <li>Unlimited Basic/Medium/Advanced Tests</li>
              <li>Private deployment options (future)</li>
            </ul>
            <a
              href='/contact'
              className='mt-6 rounded-xl border border-[var(--qs-border)] bg-[var(--qs-bg)] px-4 py-3 text-center text-sm font-semibold text-[var(--qs-text)] hover:bg-[var(--qs-bg-soft)] shadow'
            >
              Contact sales
            </a>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Pricing;
