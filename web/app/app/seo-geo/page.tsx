"use client";

import { useEffect, useState, useRef } from "react";
import { Search, RefreshCw, Loader2 } from "lucide-react";

import { useAuth } from "@/components/auth/auth-provider";
import { useToast } from "@/stores/toast";
import { getErrorMessage } from "@/types/errors";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { getCompanies } from "@/lib/api/company";
import { getSeoAudit, getSeoGaps, runSeoAudit, type SeoIssue } from "@/lib/api/seo";
import { getGeoGaps, getGeoReadiness, runGeoAudit, type GeoGap, type GeoReadiness } from "@/lib/api/geo";

export default function SeoGeoPage() {
  const { token } = useAuth();
  const { success, error } = useToast();
  const [activeTab, setActiveTab] = useState("seo");
  const [companyId, setCompanyId] = useState<number | null>(null);

  const [seoIssues, setSeoIssues] = useState<SeoIssue[]>([]);
  const [seoGaps, setSeoGaps] = useState<SeoIssue[]>([]);
  const [geoGaps, setGeoGaps] = useState<GeoGap[]>([]);
  const [geoReadiness, setGeoReadiness] = useState<GeoReadiness | null>(null);

  const [loadingSeo, setLoadingSeo] = useState(true);
  const [loadingGeo, setLoadingGeo] = useState(true);
  const [seoError, setSeoError] = useState<string | null>(null);
  const [geoError, setGeoError] = useState<string | null>(null);
  const [runningAgent, setRunningAgent] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!token) return;
    void loadData();
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [token]);

  async function loadData() {
    if (!token) return;
    setLoadingSeo(true);
    setLoadingGeo(true);
    setSeoError(null);
    setGeoError(null);
    try {
      const companies = await getCompanies(token);
      const company = companies.find((c) => c.is_active) ?? companies[0];
      if (!company) {
        setLoadingSeo(false);
        setLoadingGeo(false);
        return;
      }
      setCompanyId(company.id);
      await Promise.allSettled([
        loadSeoData(token, company.id),
        loadGeoData(token, company.id),
      ]);
    } catch (err) {
      setSeoError(getErrorMessage(err));
      setGeoError(getErrorMessage(err));
    }
    setLoadingSeo(false);
    setLoadingGeo(false);
  }

  async function loadSeoData(tok: string, cid: number) {
    try {
      const [audit, gaps] = await Promise.allSettled([
        getSeoAudit(tok, cid),
        getSeoGaps(tok, cid),
      ]);
      if (audit.status === "fulfilled") {
        setSeoIssues(audit.value.issues);
      } else {
        setSeoError(getErrorMessage(audit.reason));
      }
      if (gaps.status === "fulfilled") {
        setSeoGaps(gaps.value);
      }
    } catch (err) {
      setSeoError(getErrorMessage(err));
    }
  }

  async function loadGeoData(tok: string, cid: number) {
    try {
      const [gaps, readiness] = await Promise.allSettled([
        getGeoGaps(tok, cid),
        getGeoReadiness(tok, cid),
      ]);
      if (gaps.status === "fulfilled") {
        setGeoGaps(gaps.value);
      } else {
        setGeoError(getErrorMessage(gaps.reason));
      }
      if (readiness.status === "fulfilled") {
        setGeoReadiness(readiness.value);
      }
    } catch (err) {
      setGeoError(getErrorMessage(err));
    }
  }

  async function handleRunAudit(agent: "seo" | "geo") {
    if (!token || !companyId) return;
    setRunningAgent(agent);
    try {
      const runFn = agent === "seo" ? runSeoAudit : runGeoAudit;
      await runFn(token, companyId);
      success(`${agent.toUpperCase()} audit started`, "Results will appear shortly...");
      // Poll for updated data every 3 seconds for up to 60 seconds
      let attempts = 0;
      if (pollRef.current) clearInterval(pollRef.current);
      pollRef.current = setInterval(async () => {
        attempts++;
        if (attempts > 20) {
          if (pollRef.current) clearInterval(pollRef.current);
          setRunningAgent(null);
          return;
        }
        if (agent === "seo") {
          await loadSeoData(token!, companyId);
        } else {
          await loadGeoData(token!, companyId);
        }
      }, 3000);
    } catch (err) {
      error("Failed to start audit", getErrorMessage(err));
      setRunningAgent(null);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader title="SEO / GEO" description="Audit and optimize for search and generative engine visibility." />

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="seo">SEO Audit</TabsTrigger>
          <TabsTrigger value="geo">GEO Visibility</TabsTrigger>
          <TabsTrigger value="gaps">Keyword Gaps</TabsTrigger>
        </TabsList>

        <TabsContent value="seo" className="space-y-4">
          <div className="flex justify-end">
            <Button variant="outline" size="sm" onClick={() => void handleRunAudit("seo")} disabled={runningAgent === "seo"}>
              {runningAgent === "seo" ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5 mr-1" />}
              Run SEO Audit
            </Button>
          </div>
          {loadingSeo ? (
            <Card><CardContent className="p-8 text-center text-sm text-muted-foreground"><Loader2 className="h-5 w-5 animate-spin mx-auto mb-2" />Loading SEO audit...</CardContent></Card>
          ) : seoError ? (
            <Card><CardContent className="p-8 text-center"><p className="text-sm text-destructive mb-3">{seoError}</p><Button variant="outline" size="sm" onClick={() => void loadData()}>Retry</Button></CardContent></Card>
          ) : seoIssues.length === 0 ? (
            <Card><CardContent className="p-8 text-center text-sm text-muted-foreground">No SEO issues found. Run an audit to check for problems.</CardContent></Card>
          ) : (
            seoIssues.map((issue) => (
              <Card key={issue.id}>
                <CardContent className="p-4 flex items-center gap-4">
                  <StatusBadge variant={issue.score > 70 ? "error" : issue.score > 40 ? "warning" : "success"} dot>
                    {issue.score > 70 ? "error" : issue.score > 40 ? "warning" : "success"}
                  </StatusBadge>
                  <div className="flex-1">
                    <div className="text-sm font-medium">{issue.title}</div>
                    <div className="text-xs text-muted-foreground">{issue.body?.slice(0, 120) ?? "No details"}</div>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </TabsContent>

        <TabsContent value="geo" className="space-y-6">
          <div className="flex justify-end">
            <Button variant="outline" size="sm" onClick={() => void handleRunAudit("geo")} disabled={runningAgent === "geo"}>
              {runningAgent === "geo" ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5 mr-1" />}
              Run GEO Audit
            </Button>
          </div>
          {loadingGeo ? (
            <Card><CardContent className="p-8 text-center text-sm text-muted-foreground"><Loader2 className="h-5 w-5 animate-spin mx-auto mb-2" />Loading GEO data...</CardContent></Card>
          ) : geoError ? (
            <Card><CardContent className="p-8 text-center"><p className="text-sm text-destructive mb-3">{geoError}</p><Button variant="outline" size="sm" onClick={() => void loadData()}>Retry</Button></CardContent></Card>
          ) : !geoReadiness && geoGaps.length === 0 ? (
            <Card><CardContent className="p-8 text-center text-sm text-muted-foreground">No GEO data yet. Run an audit to check visibility.</CardContent></Card>
          ) : (
            <>
              {geoReadiness && (
                <Card>
                  <CardHeader><CardTitle className="text-base">GEO Readiness Score</CardTitle></CardHeader>
                  <CardContent className="space-y-3">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-2 rounded-full bg-muted overflow-hidden">
                        <div className="h-full bg-primary rounded-full" style={{ width: `${geoReadiness.readiness_score}%` }} />
                      </div>
                      <span className="text-xs font-medium">{geoReadiness.readiness_score}%</span>
                    </div>
                    <p className="text-xs text-muted-foreground">{geoReadiness.gap_count} visibility gaps detected.</p>
                  </CardContent>
                </Card>
              )}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {geoGaps.map((gap) => (
                  <Card key={gap.id}>
                    <CardHeader><CardTitle className="text-base">{gap.title}</CardTitle></CardHeader>
                    <CardContent className="space-y-3">
                      <p className="text-xs text-muted-foreground">{gap.body?.slice(0, 100) ?? "No details available"}</p>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </>
          )}
        </TabsContent>

        <TabsContent value="gaps" className="space-y-4">
          {loadingSeo ? (
            <Card><CardContent className="p-8 text-center text-sm text-muted-foreground"><Loader2 className="h-5 w-5 animate-spin mx-auto mb-2" />Loading keyword gaps...</CardContent></Card>
          ) : seoGaps.length === 0 ? (
            <Card><CardContent className="p-8 text-center text-sm text-muted-foreground">No keyword gaps found. Run an SEO audit to discover content opportunities.</CardContent></Card>
          ) : (
            seoGaps.map((gap) => (
              <Card key={gap.id}>
                <CardContent className="p-4 flex items-center gap-4">
                  <Search className="h-4 w-4 text-muted-foreground shrink-0" />
                  <div className="flex-1">
                    <div className="text-sm font-medium">{gap.title}</div>
                    <div className="text-xs text-muted-foreground">{gap.body?.slice(0, 100) ?? "Keyword gap"}</div>
                  </div>
                  <Badge variant="secondary" className="text-xs">Score: {gap.score}</Badge>
                </CardContent>
              </Card>
            ))
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
