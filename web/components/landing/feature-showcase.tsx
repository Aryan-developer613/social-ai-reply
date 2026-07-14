"use client";

import { m } from "framer-motion";

const features = [
  {
    title: "The SEO Agent",
    description:
      "Scans your site, finds keyword gaps, and suggests technical fixes. Automatically crawls your sitemap and content to ensure you rank for what matters most.",
    mockup: (
      <div className="grid gap-3">
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-lg bg-muted p-4">
            <div className="text-xs font-medium text-muted-foreground">Overall Visibility</div>
            <div className="mt-1 text-4xl font-bold text-primary">87<span className="text-lg">/100</span></div>
            <div className="mt-2 text-xs font-medium text-muted-foreground">+12pts this month</div>
          </div>
          <div className="grid gap-2">
            {[
              { name: "ChatGPT", pct: 92 },
              { name: "Perplexity", pct: 78 },
              { name: "Gemini", pct: 65 },
              { name: "Claude", pct: 71 },
            ].map((m) => (
              <div key={m.name} className="flex items-center gap-2 rounded-lg bg-muted p-2">
                <span className="w-16 text-xs font-medium text-muted-foreground">{m.name}</span>
                <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-border">
                  <div className="h-full rounded-full bg-primary" style={{ width: `${m.pct}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>
        <div className="rounded-lg bg-muted p-4">
          <div className="mb-2 text-xs font-semibold text-foreground">Recent Citations</div>
          {["Mentioned in top 3 for 'best CRM software'", "Cited as alternative to HubSpot in ChatGPT", "New source gap detected on Perplexity"].map((c, i) => (
            <div key={i} className="flex items-start gap-2 py-1.5">
              <div className={`mt-1 h-1.5 w-1.5 shrink-0 rounded-full ${i < 2 ? "bg-primary" : "bg-muted-foreground"}`} />
              <span className="text-xs text-muted-foreground">{c}</span>
            </div>
          ))}
        </div>
      </div>
    ),
    reverse: false,
  },
  {
    title: "The Social & Community Agent",
    description:
      "Discovers high-intent conversations on Reddit and LinkedIn where your expertise matters most, drafting authentic, non-spammy replies for you to approve.",
    mockup: (
      <div className="grid gap-3">
        {[
          { subreddit: "r/SaaS", title: "Best CRM for early-stage startups?", score: 94, intent: "Recommendation", comments: "3" },
          { subreddit: "r/Marketing", title: "Switching from HubSpot — what's better?", score: 89, intent: "Comparison", comments: "7" },
          { subreddit: "r/Entrepreneur", title: "Tools that actually save time for small teams", score: 82, intent: "Discussion", comments: "12" },
        ].map((opp) => (
          <div key={opp.title} className="flex items-start gap-3 rounded-lg border border-border bg-muted p-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-coral-glow text-sm font-bold text-primary">
              {opp.score}
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-xs font-medium text-muted-foreground">{opp.subreddit}</div>
              <div className="text-sm font-semibold text-foreground">{opp.title}</div>
              <div className="mt-1 flex gap-2">
                <span className="rounded-full bg-coral-glow px-2 py-0.5 text-xs font-medium text-primary">{opp.intent}</span>
                <span className="text-xs text-muted-foreground">{opp.comments} comments</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    ),
    reverse: true,
  },
  {
    title: "The Content & UGC Agent",
    description:
      "Brainstorms user-generated content ideas and drafts blog posts in your exact brand voice. Never sound robotic — every draft is helpful, relevant, and human.",
    mockup: (
      <div className="grid gap-3">
        <div className="rounded-lg bg-muted p-4">
          <div className="mb-2 text-xs font-semibold text-foreground">Generated Reply</div>
          <div className="space-y-2 text-sm leading-relaxed text-muted-foreground">
            <p>Great question! I switched to a CRM built specifically for early-stage startups and it made a huge difference. The key things I looked for were...</p>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-2">
          <div className="rounded-lg bg-muted p-3 text-center">
            <div className="text-xs font-medium text-muted-foreground">Brand Voice</div>
            <div className="mt-1 text-sm font-bold text-primary">98% Match</div>
          </div>
          <div className="rounded-lg bg-muted p-3 text-center">
            <div className="text-xs font-medium text-muted-foreground">Rule Check</div>
            <div className="mt-1 text-sm font-bold text-primary">Compliant</div>
          </div>
          <div className="rounded-lg bg-muted p-3 text-center">
            <div className="text-xs font-medium text-muted-foreground">Spam Score</div>
            <div className="mt-1 text-sm font-bold text-primary">0%</div>
          </div>
        </div>
      </div>
    ),
    reverse: false,
  },
];

export function FeatureShowcase() {
  return (
    <section id="features" className="py-20 md:py-28">
      <div className="mx-auto max-w-7xl px-6">
        <m.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.5 }}
          className="text-center"
        >
          <span
            className="mb-4 inline-block text-xs font-semibold uppercase tracking-widest text-primary"
          >
            Features
          </span>
          <h2
            className="text-3xl font-bold tracking-tight text-foreground md:text-4xl"
          >
            Everything you need to own your narrative
          </h2>
        </m.div>

        <div className="mt-16 space-y-24">
          {features.map((feature) => (
            <m.div
              key={feature.title}
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{ duration: 0.6 }}
              className="grid items-center gap-12 md:grid-cols-2"
            >
              <div className={feature.reverse ? "md:order-2" : undefined}>
                <h3
                  className="mb-4 text-2xl font-bold tracking-tight text-foreground md:text-3xl"
                >
                  {feature.title}
                </h3>
                <p
                  className="text-base leading-relaxed text-muted-foreground"
                >
                  {feature.description}
                </p>
              </div>

              <div
                className={`relative overflow-hidden rounded-2xl border border-border bg-background p-6 shadow-xl shadow-primary/5 dark:shadow-primary/10 transition-all duration-500 hover:shadow-2xl hover:shadow-primary/10 dark:hover:shadow-primary/15 ${feature.reverse ? " md:order-1" : ""}`}
              >
                {feature.mockup}
              </div>
            </m.div>
          ))}
        </div>
      </div>
    </section>
  );
}
