import type { CompanyProfile, Opportunity } from "@/lib/api";

type CompetitorSource = Pick<CompanyProfile, "competitors" | "extracted_competitors"> | null | undefined;
type CompetitorSuggestionSource = Pick<
  CompanyProfile,
  "name" | "category" | "description" | "target_audience" | "competitors" | "extracted_competitors"
> | null | undefined;

function normalizeName(name: string): string {
  return name.replace(/\s+/g, " ").trim();
}

export function parseCompetitorNames(value: string | null | undefined): string[] {
  if (!value) {
    return [];
  }
  const trimmed = value.trim();
  if (trimmed.startsWith("[")) {
    try {
      const parsed = JSON.parse(trimmed);
      if (Array.isArray(parsed)) {
        return parsed.map((item) => normalizeName(String(item))).filter((item) => item.length > 1);
      }
    } catch {
      // Fall through to delimiter parsing.
    }
  }
  return trimmed
    .split(/[,;\n]+/)
    .map((item) => normalizeName(item.replace(/^[-*]\s*/, "")))
    .filter((item) => item.length > 1);
}

export function competitorNamesFromCompany(company: CompetitorSource): string[] {
  const seen = new Set<string>();
  const names: string[] = [];
  for (const name of [
    ...parseCompetitorNames(company?.competitors),
    ...parseCompetitorNames(company?.extracted_competitors),
  ]) {
    const key = name.toLowerCase();
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    names.push(name);
  }
  return names;
}

export function matchedCompetitorsForOpportunity(
  opportunity: Opportunity,
  competitors: readonly string[],
): string[] {
  if (competitors.length === 0) {
    return [];
  }
  const text = [
    opportunity.title,
    opportunity.body_excerpt,
    opportunity.intent,
    opportunity.score_reasons?.join(" "),
    opportunity.keyword_hits?.join(" "),
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();

  return competitors.filter((competitor) => {
    const normalized = normalizeName(competitor).toLowerCase();
    if (normalized.length < 2) {
      return false;
    }
    const escaped = normalized.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    return new RegExp(`(^|[^a-z0-9])${escaped}([^a-z0-9]|$)`, "i").test(text);
  });
}

export function hasCompetitorMention(opportunity: Opportunity, competitors: readonly string[]): boolean {
  return matchedCompetitorsForOpportunity(opportunity, competitors).length > 0;
}

const COMPETITOR_SUGGESTION_SETS: Array<{ terms: string[]; names: string[] }> = [
  {
    terms: ["ecommerce", "e-commerce", "shopping", "retail", "marketplace", "grocery", "electronics"],
    names: ["Amazon", "Myntra", "Meesho", "Ajio", "Tata Neu", "Snapdeal"],
  },
  {
    terms: ["real estate", "property", "housing", "rental", "broker", "apartment"],
    names: ["Magicbricks", "99acres", "Housing.com", "NoBroker", "Square Yards"],
  },
  {
    terms: ["social", "marketing", "scheduler", "content", "creator", "agency"],
    names: ["Buffer", "Hootsuite", "Sprout Social", "Postiz", "Later"],
  },
  {
    terms: ["crm", "sales", "lead", "pipeline"],
    names: ["HubSpot", "Salesforce", "Zoho CRM", "Pipedrive"],
  },
  {
    terms: ["ai", "automation", "assistant", "workflow"],
    names: ["Zapier", "Make", "Notion AI", "ChatGPT", "Claude"],
  },
];

export function suggestCompetitorsForCompany(
  company: CompetitorSuggestionSource,
  existing: readonly string[],
  limit = 8,
): string[] {
  const current = new Set(existing.map((name) => normalizeName(name).toLowerCase()));
  const companyName = normalizeName(company?.name || "").toLowerCase();
  const context = [
    company?.name,
    company?.category,
    company?.description,
    company?.target_audience,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  const suggestions: string[] = [];

  for (const set of COMPETITOR_SUGGESTION_SETS) {
    if (!set.terms.some((term) => context.includes(term))) {
      continue;
    }
    for (const name of set.names) {
      const key = name.toLowerCase();
      if (key !== companyName && !current.has(key) && !suggestions.some((item) => item.toLowerCase() === key)) {
        suggestions.push(name);
      }
    }
  }

  for (const name of parseCompetitorNames(company?.extracted_competitors)) {
    const key = name.toLowerCase();
    if (key !== companyName && !current.has(key) && !suggestions.some((item) => item.toLowerCase() === key)) {
      suggestions.push(name);
    }
  }

  return suggestions.slice(0, limit);
}
