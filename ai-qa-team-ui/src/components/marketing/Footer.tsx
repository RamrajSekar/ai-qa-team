"use client";
console.log("Hero render SSR from C");
const Footer = () => {
  const currentYear = new Date().getFullYear();

  return (
    <footer className='bg-[var(--qs-bg)] border-t border-[var(--qs-border)] py-10'>
      <div className='max-w-6xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-3 text-xs text-[var(--qs-text-soft)]'>
        <p>
          © {currentYear} QA Squad, Inc. All rights reserved.{' '}
          <span className='text-[var(--qs-text-soft)]'>
            Built for quality and speed.
          </span>
        </p>
        <div className='flex gap-4'>
          <a href='/terms' className='hover:text-[var(--qs-text)]'>
            Terms of Service
          </a>
          <a href='/privacy' className='hover:text-[var(--qs-text)]'>
            Privacy Policy
          </a>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
