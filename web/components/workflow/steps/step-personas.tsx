"use client";

import { useEffect, useState } from "react";
import { Loader2, Sparkles, Users, X, Plus, ArrowRight, ChevronDown, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { apiRequest, type Persona } from "@/lib/api";
import { getPersonas, createPersona, deletePersona } from "@/lib/api/personas";
import { useToast } from "@/stores/toast";
import type { StepStatus } from "@/stores/workflow-store";

const BLANK_PERSONA = {
  name: "",
  role: "",
  summary: "",
  pain_points: [] as string[],
  goals: [] as string[],
  triggers: [] as string[],
  preferred_subreddits: [] as string[],
  source: "manual",
  is_active: true,
};

interface Props {
  token: string;
  projectId: number | null;
  onStatusChange: (status: StepStatus) => void;
  onSummary?: (summary: string) => void;
  onContinue: () => void;
}

export function StepPersonas({ token, projectId, onStatusChange, onSummary, onContinue }: Props) {
  const { success, error } = useToast();
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [draft, setDraft] = useState(BLANK_PERSONA);
  const [creating, setCreating] = useState(false);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  useEffect(() => {
    if (projectId) void load();
  }, [projectId, token]);

  async function load() {
    setLoading(true);
    try {
      const data = await getPersonas(token, projectId!);
      setPersonas(data);
      onStatusChange(data.length > 0 ? "done" : "empty");
      onSummary?.(data.length > 0 ? `${data.length} persona${data.length !== 1 ? "s" : ""}` : "None yet");
    } catch {
      onStatusChange("empty");
    }
    setLoading(false);
  }

  async function generate() {
    if (!projectId) return;
    setGenerating(true);
    try {
      await apiRequest(
        `/v1/personas/generate?project_id=${projectId}&count=3`,
        { method: "POST", headers: { Authorization: `Bearer ${token}` } }
      );
      success("Personas generated", "Refreshing…");
      await load();
    } catch (err) {
      error("Generation failed", err instanceof Error ? err.message : "Make sure Company Setup is complete");
    }
    setGenerating(false);
  }

  async function create() {
    if (!projectId || !draft.name) return;
    setCreating(true);
    try {
      await createPersona(token, projectId, draft as Partial<Persona>);
      setDraft(BLANK_PERSONA);
      setShowForm(false);
      await load();
    } catch (err) {
      error("Failed to create persona", err instanceof Error ? err.message : "");
    }
    setCreating(false);
  }

  async function remove(id: number) {
    try {
      await deletePersona(token, id);
      setPersonas((prev) => {
        const next = prev.filter((p) => p.id !== id);
        onStatusChange(next.length > 0 ? "done" : "empty");
        return next;
      });
    } catch (err) {
      error("Failed to delete", err instanceof Error ? err.message : "");
    }
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 py-4 text-muted-foreground text-sm">
        <Loader2 className="h-4 w-4 animate-spin" /> Loading personas…
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Note about why personas matter */}
      <p className="text-xs text-muted-foreground bg-muted/40 rounded-lg px-3 py-2 border border-border">
        Personas refine relevance scoring — the AI uses their pain points and triggers to rank opportunities higher when they match your ideal buyer.
      </p>

      {/* Existing personas */}
      {personas.length > 0 ? (
        <div className="space-y-2">
          {personas.map((p) => (
            <div key={p.id} className="rounded-lg border bg-card">
              <button
                className="w-full flex items-start justify-between gap-3 p-3 text-left"
                onClick={() => setExpandedId(expandedId === p.id ? null : p.id)}
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className="h-7 w-7 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                    <Users className="h-3.5 w-3.5 text-primary" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-semibold truncate">{p.name}</p>
                    {p.role && <p className="text-xs text-muted-foreground truncate">{p.role}</p>}
                  </div>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  {p.source === "ai" && (
                    <Badge variant="secondary" className="text-[10px] h-4">AI</Badge>
                  )}
                  {expandedId === p.id ? (
                    <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
                  ) : (
                    <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
                  )}
                </div>
              </button>
              {expandedId === p.id && (
                <div className="px-3 pb-3 border-t pt-3 space-y-2">
                  {p.summary && <p className="text-sm text-muted-foreground">{p.summary}</p>}
                  {p.pain_points && p.pain_points.length > 0 && (
                    <div>
                      <p className="text-xs font-medium mb-1">Pain points</p>
                      <div className="flex flex-wrap gap-1.5">
                        {p.pain_points.map((pt, i) => (
                          <span key={i} className="text-xs bg-muted px-2 py-0.5 rounded-full">{pt}</span>
                        ))}
                      </div>
                    </div>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-destructive hover:text-destructive h-7 text-xs"
                    onClick={() => void remove(p.id)}
                  >
                    <X className="h-3 w-3 mr-1" />
                    Remove
                  </Button>
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="rounded-lg border border-dashed p-5 text-center text-sm text-muted-foreground">
          No personas yet. Generate with AI or create manually.
        </div>
      )}

      {/* Manual create form */}
      {showForm && (
        <div className="rounded-lg border bg-muted/20 p-4 space-y-3">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">New Persona</p>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label className="text-xs">Name *</Label>
              <Input
                value={draft.name}
                onChange={(e) => setDraft({ ...draft, name: e.target.value })}
                placeholder="e.g. Growth Marketer"
                className="h-8 text-sm"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Role</Label>
              <Input
                value={draft.role}
                onChange={(e) => setDraft({ ...draft, role: e.target.value })}
                placeholder="e.g. Head of Marketing"
                className="h-8 text-sm"
              />
            </div>
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Summary</Label>
            <Textarea
              value={draft.summary}
              onChange={(e) => setDraft({ ...draft, summary: e.target.value })}
              placeholder="Brief description of this persona and their context…"
              rows={2}
              className="text-sm"
            />
          </div>
          <div className="flex gap-2">
            <Button size="sm" onClick={create} disabled={creating || !draft.name}>
              {creating ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
              Create
            </Button>
            <Button size="sm" variant="ghost" onClick={() => { setShowForm(false); setDraft(BLANK_PERSONA); }}>
              Cancel
            </Button>
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center justify-between pt-2">
        <div className="flex gap-2">
          <Button variant="outline" onClick={generate} disabled={generating}>
            {generating ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
            {generating ? "Generating…" : "AI Generate"}
          </Button>
          {!showForm && (
            <Button variant="ghost" size="sm" onClick={() => setShowForm(true)}>
              <Plus className="h-3.5 w-3.5 mr-1" />
              Manual
            </Button>
          )}
        </div>
        <Button onClick={onContinue}>
          Continue
          <ArrowRight className="h-3.5 w-3.5 ml-1" />
        </Button>
      </div>
    </div>
  );
}
