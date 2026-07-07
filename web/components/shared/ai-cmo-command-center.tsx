"use client";

import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import {
  ArrowRight,
  BarChart3,
  Code2,
  Compass,
  FileText,
  Globe2,
  Lightbulb,
  Megaphone,
  PenLine,
  Search,
  Sparkles,
  Target,
  Users,
  Video,
  Zap,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { StatusBadge } from "@/components/shared/status-badge";
import { cn } from "@/lib/utils";

type AgentStatus = "active" | "ready" | "setup" | "planned";

interface CalendarDraftSignal {
  platform?: string | null;
  status?: string | null;
  scheduled_at?: string | null;
}

interface AgentCard {
  name: string;
  focus: string;
  metric: string;
  status: AgentStatus;
  href: string;
  icon: LucideIcon;
}

interface ActionItem {
  title: string;
  detail: string;
  href: string;
  label: string;
}

interface AiCmoCommandCenterProps {
  projectName?: string | null;
  opportunities: number;
  replyDrafts: number;
  published: number;
  shareOfVoice?: number | null;
  visibilityRuns?: number | null;
  calendarDrafts: CalendarDraftSignal[];
}

function platformValue(draft: CalendarDraftSignal): string {
  return (draft.platform || "").toLowerCase();
}

function statusVariant(status: AgentStatus): "success" | "warning" | "info" | "neutral" {
  if (status === "active") return "success";
  if (status === "ready") return "info";
  if (status === "setup") return "warning";
  return "neutral";
}

function statusLabel(status: AgentStatus): string {
  if (status === "active") return "Active";
  if (status === "ready") return "Ready";
  if (status === "setup") return "Needs setup";
  return "Planned";
}

function buildActions({
  opportunities,
  replyDrafts,
  calendarDrafts,
  shareOfVoice,
}: {
  opportunities: number;
  replyDrafts: number;
  calendarDrafts: CalendarDraftSignal[];
  shareOfVoice?: number | null;
}): ActionItem[] {
  const actions: ActionItem[] = [];
  const approvedCalendar = calendarDrafts.filter((draft) => draft.status === "scheduled").length;

  if (opportunities === 0) {
    actions.push({
      title: "Find live conversations",
      detail: "Add signals and run Social Radar to build the opportunity queue.",
      href: "/app/discovery",
      label: "Open Radar",
    });
  } else if (replyDrafts === 0) {
    actions.push({
      title: "Turn opportunities into replies",
      detail: "Draft replies for the strongest conversations before they go cold.",
      href: "/app/content",
      label: "Draft replies",
    });
  }

  if (calendarDrafts.length === 0) {
    actions.push({
      title: "Create a social content plan",
      detail: "Generate one week of X and LinkedIn posts from the brand context.",
      href: "/app/content?tab=calendar",
      label: "Open Calendar",
    });
  } else if (approvedCalendar < calendarDrafts.length) {
    actions.push({
      title: "Approve scheduled content",
      detail: `${calendarDrafts.length - approvedCalendar} posts are waiting for review.`,
      href: "/app/content?tab=calendar",
      label: "Review posts",
    });
  }

  if (!shareOfVoice) {
    actions.push({
      title: "Run SEO and GEO checks",
      detail: "Find search gaps and AI visibility issues before planning new articles.",
      href: "/app/seo-geo",
      label: "Run audit",
    });
  }

  actions.push({
    title: "Track competitor angles",
    detail: "Use competitor complaints and content gaps to shape the next campaign.",
    href: "/app/competitors",
    label: "Open competitors",
  });

  return actions.slice(0, 4);
}

export function AiCmoCommandCenter({
  projectName,
  opportunities,
  replyDrafts,
  published,
  shareOfVoice,
  visibilityRuns,
  calendarDrafts,
}: AiCmoCommandCenterProps) {
  const xDrafts = calendarDrafts.filter((draft) => {
    const platform = platformValue(draft);
    return platform === "x" || platform === "twitter";
  }).length;
  const linkedinDrafts = calendarDrafts.filter((draft) => platformValue(draft) === "linkedin").length;
  const scheduledDrafts = calendarDrafts.filter((draft) => draft.status === "scheduled").length;
  const readinessSignals = [
    opportunities > 0,
    replyDrafts > 0,
    calendarDrafts.length > 0,
    Boolean(shareOfVoice && shareOfVoice > 0),
    published > 0,
  ];
  const readinessScore = Math.round((readinessSignals.filter(Boolean).length / readinessSignals.length) * 100);

  const agents: AgentCard[] = [
    {
      name: "Reddit Agent",
      focus: "Find threads and draft reply ideas.",
      metric: `${opportunities} opportunities`,
      status: opportunities > 0 ? "active" : "setup",
      href: "/app/discovery",
      icon: Search,
    },
    {
      name: "Reply Agent",
      focus: "Write helpful responses for approved leads.",
      metric: `${replyDrafts} drafts`,
      status: replyDrafts > 0 ? "active" : opportunities > 0 ? "ready" : "setup",
      href: "/app/content",
      icon: PenLine,
    },
    {
      name: "X Agent",
      focus: "Draft short posts and campaign threads.",
      metric: `${xDrafts} posts`,
      status: xDrafts > 0 ? "active" : "ready",
      href: "/app/content?tab=calendar",
      icon: Megaphone,
    },
    {
      name: "LinkedIn Agent",
      focus: "Plan professional posts from brand context.",
      metric: `${linkedinDrafts} posts`,
      status: linkedinDrafts > 0 ? "active" : "ready",
      href: "/app/content?tab=calendar",
      icon: FileText,
    },
    {
      name: "SEO Agent",
      focus: "Find keyword and page opportunities.",
      metric: shareOfVoice ? `${shareOfVoice}% visibility` : "Audit needed",
      status: shareOfVoice ? "active" : "setup",
      href: "/app/seo-geo",
      icon: BarChart3,
    },
    {
      name: "GEO Agent",
      focus: "Improve AI citation and answer visibility.",
      metric: `${visibilityRuns ?? 0} runs`,
      status: visibilityRuns ? "active" : "setup",
      href: "/app/visibility",
      icon: Globe2,
    },
    {
      name: "Writer Agent",
      focus: "Draft articles, briefs, and long-form copy.",
      metric: "Articles and briefs",
      status: "ready",
      href: "/app/content-studio",
      icon: Sparkles,
    },
    {
      name: "Competitor Agent",
      focus: "Turn competitor mentions into angles.",
      metric: "Positioning gaps",
      status: "ready",
      href: "/app/competitors",
      icon: Target,
    },
    {
      name: "UGC Agent",
      focus: "Create creator briefs for social content.",
      metric: "Brief exports",
      status: "ready",
      href: "/app/content-studio",
      icon: Video,
    },
    {
      name: "Influencer Agent",
      focus: "Prepare creator outreach workflows.",
      metric: "Connector pending",
      status: "planned",
      href: "/app/sources",
      icon: Users,
    },
    {
      name: "Technical SEO Agent",
      focus: "Flag site fixes that affect growth.",
      metric: "Audit ready",
      status: "ready",
      href: "/app/seo-geo",
      icon: Code2,
    },
    {
      name: "Hacker News Agent",
      focus: "Find timely discussion moments.",
      metric: "Radar source",
      status: "ready",
      href: "/app/discovery",
      icon: Compass,
    },
  ];

  const activeAgents = agents.filter((agent) => agent.status === "active").length;
  const nextActions = buildActions({ opportunities, replyDrafts, calendarDrafts, shareOfVoice });

  return (
    <section className="space-y-4">
      <Card className="overflow-hidden">
        <CardContent className="grid gap-5 py-5 lg:grid-cols-[1.15fr_0.85fr] lg:items-center">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="secondary">AI CMO</Badge>
              <StatusBadge variant={readinessScore >= 60 ? "success" : "warning"}>
                {readinessScore}% ready
              </StatusBadge>
            </div>
            <h2 className="mt-3 text-2xl font-semibold tracking-tight">
              Marketing command center
            </h2>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted-foreground">
              {projectName ? `${projectName} now has` : "Your workspace has"} agent workflows for social discovery,
              replies, content planning, SEO/GEO, competitors, UGC, and technical growth work.
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <Link href="/app/auto-pipeline">
                <Button size="sm">
                  <Zap className="h-4 w-4" />
                  Run Auto Pipeline
                </Button>
              </Link>
              <Link href="/app/content?tab=calendar">
                <Button variant="outline" size="sm">
                  Create Content Plan
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
            </div>
          </div>
          <div className="grid gap-2 sm:grid-cols-3 lg:grid-cols-1">
            <div className="rounded-lg border bg-background p-3">
              <p className="text-xs text-muted-foreground">Active agents</p>
              <p className="mt-1 text-xl font-semibold">{activeAgents}/{agents.length}</p>
            </div>
            <div className="rounded-lg border bg-background p-3">
              <p className="text-xs text-muted-foreground">Scheduled posts</p>
              <p className="mt-1 text-xl font-semibold">{scheduledDrafts}/{calendarDrafts.length}</p>
            </div>
            <div className="rounded-lg border bg-background p-3">
              <p className="text-xs text-muted-foreground">Published work</p>
              <p className="mt-1 text-xl font-semibold">{published}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 xl:grid-cols-[1.35fr_0.65fr]">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {agents.map((agent) => {
            const Icon = agent.icon;
            return (
              <Link key={agent.name} href={agent.href} className="group rounded-lg focus:outline-none focus:ring-2 focus:ring-ring">
                <Card className="h-full transition-colors group-hover:bg-accent/40">
                  <CardContent className="flex h-full flex-col gap-3 py-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                        <Icon className="h-4 w-4" />
                      </div>
                      <StatusBadge variant={statusVariant(agent.status)}>
                        {statusLabel(agent.status)}
                      </StatusBadge>
                    </div>
                    <div>
                      <p className="text-sm font-semibold">{agent.name}</p>
                      <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-muted-foreground">{agent.focus}</p>
                    </div>
                    <div className="mt-auto flex items-center justify-between gap-2">
                      <span className="truncate text-xs font-medium text-muted-foreground">{agent.metric}</span>
                      <ArrowRight className="h-3.5 w-3.5 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
                    </div>
                  </CardContent>
                </Card>
              </Link>
            );
          })}
        </div>

        <div className="space-y-4">
          <Card>
            <CardContent className="py-4">
              <div className="flex items-center gap-2">
                <Lightbulb className="h-4 w-4 text-primary" />
                <p className="text-sm font-semibold">Next best actions</p>
              </div>
              <div className="mt-3 space-y-3">
                {nextActions.map((action) => (
                  <div key={action.title} className="rounded-lg border bg-background p-3">
                    <p className="text-sm font-medium">{action.title}</p>
                    <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{action.detail}</p>
                    <Link href={action.href}>
                      <Button variant="outline" size="sm" className="mt-3">
                        {action.label}
                        <ArrowRight className="h-3.5 w-3.5" />
                      </Button>
                    </Link>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="py-4">
              <div className="flex items-center gap-2">
                <Zap className="h-4 w-4 text-primary" />
                <p className="text-sm font-semibold">Connector readiness</p>
              </div>
              <div className="mt-3 space-y-2">
                {[
                  ["Website sources", "Ready"],
                  ["Google Search Console", "Setup later"],
                  ["Google Analytics", "Setup later"],
                  ["X / Twitter posting", "Manual approval"],
                  ["LinkedIn posting", "Manual approval"],
                ].map(([name, state]) => (
                  <div key={name} className="flex items-center justify-between gap-3 rounded-lg border bg-background px-3 py-2">
                    <span className="truncate text-xs font-medium">{name}</span>
                    <Badge
                      variant="outline"
                      className={cn(state === "Ready" && "border-success/30 text-success")}
                    >
                      {state}
                    </Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </section>
  );
}
