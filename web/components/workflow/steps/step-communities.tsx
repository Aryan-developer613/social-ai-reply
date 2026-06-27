"use client";

import { useEffect, useState } from "react";
import { Loader2, Sparkles, X, Plus, ArrowRight, Hash, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { apiRequest, type MonitoredSubreddit } from "@/lib/api";
import { useToast } from "@/stores/toast";
import type { StepStatus } from "@/stores/workflow-store";

interface Props {
  token: string;
  projectId: number | null;
  onStatusChange: (status: StepStatus) => void;
  onSummary?: (summary: string) => void;
  onContinue: () => void;
}

export function StepCommunities({ token, projectId, onStatusChange, onSummary, onContinue }: Props) {
  const { success, error } = useToast();
  const [subreddits, setSubreddits] = useState<MonitoredSubreddit[]>([]);
  const [loading, setLoading] = useState(true);
  const [discovering, setDiscovering] = useState(false);
  const [newSub, setNewSub] = useState("");
  const [adding, setAdding] = useState(false);

  useEffect(() => {
    if (projectId) void load();
  }, [projectId, token]);

  async function load() {
    setLoading(true);
    try {
      const data = await apiRequest<MonitoredSubreddit[]>(
        `/v1/discovery/subreddits?project_id=${projectId}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setSubreddits(data);
      onStatusChange(data.length > 0 ? "done" : "empty");
      onSummary?.(data.length > 0 ? `${data.length} communit${data.length !== 1 ? "ies" : "y"}` : "None yet");
    } catch {
      onStatusChange("empty");
    }
    setLoading(false);
  }

  async function discover() {
    if (!projectId) return;
    setDiscovering(true);
    try {
      await apiRequest(
        `/v1/discovery/subreddits/discover?project_id=${projectId}`,
        {
          method: "POST",
          body: JSON.stringify({ max_subreddits: 10 }),
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      success("Communities discovered", "Refreshing list…");
      await load();
    } catch (err) {
      error("Discovery failed", err instanceof Error ? err.message : "Make sure keywords are configured first");
    }
    setDiscovering(false);
  }

  async function addSubreddit() {
    if (!newSub.trim() || !projectId) return;
    setAdding(true);
    const name = newSub.trim().replace(/^r\//i, "");
    try {
      await apiRequest(
        `/v1/discovery/subreddits?project_id=${projectId}`,
        {
          method: "POST",
          body: JSON.stringify({ name }),
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      setNewSub("");
      await load();
    } catch (err) {
      error("Failed to add", err instanceof Error ? err.message : "");
    }
    setAdding(false);
  }

  async function remove(id: number) {
    try {
      await apiRequest(
        `/v1/discovery/subreddits/${id}`,
        { method: "DELETE", headers: { Authorization: `Bearer ${token}` } }
      );
      setSubreddits((prev) => {
        const next = prev.filter((s) => s.id !== id);
        onStatusChange(next.length > 0 ? "done" : "empty");
        return next;
      });
    } catch (err) {
      error("Failed to remove", err instanceof Error ? err.message : "");
    }
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 py-4 text-muted-foreground text-sm">
        <Loader2 className="h-4 w-4 animate-spin" /> Loading communities…
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Community list */}
      {subreddits.length > 0 ? (
        <div className="space-y-1.5">
          {subreddits.map((sub) => (
            <div
              key={sub.id}
              className="group flex items-center justify-between rounded-lg border bg-card px-3 py-2.5 hover:bg-muted/30 transition-colors"
            >
              <div className="flex items-center gap-2.5 min-w-0">
                <Hash className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                <span className="text-sm font-medium truncate">r/{sub.name}</span>
                {sub.fit_score != null && (
                  <Badge
                    variant="outline"
                    className="text-[10px] h-4 shrink-0"
                    title="Fit score: how relevant this community is to your brand"
                  >
                    fit {sub.fit_score}
                  </Badge>
                )}
                {sub.subscribers != null && (
                  <span className="text-xs text-muted-foreground shrink-0">
                    {(sub.subscribers / 1000).toFixed(0)}k
                  </span>
                )}
              </div>
              <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                <a
                  href={`https://reddit.com/r/${sub.name}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-1 text-muted-foreground hover:text-foreground"
                  onClick={(e) => e.stopPropagation()}
                >
                  <ExternalLink className="h-3 w-3" />
                </a>
                <button
                  onClick={() => void remove(sub.id)}
                  className="p-1 text-muted-foreground hover:text-destructive"
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="rounded-lg border border-dashed p-5 text-center text-sm text-muted-foreground">
          No communities yet. Discover with AI or add manually.
        </div>
      )}

      {/* Add manually */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">r/</span>
          <Input
            value={newSub}
            onChange={(e) => setNewSub(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && void addSubreddit()}
            placeholder="subredditname"
            className="pl-7 h-9 text-sm"
          />
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={addSubreddit}
          disabled={adding || !newSub.trim()}
        >
          {adding ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
        </Button>
      </div>

      {/* Actions */}
      <div className="flex items-center justify-between pt-2">
        <Button variant="outline" onClick={discover} disabled={discovering}>
          {discovering ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
          {discovering ? "Discovering…" : "AI Discover"}
        </Button>
        <Button onClick={onContinue} disabled={subreddits.length === 0}>
          Continue
          <ArrowRight className="h-3.5 w-3.5 ml-1" />
        </Button>
      </div>
    </div>
  );
}
