import type { Metadata } from 'next';
import '@/components/marketing/marketing.css';
import Hero from '@/components/marketing/Hero';
import Workflow from '@/components/marketing/Workflow';
import Features from '@/components/marketing/Features';
import Roadmap from '@/components/marketing/Roadmap';
import Footer from '@/components/marketing/Footer';

export const metadata: Metadata = {
  title: 'AI QA Team | Human-Supervised Visual QA',
  description: 'Explore our product direction: learn product knowledge from narrated recordings, generate tests from stories and acceptance criteria, and review approved visual execution with evidence.',
};

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
