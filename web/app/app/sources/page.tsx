"use client";
import { useState } from "react";
import { Loader2 } from "lucide-react";

import { useAuth } from "@/components/auth/auth-provider";
import { useToast } from "@/stores/toast";
import { useAsyncData } from "@/hooks/use-async-data";
import { Card } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { getCitations, getSourceDomains, getSourceGaps, CitationItem, apiRequest, type BrandProfile } from "@/lib/api";
import { useSelectedProjectId } from "@/hooks/use-selected-project";
import { PageHeader } from "@/components/shared/page-header";
import { CompanyNav } from "@/components/company/company-nav";
import { KPIGrid, type KPICardProps } from "@/components/shared/kpi-card";
import { DataTable, type ColumnDef } from "@/components/shared/data-table";

interface SourceDomain {
  domain: string;
  total_citations: number;
}

interface SourceGap {
  id: number;
  competitor_name: string;
  domain: string;
  citation_count: number;
}

function normalizeHostname(value: string | null | undefined) {
  if (!value) {
    return null;
  }

  try {
    const parsed = new URL(value.includes("://") ? value : `https://${value}`);
    return parsed.hostname.toLowerCase().replace(/^www\./, "");
  } catch {
    return value.toLowerCase().replace(/^www\./, "").replace(/\/.*$/, "");
  }
}

function isOwnedDomain(domain: string, ownedWebsiteHost: string | null) {
  const normalizedDomain = normalizeHostname(domain);
  if (!normalizedDomain || !ownedWebsiteHost) {
    return false;
  }

  return (
    normalizedDomain === ownedWebsiteHost
    || normalizedDomain.endsWith(`.${ownedWebsiteHost}`)
    || ownedWebsiteHost.endsWith(`.${normalizedDomain}`)
  );
}

interface SourcesData {
  domains: SourceDomain[];
  citations: CitationItem[];
  gaps: SourceGap[];
  citationTotal: number;
  ownedWebsiteHost: string | null;
}

export default function SourcesPage() {
  const { token } = useAuth();
  const { error } = useToast();
  const selectedProjectId = useSelectedProjectId();
  const [activeTab, setActiveTab] = useState("all");

  const { data, loading } = useAsyncData<SourcesData>(
    async () => {
      const [domRes, citRes, gapRes, brandRes] = await Promise.allSettled([
        getSourceDomains(token!, selectedProjectId),
        getCitations(token!, undefined, 100, selectedProjectId),
        getSourceGaps(token!, selectedProjectId),
        selectedProjectId ? apiRequest<BrandProfile>(`/v1/brand/${selectedProjectId}`, {}, token) : Promise.resolve(null),
      ]);

      return {
        domains: domRes.status === "fulfilled" ? (domRes.value.items || []) : [],
        citations: citRes.status === "fulfilled" ? (citRes.value.items || []) : [],
        citationTotal: citRes.status === "fulfilled" ? (citRes.value.total || 0) : 0,
        gaps: gapRes.status === "fulfilled" ? (gapRes.value.items || []) : [],
        ownedWebsiteHost: brandRes.status === "fulfilled" ? normalizeHostname(brandRes.value?.website_url) : null,
      };
    },
    [token, selectedProjectId],
    {
      enabled: !!token,
      onError: (message) => {
        if (!message.includes("No active project") && !message.includes("Not Found") && !message.includes("404")) {
          error("Failed to load source data", message);
        }
      },
    },
  );

  const domains = data?.domains ?? [];
  const citations = data?.citations ?? [];
  const gaps = data?.gaps ?? [];
  const citationTotal = data?.citationTotal ?? 0;
  const ownedWebsiteHost = data?.ownedWebsiteHost ?? null;
  const uniqueDomains = domains.length;

  const ownedDomainItems = domains.filter((domainItem) => isOwnedDomain(domainItem.domain, ownedWebsiteHost));
  const ownedSources = ownedDomainItems.length;

  // Column definitions for All Citations DataTable
  const citationColumns: ColumnDef<Record<string, unknown>>[] = [
    {
      key: "domain",
      header: "Domain",
      render: (row) => <span className="font-semibold">{String(row.domain ?? "")}</span>,
    },
    {
      key: "url",
      header: "URL",
      className: "max-w-[350px]",
      render: (row) => (
        <a href={String(row.url ?? "#")} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline truncate block">
          {String(row.url ?? "")}
        </a>
      ),
    },
    {
      key: "platform",
      header: "Platform",
      render: () => <Badge variant="secondary">AI Response</Badge>,
    },
    {
      key: "content_type",
      header: "Type",
      render: (row) => <Badge variant="secondary">{String(row.content_type || "Page")}</Badge>,
    },
    {
      key: "first_seen_at",
      header: "First Seen",
      render: (row) => {
        const val = row.first_seen_at as string | null;
        return (
          <span className="text-xs text-muted-foreground">
            {val ? new Date(val).toLocaleDateString() : "—"}
          </span>
        );
      },
    },
  ];

  // Column definitions for Our Sources DataTable
  const ownedColumns: ColumnDef<Record<string, unknown>>[] = [
    {
      key: "domain",
      header: "Domain",
      render: (row) => <span className="font-semibold">{String(row.domain ?? "")}</span>,
    },
    {
      key: "total_citations",
      header: "Citations",
    },
    {
      key: "share",
      header: "Share",
      render: (row) => {
        const totalCitations = Number(row.total_citations ?? 0);
        const share = citationTotal > 0 ? Math.round((totalCitations / citationTotal) * 100) : 0;
        return (
          <div className="flex items-center gap-2">
            <div className="w-16 h-1.5 bg-muted rounded-full overflow-hidden">
              <div
                className="h-full bg-primary rounded-full"
                style={{ width: `${share}%` }}
              />
            </div>
            <span className="text-xs">{share}%</span>
          </div>
        );
      },
    },
  ];

  if (loading) {
    return (
      <div className="flex flex-col gap-8">
        <CompanyNav />
      <PageHeader title="Source Intelligence" description="Understand which domains and URLs AI models cite when responding to prompts about your category." />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-5">
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

  // KPI cards
  const kpiCards: KPICardProps[] = [
    { label: "Unique Domains", value: uniqueDomains },
    { label: "Total Citations", value: citationTotal },
    { label: "Sources We Own", value: ownedSources },
    { label: "Source Gaps", value: gaps.length },
  ];

  // Cast data for DataTable (requires Record<string, unknown>)
  const citationRows = citations.slice(0, 50) as unknown as Record<string, unknown>[];
  const citationColumnDefs = citationColumns as unknown as ColumnDef<Record<string, unknown>>[];
  const ownedRows = ownedDomainItems as unknown as Record<string, unknown>[];
  const ownedColumnDefs = ownedColumns as unknown as ColumnDef<Record<string, unknown>>[];

  return (
    <div className="flex flex-col gap-8">
      <CompanyNav />
      <PageHeader title="Source Intelligence" description="Understand which domains and URLs AI models cite when responding to prompts about your category." />

      {/* KPI Row - 4 cards */}
      <KPIGrid cards={kpiCards} columns={4} className="grid-cols-2 md:grid-cols-4" />

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="all">
            All Citations
            <Badge variant="secondary" className="ml-1.5">
              {citationTotal}
              {citationTotal > 50 && " (50 shown)"}
            </Badge>
          </TabsTrigger>
          <TabsTrigger value="owned">
            Our Sources
            <Badge variant="secondary" className="ml-1.5">{ownedSources}</Badge>
          </TabsTrigger>
          <TabsTrigger value="gaps">
            Source Gaps
            <Badge variant="secondary" className="ml-1.5">{gaps.length}</Badge>
          </TabsTrigger>
        </TabsList>

        {/* Tab 1: All Citations */}
        <TabsContent value="all" className="mt-5">
          <DataTable
            columns={citationColumnDefs}
            data={citationRows}
            emptyState={{
              title: "No citations found yet",
              description: "Citations are automatically extracted from AI model responses when you run prompt sets on the AI Visibility page.",
            }}
          />
        </TabsContent>

        {/* Tab 2: Our Sources */}
        <TabsContent value="owned" className="mt-5">
          <DataTable
            columns={ownedColumnDefs}
            data={ownedRows}
            emptyState={{
              title: "No owned sources yet",
              description: "Sources you own are identified from your brand profile. Set up your brand to track which of the cited domains are yours.",
            }}
          />
        </TabsContent>

        {/* Tab 3: Source Gaps */}
        <TabsContent value="gaps" className="mt-5">
          {gaps.length === 0 ? (
            <div className="flex flex-col items-center justify-center p-8 text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted mb-4">
                <Loader2 className="h-8 w-8 text-muted-foreground/50" />
              </div>
              <h3 className="text-lg font-semibold mb-1">No source gaps detected</h3>
              <p className="text-sm text-muted-foreground max-w-md">
                Source gaps show where competitors are cited by AI but your brand is not. Run visibility tracking to discover gaps.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {gaps.map(g => (
                <div
                  key={g.id}
                  className="rounded-xl border bg-card p-5 grid grid-cols-[1fr_auto] gap-3 items-center"
                >
                  <div>
                    <div className="text-sm font-semibold">
                      <span className="text-primary">{g.competitor_name}</span> is cited on{" "}
                      <span className="font-bold">{g.domain}</span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      Your brand is not cited on this domain. Consider creating content there to close the gap.
                    </p>
                  </div>
                  <div className="text-right">
                    <div className="text-lg font-bold text-primary">{g.citation_count}</div>
                    <div className="text-xs text-muted-foreground">citation{g.citation_count !== 1 ? "s" : ""}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
