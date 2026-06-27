"use client";

import { useEffect, useState } from "react";
import { Loader2, Globe, Sparkles, Save, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  getCompanies,
  createCompany,
  updateCompany,
  analyzeCompanyWebsite,
  type CompanyProfile,
} from "@/lib/api/company";
import { useToast } from "@/stores/toast";
import type { StepStatus } from "@/stores/workflow-store";

interface Props {
  token: string;
  onStatusChange: (status: StepStatus) => void;
  onSummary?: (summary: string) => void;
  onContinue: () => void;
}

const BLANK: CompanyProfile = {
  id: 0,
  workspace_id: 0,
  name: "",
  website_url: null,
  description: null,
  category: null,
  target_audience: null,
  geography: null,
  language: "en",
  features: "",
  benefits: "",
  pain_points: "",
  competitors: "",
  brand_voice: null,
  preferred_cta: null,
  extracted_summary: null,
  extracted_keywords: "",
  extracted_pain_points: "",
  extracted_competitors: "",
  is_active: true,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

export function StepCompany({ token, onStatusChange, onSummary, onContinue }: Props) {
  const { success, error } = useToast();
  const [company, setCompany] = useState<CompanyProfile>(BLANK);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisInterval, setAnalysisInterval] = useState<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      if (analysisInterval) clearInterval(analysisInterval);
    };
  }, [analysisInterval]);

  useEffect(() => {
    void load();
  }, [token]);

  async function load() {
    setLoading(true);
    try {
      const list = await getCompanies(token);
      const active = list.find((c) => c.is_active) ?? list[0] ?? null;
      if (active) {
        setCompany(active);
        onStatusChange(active.name ? "done" : "partial");
        if (active.name) onSummary?.(active.website_url ? `${active.name} · ${active.website_url}` : active.name);
      }
    } catch {
      /* first time — no company yet */
    }
    setLoading(false);
  }

  async function handleSave() {
    setSaving(true);
    try {
      const {
        id, workspace_id, created_at, updated_at,
        extracted_summary, extracted_keywords, extracted_pain_points, extracted_competitors,
        is_active, ...payload
      } = company;
      let saved: CompanyProfile;
      if (company.id) {
        saved = await updateCompany(token, company.id, payload);
      } else {
        saved = await createCompany(token, payload);
      }
      setCompany(saved);
      onStatusChange(saved.name ? "done" : "partial");
      if (saved.name) onSummary?.(saved.website_url ? `${saved.name} · ${saved.website_url}` : saved.name);
      success("Saved", "Company profile updated.");
    } catch (err) {
      error("Save failed", err instanceof Error ? err.message : "Unknown error");
    }
    setSaving(false);
  }

  async function handleAnalyze() {
    if (!company.id || !company.website_url) return;
    setAnalyzing(true);
    try {
      await analyzeCompanyWebsite(token, company.id);
      success("Analysis started", "Refreshing in the background…");
      // Poll for 90s
      let attempts = 0;
      const iv = setInterval(async () => {
        attempts++;
        try {
          const list = await getCompanies(token);
          const updated = list.find((c) => c.id === company.id);
          if (updated?.extracted_summary && updated.extracted_summary !== company.extracted_summary) {
            setCompany(updated);
            clearInterval(iv);
            setAnalysisInterval(null);
            setAnalyzing(false);
            success("Analysis complete", "Brand intelligence updated.");
          }
        } catch { /* ignore */ }
        if (attempts >= 30) {
          clearInterval(iv);
          setAnalysisInterval(null);
          setAnalyzing(false);
        }
      }, 3000);
      setAnalysisInterval(iv);
    } catch (err) {
      error("Analysis failed", err instanceof Error ? err.message : "Unknown error");
      setAnalyzing(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 py-4 text-muted-foreground text-sm">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading company profile…
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Core fields */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="space-y-1.5">
          <Label htmlFor="wf-company-name">Company Name</Label>
          <Input
            id="wf-company-name"
            value={company.name}
            onChange={(e) => setCompany({ ...company, name: e.target.value })}
            placeholder="Acme Inc."
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="wf-website">Website URL</Label>
          <div className="flex gap-2">
            <Input
              id="wf-website"
              type="url"
              value={company.website_url ?? ""}
              onChange={(e) => setCompany({ ...company, website_url: e.target.value })}
              placeholder="https://example.com"
              className="flex-1"
            />
            {company.website_url && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleAnalyze}
                disabled={analyzing || !company.id}
                title="AI-analyze the website to extract brand intelligence"
              >
                {analyzing ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Sparkles className="h-3.5 w-3.5" />
                )}
              </Button>
            )}
          </div>
          {!company.id && (
            <p className="text-[11px] text-muted-foreground">Save first to enable AI analysis</p>
          )}
        </div>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="wf-desc">Description</Label>
        <Textarea
          id="wf-desc"
          value={company.description ?? ""}
          onChange={(e) => setCompany({ ...company, description: e.target.value })}
          placeholder="What your product does and who it's for"
          rows={2}
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="space-y-1.5">
          <Label htmlFor="wf-audience">Target Audience</Label>
          <Input
            id="wf-audience"
            value={company.target_audience ?? ""}
            onChange={(e) => setCompany({ ...company, target_audience: e.target.value })}
            placeholder="e.g. Marketing teams, SaaS founders"
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="wf-voice">Brand Voice</Label>
          <Input
            id="wf-voice"
            value={company.brand_voice ?? ""}
            onChange={(e) => setCompany({ ...company, brand_voice: e.target.value })}
            placeholder="e.g. Professional, witty, direct"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="space-y-1.5">
          <Label htmlFor="wf-competitors">Competitors (comma-separated)</Label>
          <Input
            id="wf-competitors"
            value={company.competitors ?? ""}
            onChange={(e) => setCompany({ ...company, competitors: e.target.value })}
            placeholder="CompetitorA, CompetitorB"
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="wf-cta">Preferred CTA</Label>
          <Input
            id="wf-cta"
            value={company.preferred_cta ?? ""}
            onChange={(e) => setCompany({ ...company, preferred_cta: e.target.value })}
            placeholder="Start a free trial, Book a demo"
          />
        </div>
      </div>

      {/* AI-extracted intelligence */}
      {company.extracted_summary && (
        <div className="rounded-lg border bg-muted/30 p-4 space-y-2">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide flex items-center gap-1.5">
            <Globe className="h-3.5 w-3.5" />
            Extracted Brand Intelligence
          </p>
          <p className="text-sm text-foreground/80 leading-relaxed">{company.extracted_summary}</p>
          {company.extracted_keywords && (
            <p className="text-xs text-muted-foreground">
              <span className="font-medium">Keywords:</span> {company.extracted_keywords}
            </p>
          )}
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center justify-between pt-2">
        <Button variant="outline" onClick={handleSave} disabled={saving}>
          {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
          Save
        </Button>
        <Button onClick={async () => { await handleSave(); onContinue(); }} disabled={saving || !company.name}>
          Continue
          <ArrowRight className="h-3.5 w-3.5 ml-1" />
        </Button>
      </div>
    </div>
  );
}
