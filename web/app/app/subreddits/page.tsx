"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/components/auth/auth-provider";
import { useToast } from "@/stores/toast";
import { apiRequest, type Dashboard, type MonitoredSubreddit } from "@/lib/api";
import { fetchDashboard, getCurrentProject } from "@/lib/workspace-data";
import { useSelectedProjectId } from "@/hooks/use-selected-project";
import { ScoreBadge } from "@/components/shared/score-badge";
import { PageHeader } from "@/components/shared/page-header";
import { KPIGrid, type KPICardProps } from "@/components/shared/kpi-card";
import { EmptyState } from "@/components/shared/empty-state";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

type SortOption = "fit-score" | "activity-score" | "name";

export default function SubredditsPage() {
  const { token } = useAuth();
  const { success, error: toastError } = useToast();
  const selectedProjectId = useSelectedProjectId();
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [subreddits, setSubreddits] = useState<MonitoredSubreddit[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorState, setErrorState] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [refreshingId, setRefreshingId] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState<SortOption>("fit-score");
  const [activeTab, setActiveTab] = useState<"all" | "top">("all");

  const project = dashboard ? getCurrentProject(dashboard) : null;

  useEffect(() => {
    if (!token) {
      return;
    }
    fetchDashboard(token, selectedProjectId)
      .then(setDashboard)
      .catch((err) => {
        toastError(err.message);
        setLoading(false);
      });
  }, [token, selectedProjectId]);

  useEffect(() => {
    if (!token || !project) {
      return;
    }
    setLoading(true);
    setErrorState(null);
    apiRequest<MonitoredSubreddit[]>(`/v1/discovery/subreddits?project_id=${project.id}`, {}, token)
      .then((data) => { setSubreddits(data); setErrorState(null); })
      .catch((err) => {
        setErrorState(err.message);
        toastError(err.message);
      })
      .finally(() => setLoading(false));
  }, [project, token]);

  async function refreshAnalysis(subredditId: number) {
    if (!token) {
      return;
    }
    setRefreshingId(subredditId);
    try {
      const updated = await apiRequest<MonitoredSubreddit>(
        `/v1/subreddits/${subredditId}/analyze`,
        { method: "POST" },
        token
      );
      setSubreddits((rows) => rows.map((row) => (row.id === updated.id ? updated : row)));
      success("Analysis refreshed");
    } catch (err) {
      toastError((err as Error).message);
    } finally {
      setRefreshingId(null);
    }
  }

  // Filter communities based on tab and search query
  const filteredSubreddits = subreddits
    .filter((s) => {
      if (activeTab === "top" && s.fit_score < 70) {
        return false;
      }
      return s.name.toLowerCase().includes(searchQuery.toLowerCase());
    })
    .sort((a, b) => {
      switch (sortBy) {
        case "fit-score":
          return b.fit_score - a.fit_score;
        case "activity-score":
          return b.activity_score - a.activity_score;
        case "name":
          return a.name.localeCompare(b.name);
        default:
          return 0;
      }
    });

  // Calculate KPI metrics
  const avgFitScore = subreddits.length ? Math.round(subreddits.reduce((sum, s) => sum + s.fit_score, 0) / subreddits.length) : 0;
  const avgActivityScore = subreddits.length ? Math.round(subreddits.reduce((sum, s) => sum + s.activity_score, 0) / subreddits.length) : 0;
  const activeCount = subreddits.filter((s) => s.is_active).length;

  // KPI cards
  const kpiCards: KPICardProps[] = [
    { label: "Total Communities", value: subreddits.length },
    { label: "Avg Fit Score", value: avgFitScore },
    { label: "Avg Activity Score", value: avgActivityScore },
    { label: "Active", value: activeCount },
  ];

  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        title="Communities"
        description="Review which communities deserve active engagement. Scoring covers fit, activity, moderation risk, and audience signals."
        actions={
          <div className="flex flex-wrap gap-2">
            <Badge>Reddit live now</Badge>
            <Badge variant="secondary">Q and A pattern ready</Badge>
            <Badge variant="secondary">Forum pattern ready</Badge>
          </div>
        }
      />

      {message && (
        <div className="rounded-lg bg-muted px-4 py-3 text-sm">{message}</div>
      )}

      {/* KPI Cards */}
      {!loading && subreddits.length > 0 && (
        <KPIGrid cards={kpiCards} columns={4} className="grid-cols-2 md:grid-cols-4" />
      )}

      {/* Controls */}
      {!loading && subreddits.length > 0 && (
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:gap-4">
          {/* Tabs */}
          <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as "all" | "top")}>
            <TabsList>
              <TabsTrigger value="all">All Communities</TabsTrigger>
              <TabsTrigger value="top">Top Performers</TabsTrigger>
            </TabsList>
          </Tabs>

          <div className="flex flex-col gap-3 sm:flex-row sm:gap-3 flex-1">
            <Input
              type="text"
              placeholder="Filter by subreddit name..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="flex-1"
            />
            <Select value={sortBy} onValueChange={(v) => setSortBy((v ?? "fit-score") as SortOption)}>
              <SelectTrigger className="w-full sm:w-[200px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="fit-score">Sort by Fit Score</SelectItem>
                <SelectItem value="activity-score">Sort by Activity Score</SelectItem>
                <SelectItem value="name">Sort by Name</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="flex justify-center p-8">
          <Loader2 className="h-5 w-5 animate-spin" />
        </div>
      )}

      {/* Communities Card Grid */}
      {!loading && filteredSubreddits.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredSubreddits.map((subreddit) => (
            <Card key={subreddit.id} className="p-5 flex flex-col gap-3">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <strong className="text-lg">r/{subreddit.name}</strong>
                  {subreddit.title && (
                    <p className="mt-1 text-sm text-muted-foreground truncate">{subreddit.title}</p>
                  )}
                </div>
                <Button
                  onClick={() => refreshAnalysis(subreddit.id)}
                  disabled={refreshingId === subreddit.id}
                  variant="outline"
                  size="sm"
                  className="shrink-0"
                >
                  {refreshingId === subreddit.id ? (
                    <span className="inline-flex items-center gap-2">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Refreshing...
                    </span>
                  ) : (
                    "Refresh"
                  )}
                </Button>
              </div>

              {/* Description */}
              {subreddit.description && (
                <p className="text-sm text-muted-foreground line-clamp-2">
                  {subreddit.description}
                </p>
              )}

              {/* Scores */}
              <div className="flex flex-wrap gap-2">
                <div className="flex items-center gap-1.5">
                  <span className="text-xs text-muted-foreground">Fit</span>
                  <ScoreBadge score={subreddit.fit_score} />
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="text-xs text-muted-foreground">Activity</span>
                  <ScoreBadge score={subreddit.activity_score} />
                </div>
              </div>

              {/* Subscriber Count */}
              <div className="text-sm text-muted-foreground">
                {subreddit.subscribers.toLocaleString()} subscribers
              </div>

              {/* Analysis */}
              {subreddit.analyses[0] && (
                <div className="rounded-lg bg-muted px-4 py-3 text-sm">
                  <strong>Recommendation:</strong> {subreddit.analyses[0].recommendation}
                  {subreddit.analyses[0].audience_signals.length > 0 && (
                    <>
                      <br />
                      <strong className="text-sm">Audience signals:</strong> {subreddit.analyses[0].audience_signals.join(", ")}
                    </>
                  )}
                </div>
              )}

              {/* Rules Summary */}
              {subreddit.rules_summary && (
                <div className="text-sm text-muted-foreground">
                  <strong>Rules to watch:</strong> {subreddit.rules_summary}
                </div>
              )}
            </Card>
          ))}
        </div>
      )}

      {/* Error State (Issue #11 - distinguish error from empty) */}
      {!loading && errorState && (
        <Card className="p-6 text-center">
          <h3 className="text-sm font-semibold text-destructive">Failed to load communities</h3>
          <p className="mt-1 text-sm text-muted-foreground">{errorState}</p>
          <Button
            variant="outline"
            className="mt-4"
            size="sm"
            onClick={() => {
              setErrorState(null);
              if (token && project) {
                setLoading(true);
                apiRequest<MonitoredSubreddit[]>(`/v1/discovery/subreddits?project_id=${project.id}`, {}, token)
                  .then(setSubreddits)
                  .catch((err) => setErrorState(err.message))
                  .finally(() => setLoading(false));
              }
            }}
          >
            Retry
          </Button>
        </Card>
      )}

      {/* Empty States */}
      {!loading && !errorState && filteredSubreddits.length === 0 && subreddits.length === 0 && (
        <EmptyState
          title="No communities yet"
          description="Use the Find posts page to discover communities first."
        />
      )}

      {!loading && !errorState && filteredSubreddits.length === 0 && subreddits.length > 0 && (
        <EmptyState
          title="No communities match your filter"
          description="Try adjusting your search or sort options."
        />
      )}
    </div>
  );
}
