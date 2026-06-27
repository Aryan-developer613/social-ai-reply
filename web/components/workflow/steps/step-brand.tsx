"use client";

import { useEffect, useState } from "react";
import { Loader2, Sparkles, X, Plus, ArrowRight, Tag } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { apiRequest } from "@/lib/api";
import { getCompanies } from "@/lib/api/company";
import { useToast } from "@/stores/toast";
import type { StepStatus } from "@/stores/workflow-store";

interface SignalItem {
  id: number;
  keyword: string;
  is_active: boolean;
  priority_score?: number;
  source?: string;
}

interface Props {
  token: string;
  projectId: number | null;
  onStatusChange: (status: StepStatus) => void;
  onSummary?: (summary: string) => void;
  onContinue: () => void;
}

export function StepBrand({ token, projectId, onStatusChange, onSummary, onContinue }: Props) {
  const { success, error } = useToast();
  const [keywords, setKeywords] = useState<SignalItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [newKw, setNewKw] = useState("");
  const [adding, setAdding] = useState(false);

  useEffect(() => {
    if (projectId) void load();
  }, [projectId, token]);

  async function load() {
    setLoading(true);
    try {
      const data = await apiRequest<SignalItem[]>(
        `/v1/discovery/keywords?project_id=${projectId}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setKeywords(data);
      onStatusChange(data.length > 0 ? "done" : "empty");
      onSummary?.(data.length > 0 ? `${data.length} keywords` : "No keywords");
    } catch {
      /* no keywords yet */
      onStatusChange("empty");
    }
    setLoading(false);
  }

  async function generate() {
    if (!projectId) return;
    setGenerating(true);
    try {
      await apiRequest(
        `/v1/discovery/keywords/generate?project_id=${projectId}`,
        { method: "POST", body: JSON.stringify({ count: 15 }), headers: { Authorization: `Bearer ${token}` } }
      );
      success("Keywords generated", "Refreshing list…");
      await load();
    } catch (err) {
      // Also try company-level keyword generation as fallback
      try {
        const companies = await getCompanies(token);
        const active = companies.find((c) => c.is_active) ?? companies[0];
        if (active?.id) {
          await apiRequest(
            `/v1/companies/${active.id}/keywords/generate`,
            { method: "POST", headers: { Authorization: `Bearer ${token}` } }
          );
          success("Keywords generated via brand", "Refreshing…");
          await load();
          return;
        }
      } catch { /* ignore secondary attempt */ }
      error("Generation failed", err instanceof Error ? err.message : "Check company setup first");
    }
    setGenerating(false);
  }

  async function addKeyword() {
    if (!newKw.trim() || !projectId) return;
    setAdding(true);
    try {
      await apiRequest(
        `/v1/discovery/keywords?project_id=${projectId}`,
        {
          method: "POST",
          body: JSON.stringify({ keyword: newKw.trim(), rationale: "Manual", priority_score: 5, is_active: true }),
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      setNewKw("");
      await load();
    } catch (err) {
      error("Failed to add keyword", err instanceof Error ? err.message : "");
    }
    setAdding(false);
  }

  async function removeKeyword(id: number) {
    try {
      await apiRequest(
        `/v1/discovery/keywords/${id}`,
        { method: "DELETE", headers: { Authorization: `Bearer ${token}` } }
      );
      setKeywords((prev) => prev.filter((k) => k.id !== id));
      onStatusChange(keywords.length - 1 > 0 ? "done" : "empty");
    } catch (err) {
      error("Failed to remove", err instanceof Error ? err.message : "");
    }
  }

  async function toggleKeyword(kw: SignalItem) {
    try {
      await apiRequest(
        `/v1/discovery/keywords/${kw.id}`,
        {
          method: "PATCH",
          body: JSON.stringify({ is_active: !kw.is_active }),
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      setKeywords((prev) =>
        prev.map((k) => (k.id === kw.id ? { ...k, is_active: !k.is_active } : k))
      );
    } catch { /* optimistic only */ }
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 py-4 text-muted-foreground text-sm">
        <Loader2 className="h-4 w-4 animate-spin" /> Loading keywords…
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Keyword pills */}
      {keywords.length > 0 ? (
        <div className="space-y-3">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            {keywords.filter((k) => k.is_active).length} active · {keywords.filter((k) => !k.is_active).length} paused
          </p>
          <div className="flex flex-wrap gap-2">
            {keywords.map((kw) => (
              <div
                key={kw.id}
                className={`group flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-colors cursor-pointer select-none ${
                  kw.is_active
                    ? "bg-primary/10 border-primary/30 text-primary hover:bg-primary/15"
                    : "bg-muted border-border text-muted-foreground opacity-60"
                }`}
                onClick={() => void toggleKeyword(kw)}
                title={kw.is_active ? "Click to pause" : "Click to activate"}
              >
                <Tag className="h-2.5 w-2.5 shrink-0" />
                {kw.keyword}
                {kw.source === "ai" && (
                  <span className="text-[9px] text-muted-foreground">AI</span>
                )}
                <button
                  onClick={(e) => { e.stopPropagation(); void removeKeyword(kw.id); }}
                  className="opacity-0 group-hover:opacity-100 transition-opacity ml-0.5 text-muted-foreground hover:text-destructive"
                >
                  <X className="h-2.5 w-2.5" />
                </button>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="rounded-lg border border-dashed p-5 text-center text-sm text-muted-foreground">
          No keywords yet. Generate AI keywords or add manually.
        </div>
      )}

      {/* Add manually */}
      <div className="flex gap-2">
        <Input
          value={newKw}
          onChange={(e) => setNewKw(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && void addKeyword()}
          placeholder="Add a keyword…"
          className="flex-1 h-9 text-sm"
        />
        <Button
          variant="outline"
          size="sm"
          onClick={addKeyword}
          disabled={adding || !newKw.trim()}
        >
          {adding ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
        </Button>
      </div>

      {/* Actions */}
      <div className="flex items-center justify-between pt-2">
        <Button
          variant="outline"
          onClick={generate}
          disabled={generating}
        >
          {generating ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
          {generating ? "Generating…" : "AI Generate Keywords"}
        </Button>
        <Button onClick={onContinue} disabled={keywords.length === 0}>
          Continue
          <ArrowRight className="h-3.5 w-3.5 ml-1" />
        </Button>
      </div>
    </div>
  );
}
