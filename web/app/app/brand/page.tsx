"use client";

import { FormEvent, useEffect, useState } from "react";
import { Loader2, Globe, Users, Target, Share2 } from "lucide-react";

import { useAuth } from "@/components/auth/auth-provider";
import { useToast } from "@/stores/toast";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { apiRequest, type BrandProfile, type Dashboard } from "@/lib/api";
import { fetchDashboard, getCurrentProject } from "@/lib/workspace-data";
import { useSelectedProjectId } from "@/hooks/use-selected-project";
import { PageHeader } from "@/components/shared/page-header";
import { VoiceProfilesSection } from "@/components/brand/voice-profiles-section";

function CircularProgress({ value, size = 48, strokeWidth = 4 }: { value: number; size?: number; strokeWidth?: number }) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (value / 100) * circumference;
  const color = value >= 80 ? "text-emerald-500" : value >= 50 ? "text-yellow-500" : "text-red-500";

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          className="text-muted/50"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className={color}
        />
      </svg>
      <span className={`absolute text-xs font-bold ${color}`}>{value}%</span>
    </div>
  );
}

export default function BrandPage() {
  const { token } = useAuth();
  const { success, error } = useToast();
  const selectedProjectId = useSelectedProjectId();
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [brand, setBrand] = useState<BrandProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [brandLoadError, setBrandLoadError] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isFilling, setIsFilling] = useState(false);
  const [activeTab, setActiveTab] = useState("profile");

  const project = dashboard ? getCurrentProject(dashboard) : null;

  useEffect(() => {
    if (!token) {
      return;
    }
    fetchDashboard(token, selectedProjectId)
      .then(setDashboard)
      .catch((err) => {
        error("Failed to load", err.message);
      });
  }, [token, error, selectedProjectId]);

  useEffect(() => {
    if (!token || !project) {
      setLoading(false);
      return;
    }
    setLoading(true);
    apiRequest<BrandProfile>(`/v1/brand/${project.id}`, {}, token)
      .then((data) => {
        setBrand(data);
        setLoading(false);
      })
      .catch((err) => {
        error("Failed to load brand", err.message);
        setBrandLoadError(true);
        setLoading(false);
      });
  }, [project, token, error]);

  async function fillFromWebsite() {
    if (!token || !project || !brand?.website_url) {
      return;
    }
    setIsFilling(true);
    try {
      await apiRequest<{ task_id: string }>(`/v1/brand/${project.id}/analyze`, {
        method: "POST",
        body: JSON.stringify({ website_url: brand.website_url })
      }, token);
      success("Analysis started", "Your website is being analyzed in the background. Check back in a minute.");
    } catch (err) {
      error("Analysis failed", err instanceof Error ? err.message : "Could not read the website.");
    } finally {
      setIsFilling(false);
    }
  }

  async function analyzeWebsite(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await fillFromWebsite();
  }

  async function saveBrand(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token || !project || !brand) {
      return;
    }
    setIsSaving(true);
    try {
      const payload = await apiRequest<BrandProfile>(`/v1/brand/${project.id}`, {
        method: "PUT",
        body: JSON.stringify(brand)
      }, token);
      setBrand(payload);
      success("Saved", "Your brand details have been saved.");
    } catch (err) {
      error("Save failed", err instanceof Error ? err.message : "Could not save product details.");
    } finally {
      setIsSaving(false);
    }
  }

  const calculateCompletion = () => {
    if (!brand) return 0;
    const fields = [
      brand.brand_name,
      brand.website_url,
      brand.product_summary,
      brand.target_audience,
      brand.voice_notes,
      brand.call_to_action,
      brand.reddit_username,
      brand.linkedin_url
    ];
    const filled = fields.filter(f => f && f.trim().length > 0).length;
    return Math.round((filled / fields.length) * 100);
  };

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card><CardContent><Skeleton className="h-32 w-full rounded-lg" /></CardContent></Card>
        <Card><CardContent><Skeleton className="h-32 w-full rounded-lg" /></CardContent></Card>
      </div>
    );
  }

  if (!brand) {
    if (brandLoadError) {
      return (
        <Card>
          <CardContent className="flex flex-col items-center justify-center p-8 text-center">
            <span className="text-4xl mb-4">⚠️</span>
            <h3 className="text-base font-semibold mb-1">Failed to load brand profile</h3>
            <p className="text-sm text-muted-foreground">There was an error loading your brand data. Please try refreshing the page.</p>
          </CardContent>
        </Card>
      );
    }
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center p-8 text-center">
          <span className="text-4xl mb-4">🏢</span>
          <h3 className="text-base font-semibold mb-1">No brand yet</h3>
          <p className="text-sm text-muted-foreground">Go to Home and create a business first to get started.</p>
        </CardContent>
      </Card>
    );
  }

  const completion = calculateCompletion();

  return (
    <div className="space-y-8">
      <Tabs value={activeTab} onValueChange={setActiveTab}>
      <PageHeader
        title="Brand Profile"
        actions={
          <div className="flex items-center gap-3">
            <CircularProgress value={completion} />
            <div className="text-right hidden sm:block">
              <div className="text-xs text-muted-foreground">Profile completeness</div>
              <div className="text-sm font-semibold">{completion}%</div>
            </div>
          </div>
        }
        tabs={
          <TabsList>
            <TabsTrigger value="profile">Brand Profile</TabsTrigger>
            <TabsTrigger value="voice">Voice profiles</TabsTrigger>
            <TabsTrigger value="analysis">Analysis</TabsTrigger>
          </TabsList>
        }
      />

      <TabsContent value="profile">
        <form onSubmit={saveBrand}>
            <div className="grid gap-8">
              {/* Identity Group */}
              <Card>
                <CardContent className="p-6">
                  <div className="flex items-center gap-2 mb-4">
                    <Globe className="h-4 w-4 text-muted-foreground" />
                    <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Identity</span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="brand-name">Business name</Label>
                      <Input
                        id="brand-name"
                        value={brand.brand_name}
                        onChange={(event) => setBrand({ ...brand, brand_name: event.target.value })}
                        placeholder="e.g., Acme Inc."
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="website-url">Website URL</Label>
                      <Input
                        id="website-url"
                        type="url"
                        value={brand.website_url ?? ""}
                        onChange={(event) => setBrand({ ...brand, website_url: event.target.value })}
                        placeholder="https://example.com"
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Audience Group */}
              <Card>
                <CardContent className="p-6">
                  <div className="flex items-center gap-2 mb-4">
                    <Users className="h-4 w-4 text-muted-foreground" />
                    <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Audience</span>
                  </div>
                  <div className="grid grid-cols-1 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="target-audience">Who is it for?</Label>
                      <Textarea
                        id="target-audience"
                        value={brand.target_audience ?? ""}
                        onChange={(event) => setBrand({ ...brand, target_audience: event.target.value })}
                        placeholder="Who are your ideal customers? What do they look like?"
                        rows={3}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="voice-notes">How should replies sound?</Label>
                      <Textarea
                        id="voice-notes"
                        value={brand.voice_notes ?? ""}
                        onChange={(event) => setBrand({ ...brand, voice_notes: event.target.value })}
                        placeholder="Tone, personality, values... e.g., 'professional but friendly'"
                        rows={3}
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Strategy Group */}
              <Card>
                <CardContent className="p-6">
                  <div className="flex items-center gap-2 mb-4">
                    <Target className="h-4 w-4 text-muted-foreground" />
                    <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Strategy</span>
                  </div>
                  <div className="grid grid-cols-1 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="product-summary">What do you sell?</Label>
                      <Textarea
                        id="product-summary"
                        value={brand.product_summary ?? ""}
                        onChange={(event) => setBrand({ ...brand, product_summary: event.target.value })}
                        placeholder="Describe your product or service in simple terms..."
                        rows={3}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="cta">What soft next step is okay to mention?</Label>
                      <Textarea
                        id="cta"
                        value={brand.call_to_action ?? ""}
                        onChange={(event) => setBrand({ ...brand, call_to_action: event.target.value })}
                        placeholder="e.g., 'Visit our blog', 'Email us', etc."
                        rows={2}
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Social Group */}
              <Card>
                <CardContent className="p-6">
                  <div className="flex items-center gap-2 mb-4">
                    <Share2 className="h-4 w-4 text-muted-foreground" />
                    <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Social</span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="reddit-username">Reddit username</Label>
                      <Input
                        id="reddit-username"
                        value={brand.reddit_username ?? ""}
                        onChange={(event) => setBrand({ ...brand, reddit_username: event.target.value })}
                        placeholder="Optional: your Reddit username"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="linkedin-url">LinkedIn URL</Label>
                      <Input
                        id="linkedin-url"
                        type="url"
                        value={brand.linkedin_url ?? ""}
                        onChange={(event) => setBrand({ ...brand, linkedin_url: event.target.value })}
                        placeholder="Optional: https://linkedin.com/company/..."
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Action Buttons */}
              <div className="flex flex-wrap gap-2">
                <Button type="submit" disabled={isSaving}>
                  {isSaving && <Loader2 className="h-4 w-4 animate-spin" />}
                  Save details
                </Button>
                <Button
                  variant="secondary"
                  type="button"
                  onClick={fillFromWebsite}
                  disabled={!brand.website_url || isFilling}
                >
                  {isFilling && <Loader2 className="h-4 w-4 animate-spin" />}
                  Fill from website
                </Button>
              </div>
            </div>
          </form>
      </TabsContent>

      <TabsContent value="voice">
        <VoiceProfilesSection token={token} projectId={project?.id ?? selectedProjectId} />
      </TabsContent>

      <TabsContent value="analysis">
        <Card>
          <CardContent className="p-6">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Website analysis</p>
            <h2 className="text-lg font-semibold mt-1">Fastest way to fill this page</h2>
            <p className="text-sm text-muted-foreground mb-6">Paste your website URL and click &quot;Analyze website&quot; to auto-fill fields, then edit as needed.</p>

            <form onSubmit={analyzeWebsite}>
              <div className="flex flex-wrap gap-2">
                <Button
                  variant="secondary"
                  type="submit"
                  disabled={!brand.website_url || isFilling}
                >
                  {isFilling && <Loader2 className="h-4 w-4 animate-spin" />}
                  Analyze website
                </Button>
              </div>
            </form>

            <div className="space-y-3 mt-6">
              <div className="rounded-xl border bg-card p-5">
                <strong className="text-sm font-semibold">Summary</strong>
                <p className="text-sm text-muted-foreground mt-1">
                  {brand.summary && brand.summary.trim() ? brand.summary : "No summary yet. Analyze your website to fill this."}
                </p>
              </div>
              <div className="rounded-xl border bg-card p-5">
                <strong className="text-sm font-semibold">Call to action</strong>
                <p className="text-sm text-muted-foreground mt-1">
                  {brand.call_to_action && brand.call_to_action.trim() ? brand.call_to_action : "No CTA yet. Analyze your website to fill this."}
                </p>
              </div>
              <div className="rounded-xl border bg-card p-5">
                <strong className="text-sm font-semibold">Last website scan</strong>
                <p className="text-sm text-muted-foreground mt-1">
                  {brand.last_analyzed_at ? new Date(brand.last_analyzed_at).toLocaleDateString() : "Not analyzed yet"}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </TabsContent>
      </Tabs>
    </div>
  );
}
