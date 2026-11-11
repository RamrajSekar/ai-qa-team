import type { Metadata } from 'next';
import '@/components/marketing/marketing.css';
import Hero from '@/components/marketing/Hero';
import Workflow from '@/components/marketing/Workflow';
import Features from '@/components/marketing/Features';
import Roadmap from '@/components/marketing/Roadmap';
import Footer from '@/components/marketing/Footer';

export const metadata: Metadata = { title: 'AI QA Team | Your Existing Automation, Easier to Use', description: 'Explore the AI QA Team product vision: bug reproduction and strategic QA data built around automation you already own. Robot Framework first.' };

export default function MarketingPage() {
  return (
    <main className="public-landing">
      <Hero />
      <Features />
      <Workflow />
      <Roadmap />
      <Footer />
    </main>
  );
}
