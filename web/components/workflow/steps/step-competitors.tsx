"use client";

import { useEffect, useState } from "react";
import { Loader2, TrendingDown, TrendingUp, Minus, ArrowRight, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  fetchCompetitorStats,
  fetchCompetitorList,
  type CompetitorStats,
} from "@/lib/api/competitors";
import { getCompanies } from "@/lib/api/company";
import { useToast } from "@/stores/toast";
import type { StepStatus } from "@/stores/workflow-store";

interface Props {
  token: string;
  projectId: number | null;
  onStatusChange: (status: StepStatus) => void;
  onContinue: () => void;
}

const SENTIMENT_ICON: Record<string, React.ElementType> = {
  negative: TrendingDown,
  neutral: Minus,
  positive: TrendingUp,
};

const SENTIMENT_COLOR: Record<string, string> = {
  negative: "text-red-500",
  neutral: "text-yellow-500",
  positive: "text-green-500",
};

function dominantSentiment(stat: CompetitorStats): string {
  const { negative_count, neutral_count, positive_count } = stat;
  if (negative_count >= neutral_count && negative_count >= positive_count) return "negative";
  if (positive_count >= neutral_count) return "positive";
  return "neutral";
}

export function StepCompetitors({ token, projectId, onStatusChange, onContinue }: Props) {
  const { error } = useToast();
  const [stats, setStats] = useState<CompetitorStats[]>([]);
  const [competitors, setCompetitors] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (projectId) void load();
  }, [projectId, token]);

  async function load() {
    setLoading(true);
    try {
      const [statData, listData] = await Promise.allSettled([
        fetchCompetitorStats(token, projectId!),
        fetchCompetitorList(token, projectId!),
      ]);
      const resolvedStats = statData.status === "fulfilled" ? statData.value : [];
      const resolvedList = listData.status === "fulfilled" ? listData.value : [];
      setStats(resolvedStats);
      setCompetitors(resolvedList);

      // Also check company profile for competitor names
      if (resolvedList.length === 0) {
        try {
          const companies = await getCompanies(token);
          const active = companies.find((c) => c.is_active) ?? companies[0];
          const fromCompany = active?.competitors?.split(",").map((s) => s.trim()).filter(Boolean) ?? [];
          if (fromCompany.length > 0) setCompetitors(fromCompany);
        } catch { /* ignore */ }
      }

      onStatusChange(resolvedStats.length > 0 || resolvedList.length > 0 ? "done" : "partial");
    } catch {
      onStatusChange("partial");
    }
    setLoading(false);
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 py-4 text-muted-foreground text-sm">
        <Loader2 className="h-4 w-4 animate-spin" /> Loading competitor data…
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Tracked competitors from company profile */}
      {competitors.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Tracked from company profile</p>
          <div className="flex flex-wrap gap-2">
            {competitors.map((c) => (
              <span
                key={c}
                className="text-xs bg-muted border border-border rounded-full px-3 py-1 font-medium"
              >
                {c}
              </span>
            ))}
          </div>
          <p className="text-xs text-muted-foreground">
            Edit competitors in Company Setup → Competitors field, then re-run scans to populate mention data.
          </p>
        </div>
      )}

      {/* Mention stats */}
      {stats.length > 0 ? (
        <div className="space-y-2">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Mention stats from scans</p>
          {stats.map((stat) => {
            const sentiment = dominantSentiment(stat);
            const Icon = SENTIMENT_ICON[sentiment];
            return (
              <div
                key={stat.competitor_name}
                className="rounded-lg border bg-card p-3 flex items-start justify-between gap-3"
              >
                <div className="min-w-0 space-y-1">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-semibold truncate">{stat.competitor_name}</p>
                    <Icon className={cn("h-3.5 w-3.5 shrink-0", SENTIMENT_COLOR[sentiment])} />
                  </div>
                  {stat.top_complaints.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {stat.top_complaints.slice(0, 3).map((c, i) => (
                        <span key={i} className="text-[10px] bg-red-500/10 text-red-400 border border-red-500/20 rounded-full px-2 py-0.5">
                          {c}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <div className="text-right shrink-0 space-y-0.5">
                  <p className="text-sm font-semibold">{stat.total_mentions}</p>
                  <p className="text-[10px] text-muted-foreground">mentions</p>
                  <div className="flex gap-1 text-[10px]">
                    <span className="text-red-400">{stat.negative_count}−</span>
                    <span className="text-green-400">{stat.positive_count}+</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="rounded-lg border border-dashed p-5 text-sm text-muted-foreground text-center space-y-1">
          <p>No competitor mentions yet.</p>
          <p className="text-xs">Run a scan after configuring communities — the pipeline will automatically detect competitor discussions.</p>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center justify-between pt-2">
        <a
          href="/app/competitors"
          className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1 transition-colors"
        >
          Full competitor view
          <ExternalLink className="h-3 w-3" />
        </a>
        <Button onClick={onContinue}>
          Continue to Launch
          <ArrowRight className="h-3.5 w-3.5 ml-1" />
        </Button>
      </div>
    </div>
  );
}
