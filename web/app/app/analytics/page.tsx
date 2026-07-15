"use client";
import { useEffect, useState } from "react";
import { Copy } from "lucide-react";
import { useAuth } from "@/components/auth/auth-provider";
import { useToast } from "@/stores/toast";
import { apiRequest } from "@/lib/api";
import {
  getRoiRollup,
  getTrackedLinks,
  shortLinkUrl,
  type RoiRollupRow,
  type TrackedLink,
} from "@/lib/api/links";
import { copyText } from "@/lib/reddit";
import { useSelectedProjectId } from "@/hooks/use-selected-project";
import { withProjectId } from "@/lib/project";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { PageHeader } from "@/components/shared/page-header";
import { KPIGrid, type KPICardProps } from "@/components/shared/kpi-card";
import { EmptyState } from "@/components/shared/empty-state";

interface AnalyticsOverview {
  visibility_score: number;
  total_opportunities: number;
  total_drafts: number;
  total_published: number;
}

interface TrendData {
  date: string | null;
  visibility_score: number;
}

interface EngagementData {
  by_status: Record<string, number>;
  total_scans: number;
}

interface KeywordData {
  keyword: string;
  priority_score: number;
}

interface SubredditData {
  name: string;
  fit_score: number;
}

interface ActivityEvent {
  id: number;
  action: string;
  entity_type: string | null;
  metadata: Record<string, unknown>;
  created_at: string | null;
}

function toTitleCase(value: string) {
  return value.replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatActivityLabel(event: ActivityEvent) {
  const metadataTitle = typeof event.metadata?.title === "string" ? event.metadata.title : null;
  if (metadataTitle) {
    return metadataTitle;
  }

  const action = toTitleCase(event.action.replace(/[._]/g, " "));
  const entityType = event.entity_type ? toTitleCase(event.entity_type.replace(/_/g, " ")) : "";
  return entityType ? `${action} · ${entityType}` : action;
}

export default function AnalyticsPage() {
  const { token } = useAuth();
  const { success, error } = useToast();
  const selectedProjectId = useSelectedProjectId();
  const [loading, setLoading] = useState(true);
  const [dateRange, setDateRange] = useState<"7d" | "30d" | "90d" | "all">("30d");
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [trendData, setTrendData] = useState<TrendData[]>([]);
  const [engagementData, setEngagementData] = useState<EngagementData | null>(null);
  const [keywords, setKeywords] = useState<KeywordData[]>([]);
  const [subreddits, setSubreddits] = useState<SubredditData[]>([]);
  const [activity, setActivity] = useState<ActivityEvent[]>([]);
  const [trackedLinks, setTrackedLinks] = useState<TrackedLink[]>([]);
  const [roiRows, setRoiRows] = useState<RoiRollupRow[]>([]);

  useEffect(() => {
    if (!token) return;
    loadData();
  }, [token, selectedProjectId, dateRange]);

  async function loadData() {
    setLoading(true);
    try {
      const days = dateRange === "7d" ? 7 : dateRange === "30d" ? 30 : dateRange === "90d" ? 90 : 365;

      let overviewRes: AnalyticsOverview | null = null;
      let trendDataRes: TrendData[] = [];
      let funnelRes: EngagementData | null = null;
      let keywordsRes: KeywordData[] = [];
      let subredditsRes: SubredditData[] = [];
      let activityRes: ActivityEvent[] = [];

      try {
        const res = await apiRequest<AnalyticsOverview>(
          withProjectId(`/v1/analytics/overview?days=${days}`, selectedProjectId),
          {},
          token
        );
        overviewRes = res;
      } catch (err: unknown) {
        console.warn("Failed to load overview:", err);
        error("Failed to load overview data");
      }

      try {
        const res = await apiRequest<{ items: TrendData[] }>(
          withProjectId(`/v1/analytics/visibility-trend?days=${days}`, selectedProjectId),
          {},
          token
        );
        trendDataRes = res.items || [];
      } catch (err: unknown) {
        console.warn("Failed to load trend data:", err);
        error("Failed to load trend data");
      }

      try {
        const res = await apiRequest<EngagementData>(
          withProjectId(`/v1/analytics/engagement`, selectedProjectId),
          {},
          token
        );
        funnelRes = res;
      } catch (err: unknown) {
        console.warn("Failed to load engagement:", err);
        error("Failed to load engagement data");
      }

      try {
        const res = await apiRequest<{ items: KeywordData[] }>(
          withProjectId(`/v1/analytics/keywords`, selectedProjectId),
          {},
          token
        );
        keywordsRes = res.items || [];
      } catch (err: unknown) {
        console.warn("Failed to load keywords:", err);
        error("Failed to load keyword data");
      }

      try {
        const res = await apiRequest<{ items: SubredditData[] }>(
          withProjectId(`/v1/analytics/subreddits`, selectedProjectId),
          {},
          token
        );
        subredditsRes = res.items || [];
      } catch (err: unknown) {
        console.warn("Failed to load subreddits:", err);
        error("Failed to load subreddit data");
      }

      try {
        const res = await apiRequest<{ items: ActivityEvent[] }>(
          withProjectId(`/v1/activity`, selectedProjectId),
          {},
          token
        );
        activityRes = res.items || [];
      } catch (err: unknown) {
        console.warn("Failed to load activity:", err);
        error("Failed to load activity data");
      }

      // Reply ROI (tracked links + rollups). Loaded best-effort: the section
      // simply shows its empty state when these endpoints fail.
      let trackedLinksRes: TrackedLink[] = [];
      let roiRowsRes: RoiRollupRow[] = [];
      if (token) {
        try {
          trackedLinksRes = await getTrackedLinks(token, selectedProjectId);
        } catch (err: unknown) {
          console.warn("Failed to load tracked links:", err);
        }
        try {
          const res = await getRoiRollup(token, selectedProjectId);
          roiRowsRes = res.rows || [];
        } catch (err: unknown) {
          console.warn("Failed to load ROI rollup:", err);
        }
      }

      setOverview(overviewRes);
      setTrackedLinks(trackedLinksRes);
      setRoiRows(roiRowsRes);
      setTrendData(trendDataRes);
      setEngagementData(funnelRes);
      setKeywords(keywordsRes);
      setSubreddits(subredditsRes);
      setActivity(activityRes);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="flex flex-col gap-8">
        <PageHeader title="Analytics" description="Track visibility trends, engagement funnel, and performance metrics." />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {[1, 2, 3, 4].map(i => (
            <Card key={i} className="p-5">
              <Skeleton className="h-8 w-3/5 mb-2" />
              <Skeleton className="h-3 w-full" />
            </Card>
          ))}
        </div>
      </div>
    );
  }

  const firstTrendPoint = trendData[0]?.visibility_score ?? overview?.visibility_score ?? 0;
  const lastTrendPoint = trendData[trendData.length - 1]?.visibility_score ?? overview?.visibility_score ?? 0;
  const visibilityTrend = Math.round((lastTrendPoint - firstTrendPoint) * 10) / 10;

  // Max values for bar heights — use reduce to avoid stack overflow on large arrays
  const trendScores = trendData.map(d => d.visibility_score);
  const maxTrendScore = trendScores.length ? trendScores.reduce((a, b) => Math.max(a, b), -Infinity) : 100;
  const keywordScores = keywords.map(k => k.priority_score);
  const maxKeywords = keywordScores.length ? keywordScores.reduce((a, b) => Math.max(a, b), -Infinity) : 1;
  const subredditScores = subreddits.map(s => s.fit_score);
  const maxSubreddits = subredditScores.length ? subredditScores.reduce((a, b) => Math.max(a, b), -Infinity) : 100;

  // Funnel calculations
  const byStatus = engagementData?.by_status || {};
  const funnelOpp = Object.values(byStatus).reduce((total, count) => total + count, 0);
  const funnelSaved = byStatus.saved || 0;
  const funnelDraft = byStatus.drafting || 0;
  const funnelPost = byStatus.posted || 0;
  const conv1 = funnelOpp > 0 ? Math.round((funnelSaved / funnelOpp) * 100) : 0;
  const conv2 = funnelSaved > 0 ? Math.round((funnelDraft / funnelSaved) * 100) : 0;
  const conv3 = funnelDraft > 0 ? Math.round((funnelPost / funnelDraft) * 100) : 0;

  // KPI cards
  const kpiCards: KPICardProps[] = [
    {
      label: "Visibility Score",
      value: `${overview?.visibility_score || 0}%`,
      trend: visibilityTrend !== 0
        ? { value: Math.abs(visibilityTrend), direction: visibilityTrend >= 0 ? "up" : "down" }
        : undefined,
    },
    { label: "Opportunities Found", value: overview?.total_opportunities || 0 },
    { label: "Drafts Created", value: overview?.total_drafts || 0 },
    { label: "Posts Published", value: overview?.total_published || 0 },
  ];

  // Reply ROI rollups
  const subredditClicks = roiRows.filter((row) => row.group_by === "subreddit");
  const stageClicks = roiRows.filter((row) => row.group_by === "buying_stage");
  const maxRollupClicks = roiRows.reduce((max, row) => Math.max(max, row.clicks), 1);
  const totalLinkClicks = trackedLinks.reduce((sum, link) => sum + link.click_count, 0);

  async function copyShortUrl(link: TrackedLink) {
    try {
      await copyText(shortLinkUrl(link));
      success("Short URL copied");
    } catch {
      error("Failed to copy", "Clipboard access was denied.");
    }
  }

  // SVG chart data (last 30 points)
  const chartData = trendData.slice(-30);
  const chartHeight = 200;
  const chartPadding = { top: 10, right: 10, bottom: 30, left: 40 };
  const plotWidth = 100 - chartPadding.left - chartPadding.right;
  const plotHeight = chartHeight - chartPadding.top - chartPadding.bottom;
  const barWidth = chartData.length > 1 ? plotWidth / chartData.length : plotWidth;
  const barGap = barWidth * 0.2;
  const barActualWidth = barWidth - barGap;

  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        title="Analytics"
        description="Track visibility trends, engagement funnel, and performance metrics."
        actions={
          <select
            value={dateRange}
            onChange={e => setDateRange(e.target.value as "7d" | "30d" | "90d" | "all")}
            className="rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground"
          >
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
            <option value="90d">Last 90 days</option>
            <option value="all">All time</option>
          </select>
        }
      />

      {/* KPI Row */}
      <KPIGrid cards={kpiCards} columns={4} className="grid-cols-1 sm:grid-cols-2 lg:grid-cols-4" />

      {/* Section 1: Visibility Trend Chart (SVG) */}
      <Card className="p-5">
        <h3 className="text-sm font-semibold mb-4">Visibility Score Trend</h3>
        {chartData.length === 0 ? (
          <EmptyState
            title="No trend data available yet"
            description="Run visibility checks to start building your trend chart."
          />
        ) : (
          <svg
            viewBox={`0 0 100 ${chartHeight}`}
            preserveAspectRatio="xMinYMin meet"
            className="w-full"
            style={{ height: chartHeight }}
            role="img"
            aria-label="Visibility score trend chart"
          >
            {/* Y-axis labels - computed dynamically from maxTrendScore */}
            {(() => {
              const max = maxTrendScore || 100;
              const step = max >= 100 ? 25 : max >= 50 ? 10 : max >= 20 ? 5 : 1;
              const ticks: number[] = [];
              for (let v = 0; v <= max; v += step) {
                ticks.push(v);
              }
              if (ticks[ticks.length - 1] !== max) {
                ticks.push(max);
              }
              return ticks.map(val => {
                const y = chartPadding.top + plotHeight - (val / max) * plotHeight;
                return (
                  <g key={val}>
                    <text
                      x={chartPadding.left - 4}
                      y={y + 3}
                      textAnchor="end"
                      className="fill-muted-foreground"
                      style={{ fontSize: "2.5px" }}
                    >
                      {Math.round(val)}
                    </text>
                    <line
                      x1={chartPadding.left}
                      y1={y}
                      x2={100 - chartPadding.right}
                      y2={y}
                      stroke="var(--color-border)"
                      strokeWidth="0.15"
                      strokeDasharray="1,1"
                    />
                  </g>
                );
              });
            })()}

            {/* Bars */}
            {chartData.map((d, i) => {
              const x = chartPadding.left + i * barWidth + barGap / 2;
              const barHeight = maxTrendScore > 0 ? (d.visibility_score / maxTrendScore) * plotHeight : 0;
              const y = chartPadding.top + plotHeight - barHeight;
              return (
                <rect
                  key={i}
                  x={x}
                  y={y}
                  width={Math.max(barActualWidth, 0.5)}
                  height={barHeight}
                  fill="var(--color-primary)"
                  rx="0.4"
                  opacity={0.85}
                >
                  <title>{`${d.date || "Unknown date"}: ${d.visibility_score}`}</title>
                </rect>
              );
            })}

            {/* Baseline */}
            <line
              x1={chartPadding.left}
              y1={chartPadding.top + plotHeight}
              x2={100 - chartPadding.right}
              y2={chartPadding.top + plotHeight}
              stroke="var(--color-border)"
              strokeWidth="0.3"
            />
          </svg>
        )}
      </Card>

      {/* Section 2: Engagement Funnel */}
      <Card className="p-5">
        <h3 className="text-sm font-semibold mb-4">Engagement Funnel</h3>
        <p className="text-xs text-muted-foreground mb-4">
          Based on opportunity status counts and {engagementData?.total_scans || 0} total scans.
        </p>
        <div className="space-y-4">
          {[
            { label: "Opportunities", value: funnelOpp, width: 100 },
            { label: "Saved", value: funnelSaved, width: (funnelSaved / funnelOpp) * 100 || 0, conv: conv1 },
            { label: "Drafted", value: funnelDraft, width: (funnelDraft / funnelOpp) * 100 || 0, conv: conv2 },
            { label: "Published", value: funnelPost, width: (funnelPost / funnelOpp) * 100 || 0, conv: conv3 },
          ].map((stage, i) => (
            <div key={i}>
              <div className="flex justify-between mb-1.5">
                <span className="text-sm font-semibold">{stage.label}</span>
                <div className="flex gap-2 text-xs">
                  <span><strong>{stage.value}</strong></span>
                  {stage.conv !== undefined && <span className="text-muted-foreground">{stage.conv}% conversion</span>}
                </div>
              </div>
              <div className="w-full h-8 bg-muted rounded-md overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-primary to-indigo-500 flex items-center justify-center text-white text-xs font-semibold transition-[width] duration-300"
                  style={{ width: `${Math.min(stage.width, 100)}%` }}
                >
                  {Math.round(stage.width)}%
                </div>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Section 2.5: Reply ROI */}
      <Card className="p-5">
        <h3 className="text-sm font-semibold mb-1">Reply ROI</h3>
        <p className="text-xs text-muted-foreground mb-4">
          Tracked short links attached to your replies — {trackedLinks.length} link{trackedLinks.length === 1 ? "" : "s"},{" "}
          {totalLinkClicks} click{totalLinkClicks === 1 ? "" : "s"} total.
        </p>
        {trackedLinks.length === 0 ? (
          <EmptyState
            title="No tracked links yet"
            description="Create a tracked link from a reply draft in Content Studio to start attributing clicks back to replies."
          />
        ) : (
          <div className="space-y-6">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Code</TableHead>
                  <TableHead>Destination</TableHead>
                  <TableHead className="text-right">Clicks</TableHead>
                  <TableHead className="w-[1%]" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {trackedLinks.map((link) => (
                  <TableRow key={link.id}>
                    <TableCell className="font-mono text-xs">{link.code}</TableCell>
                    <TableCell className="max-w-[320px] truncate text-xs text-muted-foreground">
                      {link.destination_url}
                    </TableCell>
                    <TableCell className="text-right text-sm font-semibold tabular-nums">
                      {link.click_count}
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="xs"
                        onClick={() => void copyShortUrl(link)}
                        aria-label={`Copy short URL for ${link.code}`}
                      >
                        <Copy className="h-3.5 w-3.5" /> Copy short URL
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <div>
                <h4 className="mb-3 text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                  Clicks per subreddit
                </h4>
                {subredditClicks.length === 0 ? (
                  <p className="text-xs text-muted-foreground">No subreddit attribution yet.</p>
                ) : (
                  <div className="space-y-2">
                    {subredditClicks.map((row) => (
                      <div key={`sr-${row.key}`} className="flex items-center gap-3 text-sm">
                        <span className="w-32 truncate shrink-0">r/{row.key}</span>
                        <div className="flex-1 h-5 bg-muted rounded overflow-hidden">
                          <div
                            className="h-full bg-primary"
                            style={{ width: `${(row.clicks / maxRollupClicks) * 100}%` }}
                          />
                        </div>
                        <span className="w-10 text-right text-xs font-semibold tabular-nums">{row.clicks}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <div>
                <h4 className="mb-3 text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                  Clicks per buying stage
                </h4>
                {stageClicks.length === 0 ? (
                  <p className="text-xs text-muted-foreground">No buying-stage attribution yet.</p>
                ) : (
                  <div className="space-y-2">
                    {stageClicks.map((row) => (
                      <div key={`stage-${row.key}`} className="flex items-center gap-3 text-sm">
                        <span className="w-32 truncate shrink-0 capitalize">{row.key.replace(/_/g, " ")}</span>
                        <div className="flex-1 h-5 bg-muted rounded overflow-hidden">
                          <div
                            className="h-full bg-indigo-500"
                            style={{ width: `${(row.clicks / maxRollupClicks) * 100}%` }}
                          />
                        </div>
                        <span className="w-10 text-right text-xs font-semibold tabular-nums">{row.clicks}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </Card>

      {/* Section 3: Two columns - Keywords & Subreddits */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Left: Top Keywords */}
        <Card className="p-5">
          <h3 className="text-sm font-semibold mb-4">Top Keywords by Priority Score</h3>
          {keywords.length === 0 ? (
            <EmptyState
              title="No keyword data yet"
              description="Keyword data will appear as you scan for opportunities."
            />
          ) : (
            <div className="space-y-3">
              {keywords.slice(0, 8).map((k, i) => (
                <div key={i} className="flex items-center gap-3 text-sm">
                  <span className="font-semibold min-w-[30px]">{i + 1}</span>
                  <span className="flex-1 truncate">{k.keyword}</span>
                  <div className="w-[60px] h-6 bg-muted rounded flex items-center justify-center overflow-hidden">
                    <div
                      className="h-full bg-primary flex items-center justify-center text-white text-[11px] font-semibold"
                      style={{ width: `${(k.priority_score / maxKeywords) * 100}%` }}
                    >
                      {k.priority_score > 0 ? Math.round(k.priority_score) : ""}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* Right: Top Subreddits */}
        <Card className="p-5">
          <h3 className="text-sm font-semibold mb-4">Top Subreddits by Fit Score</h3>
          {subreddits.length === 0 ? (
            <EmptyState
              title="No subreddit data yet"
              description="Subreddit data will appear as you run scans."
            />
          ) : (
            <div className="space-y-3">
              {subreddits.slice(0, 8).map((s, i) => (
                <div key={i} className="flex items-center gap-3 text-sm">
                  <span className="font-semibold min-w-[30px]">{i + 1}</span>
                  <span className="flex-1 truncate">r/{s.name}</span>
                  <div className="w-[60px] h-6 bg-muted rounded flex items-center justify-center overflow-hidden">
                    <div
                      className="h-full bg-primary flex items-center justify-center text-white text-[11px] font-semibold"
                      style={{ width: `${(s.fit_score / maxSubreddits) * 100}%` }}
                    >
                      {Math.round(s.fit_score)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      {/* Section 4: Recent Activity Timeline */}
      <Card className="p-5">
        <h3 className="text-sm font-semibold mb-4">Recent Activity</h3>
        {activity.length === 0 ? (
          <EmptyState
            title="No activity yet"
            description="Analytics data will appear as you use the platform. Run your first scan to get started."
          />
        ) : (
          <div className="space-y-3">
            {activity.slice(0, 12).map(evt => (
              <div
                key={evt.id}
                className="flex items-center gap-3 p-3 bg-muted rounded-xl text-sm"
              >
                <div className="w-2 h-2 rounded-full bg-primary shrink-0" />
                <div className="flex-1">
                  <strong>{formatActivityLabel(evt)}</strong>
                </div>
                <div className="text-xs text-muted-foreground whitespace-nowrap">
                  {evt.created_at ? new Date(evt.created_at).toLocaleString() : ""}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
