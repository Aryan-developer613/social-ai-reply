export type ReplyQualityLevel = "ready" | "review" | "risky";

export type ReplyQuality = {
  score: number;
  level: ReplyQualityLevel;
  label: string;
  warnings: string[];
  strengths: string[];
  characterLimit?: number;
};

const PLATFORM_LIMITS: Record<string, number> = {
  twitter: 280,
  x: 280,
  linkedin: 1250,
  instagram: 2200,
};

const SALESY_TERMS = [
  "buy now",
  "limited time",
  "sign up",
  "book a demo",
  "dm me",
  "contact us",
  "check out our",
  "our product",
  "our platform",
  "we offer",
  "we provide",
];

const HELPFUL_TERMS = [
  "try",
  "consider",
  "because",
  "for example",
  "one option",
  "tradeoff",
  "depends",
  "if",
];

export function assessReplyQuality(content: string, platform?: string | null): ReplyQuality {
  const text = content.trim();
  const normalized = text.toLowerCase();
  const platformKey = (platform || "").toLowerCase();
  const characterLimit = PLATFORM_LIMITS[platformKey];
  const warnings: string[] = [];
  const strengths: string[] = [];
  let score = 72;

  if (text.length < 80) {
    warnings.push("May be too short to be useful.");
    score -= 10;
  } else {
    strengths.push("Has enough context to be useful.");
    score += 5;
  }

  if (characterLimit && text.length > characterLimit) {
    warnings.push(`Over ${platformKey === "x" ? "X" : platformKey} character limit.`);
    score -= 20;
  }

  const salesyHits = SALESY_TERMS.filter((term) => normalized.includes(term));
  if (salesyHits.length > 0) {
    warnings.push("May sound promotional.");
    score -= Math.min(28, salesyHits.length * 9);
  } else {
    strengths.push("Low promotional risk.");
    score += 8;
  }

  if (HELPFUL_TERMS.some((term) => normalized.includes(term))) {
    strengths.push("Gives practical guidance.");
    score += 8;
  } else {
    warnings.push("Could use a more concrete next step.");
    score -= 6;
  }

  if (/https?:\/\//i.test(text)) {
    warnings.push("Contains a link. Use only when the conversation clearly needs it.");
    score -= 8;
  }

  if (/[!?]{2,}/.test(text)) {
    warnings.push("Punctuation may feel too intense.");
    score -= 4;
  }

  score = Math.max(0, Math.min(100, Math.round(score)));
  const level: ReplyQualityLevel = score >= 78 && warnings.length <= 1 ? "ready" : score >= 55 ? "review" : "risky";
  const label = level === "ready" ? "Ready" : level === "review" ? "Needs review" : "High risk";

  return { score, level, label, warnings, strengths, characterLimit };
}

export function qualityBadgeClass(level: ReplyQualityLevel): string {
  if (level === "ready") {
    return "border-emerald-500/30 bg-emerald-500/10 text-emerald-300";
  }
  if (level === "review") {
    return "border-amber-500/30 bg-amber-500/10 text-amber-300";
  }
  return "border-destructive/30 bg-destructive/10 text-destructive";
}
