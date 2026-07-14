"use client";

import { m } from "framer-motion";
import { useState } from "react";

const faqs = [
  {
    question: "How do the specialized agents find opportunities?",
    answer:
      "Our AI CMO deploys specialized agents across Reddit, Twitter/X, Instagram, LinkedIn, and TikTok. These agents score conversations for buying intent, run SEO audits on your site, and identify keyword gaps automatically.",
  },
  {
    question: "Does the AI CMO auto-post on my behalf?",
    answer:
      "No. The agents generate drafts, SEO fixes, and code suggestions for you, but all final execution is manual. You review, approve, and post from your own accounts, ensuring everything remains authentic and compliant.",
  },
  {
    question: "Which platforms are supported?",
    answer:
      "We currently support Reddit, Twitter/X, Instagram, TikTok, and LinkedIn. Reddit is fully powered out of the box. Other platforms use RapidAPI-based scrapers — you just need a free RapidAPI key to enable them.",
  },
  {
    question: "Is my data secure?",
    answer:
      "Yes. All data is encrypted at rest and in transit. Your brand profiles, generated content, and analytics are scoped to your workspace and never shared. We use JWT authentication and workspace-level access controls.",
  },
  {
    question: "Can I cancel anytime?",
    answer:
      "Absolutely. There are no long-term contracts. You can downgrade to the free plan or cancel entirely from your billing settings at any time. Your data remains accessible for 30 days after cancellation.",
  },
  {
    question: "What AI models power the agents?",
    answer:
      "SignalFlow uses Gemini as the default AI engine for intent classification, keyword expansion, and draft generation. You can also switch your AI CMO to use OpenAI (GPT-4), Claude, or Perplexity.",
  },
];

function FaqItem({ question, answer }: { question: string; answer: string }) {
  const [open, setOpen] = useState(false);
  const answerId = `faq-answer-${question.replace(/\s+/g, "-").toLowerCase().slice(0, 40)}`;

  return (
    <div className="border-b border-border">
      <button
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        aria-controls={answerId}
        className="flex w-full items-center justify-between py-5 text-left"
      >
        <span className="text-base font-medium text-foreground">
          {question}
        </span>
        <m.svg
          animate={{ rotate: open ? 180 : 0 }}
          transition={{ duration: 0.2 }}
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="text-muted-foreground"
          style={{ flexShrink: 0 }}
        >
          <polyline points="6 9 12 15 18 9" />
        </m.svg>
      </button>
      <m.div
        id={answerId}
        animate={{ height: open ? "auto" : 0, opacity: open ? 1 : 0 }}
        initial={false}
        transition={{ duration: 0.3, ease: "easeInOut" }}
        style={{ overflow: "hidden" }}
      >
        <p className="pb-5 text-sm leading-relaxed text-muted-foreground">
          {answer}
        </p>
      </m.div>
    </div>
  );
}

export function Faq() {
  return (
    <section aria-labelledby="faq-heading" className="py-20 md:py-28">
      <div className="mx-auto max-w-3xl px-6">
        <m.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.5 }}
          className="text-center"
        >
          <span className="mb-4 inline-block text-xs font-semibold uppercase tracking-widest text-primary">
            FAQ
          </span>
          <h2 id="faq-heading" className="text-3xl font-bold tracking-tight text-foreground md:text-4xl">
            Frequently asked questions
          </h2>
        </m.div>

        <m.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="mt-12"
        >
          {faqs.map((faq) => (
            <FaqItem key={faq.question} question={faq.question} answer={faq.answer} />
          ))}
        </m.div>
      </div>
    </section>
  );
}
