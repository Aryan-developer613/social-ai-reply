import type { Opportunity } from "@/lib/api";
import { sourceLabel } from "@/lib/opportunity";

const HIGH_INTENT_STAGES = new Set(["solution_seeking", "comparing", "evaluating", "problem_aware"]);
const HIGH_INTENT_TERMS = ["alternative", "recommendation", "complain", "help", "buyer", "comparison", "looking"];

export function opportunityDedupKey(opportunity: Opportunity): string {
  const permalink = (opportunity.permalink || "").trim().toLowerCase();
  if (permalink) {
    return permalink.replace(/[?#].*$/, "");
  }
  return `${sourceLabel(opportunity)}:${opportunity.title}`.toLowerCase().replace(/\s+/g, " ").trim();
}

export function isHighIntentOpportunity(opportunity: Opportunity): boolean {
  if ((opportunity.score || 0) >= 55) {
    return true;
  }
  if (opportunity.buying_stage && HIGH_INTENT_STAGES.has(opportunity.buying_stage)) {
    return true;
  }
  const intent = (opportunity.intent || "").toLowerCase();
  return HIGH_INTENT_TERMS.some((term) => intent.includes(term));
}

export function opportunityGuide(opportunity: Opportunity): {
  why: string;
  whatToSay: string;
  risk: string;
} {
  const platform = ((opportunity as Record<string, unknown>).platform as string | undefined || "reddit").toLowerCase();
  const stage = opportunity.buying_stage || "conversation";
  const reasons = opportunity.score_reasons?.filter(Boolean) ?? [];
  const keywords = opportunity.keyword_hits?.filter(Boolean) ?? [];
  const risks = opportunity.rule_risk?.filter(Boolean) ?? [];

  const why =
    reasons[0] ||
    (keywords.length > 0
      ? `Matches ${keywords.slice(0, 3).join(", ")}.`
      : `Score ${opportunity.score || 0} suggests this is worth reviewing.`);

  let whatToSay = "Acknowledge the point, add one useful detail, and keep the reply conversational.";
  if (stage.includes("solution") || stage.includes("evaluating") || stage.includes("comparing")) {
    whatToSay = "Answer directly, mention a practical tradeoff, and offer one clear next step.";
  } else if (stage.includes("problem")) {
    whatToSay = "Start with empathy, validate the problem, then suggest a low-pressure way to think about it.";
  }
  if (platform === "github") {
    whatToSay = "Be implementation-focused. Mention a concrete fix, workaround, or reference.";
  } else if (platform === "hackernews") {
    whatToSay = "Be precise and low-hype. Lead with evidence, constraints, or a useful tradeoff.";
  } else if (platform === "linkedin") {
    whatToSay = "Keep it professional and insight-led. Add credibility without turning it into a pitch.";
  }

  const risk = risks[0] || "Avoid hard selling. Only mention the brand if it clearly helps the person.";

  return { why, whatToSay, risk };
}
