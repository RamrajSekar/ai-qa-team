import type { Metadata } from 'next';
import '@/components/marketing/marketing.css';
import Hero from '@/components/marketing/Hero';
import Workflow from '@/components/marketing/Workflow';
import Footer from '@/components/marketing/Footer';

export const metadata: Metadata = {
  title: 'AI QA Team | Clearer Stories. Better Test Cases.',
  description: 'Teach product knowledge, find gaps in stories, and generate test cases for human review.'
};

export default function MarketingPage() {
  return (
    <main className="public-landing">
      <Hero />
      <Workflow />
      <Footer />
    </main>
  );
}
