import Hero from '@/components/marketing/Hero';
import Workflow from '@/components/marketing/Workflow';
import Features from '@/components/marketing/Features';
import Pricing from '@/components/marketing/Pricing';
import Roadmap from '@/components/marketing/Roadmap';
import Footer from '@/components/marketing/Footer';

export default function MarketingPage() {
  return (
    <main className="bg-[var(--qs-bg)] text-[var(--qs-text)]">
      <Hero />
      <Workflow />
      <Features />
      <Pricing />
      <Roadmap />
      <Footer />
    </main>
  );
}
