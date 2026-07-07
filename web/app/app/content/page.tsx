"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  Loader2,
  MessageSquare,
  FileEdit,
  CheckCircle,
  MoreHorizontal,
  Copy,
  Pencil,
  ExternalLink,
  ChevronDown,
  ArrowRight,
  LayoutTemplate,
  Link2,
  Megaphone,
  AlertTriangle,
  RefreshCw,
  ShieldCheck,
  ClipboardList,
  CalendarDays,
  Clock3,
  Sparkles,
  Download,
  BarChart3,
  Filter,
  ListChecks,
  Target,
  GripVertical,
  PenLine,
  UploadCloud,
} from "lucide-react";

import { useAuth } from "@/components/auth/auth-provider";
import { useToast } from "@/stores/toast";
import { getErrorMessage, isApiError } from "@/types/errors";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";
import { type PostDraft, apiRequest } from "@/lib/api";
import { withProjectId } from "@/lib/project";
import { useSelectedProjectId } from "@/hooks/use-selected-project";
import { type ReplyStylePreset, useDraftOps } from "@/hooks/use-draft-ops";
import { PlatformIcon } from "@/components/shared/platform-icon";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { EmptyState } from "@/components/shared/empty-state";
import { SheetPanel } from "@/components/shared/sheet-panel";
import { ScoreBadge } from "@/components/shared/score-badge";
import { sourceLabel } from "@/lib/opportunity";
import { redditUrl, platformUrl, copyText } from "@/lib/reddit";
import { setStoredProjectId } from "@/lib/project";
import { postToReddit as apiPostToReddit } from "@/lib/api/reddit";
import { createContentPlan, schedulePostDraft, unschedulePostDraft, updatePostDraft } from "@/lib/api/content";
import { createTrackedLink, shortLinkUrl } from "@/lib/api/links";
import { createAmplifyDraft, type AmplifyTarget } from "@/lib/api/amplify";
import { uploadAnalysisFile } from "@/lib/api/files";
import { rememberAmplifyDraft } from "@/lib/amplify-store";
import { assessReplyQuality, qualityBadgeClass } from "@/lib/reply-quality";

interface ReplyDraftRow {
  id: number;
  opportunity_id: number;
  content: string;
  rationale: string;
  version: number;
  created_at: string;
  opportunity_title?: string;
  opportunity_subreddit?: string;
  permalink?: string;
  body_excerpt?: string;
  score?: number;
  platform?: string;
}

interface ProjectContext {
  id: number;
  name: string;
}

interface RedditAccount {
  id: number;
  username: string;
}

interface PublishedPost {
  id: number;
  content: string;
  subreddit: string;
  post_date: string;
  status: string;
  permalink?: string;
  upvotes?: number;
  comments?: number;
}

function parsePositiveInt(value: string | null): number | null {
  if (!value) {
    return null;
  }
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

function replySourceLabel(draft: ReplyDraftRow): string {
  return sourceLabel({
    platform: draft.platform,
    subreddit_name: draft.platform === "reddit" || !draft.platform ? draft.opportunity_subreddit : undefined,
    source_name: draft.opportunity_subreddit,
  });
}

const REGENERATE_OPTIONS: Array<{ value: ReplyStylePreset; label: string }> = [
  { value: "shorter", label: "Make shorter" },
  { value: "more_helpful", label: "Make more helpful" },
  { value: "more_professional", label: "More professional" },
  { value: "less_promotional", label: "Less promotional" },
];

type PlannerPlatform = "x" | "linkedin";
type PlannerWindow = 7 | 30;
type PlannerCampaign = "brand_awareness" | "lead_generation" | "product_launch" | "competitor_switch" | "education";
type PlannerVoice = "professional" | "friendly" | "premium" | "witty";
type PlannerTemplate = "product_tip" | "comparison" | "founder_story" | "case_study" | "offer_post";
type CalendarPlatformFilter = "all" | PlannerPlatform;
type CalendarStatusFilter = "all" | "draft" | "scheduled" | "needs_edit" | "rejected";
type PostRewritePreset = "shorter" | "professional" | "less_salesy" | "stronger_hook";
type CalendarLayout = "board" | "list";

const PLATFORM_LABELS: Record<PlannerPlatform, string> = {
  x: "X / Twitter",
  linkedin: "LinkedIn",
};

const CAMPAIGN_OPTIONS: Array<{ value: PlannerCampaign; label: string }> = [
  { value: "brand_awareness", label: "Brand awareness" },
  { value: "lead_generation", label: "Lead generation" },
  { value: "product_launch", label: "Product launch" },
  { value: "competitor_switch", label: "Competitor switch" },
  { value: "education", label: "Education" },
];

const VOICE_OPTIONS: Array<{ value: PlannerVoice; label: string }> = [
  { value: "professional", label: "Professional" },
  { value: "friendly", label: "Friendly" },
  { value: "premium", label: "Premium" },
  { value: "witty", label: "Witty" },
];

const TEMPLATE_OPTIONS: Array<{ value: PlannerTemplate; label: string }> = [
  { value: "product_tip", label: "Product tip" },
  { value: "comparison", label: "Comparison" },
  { value: "founder_story", label: "Founder story" },
  { value: "case_study", label: "Case study" },
  { value: "offer_post", label: "Offer post" },
];

const CALENDAR_STATUS_LABELS: Record<CalendarStatusFilter, string> = {
  all: "All status",
  draft: "Suggested",
  scheduled: "Approved",
  needs_edit: "Needs edit",
  rejected: "Rejected",
};

const MEDIA_PLAN_MARKER = "\n\n[Media plan]\n";

function draftPlatform(draft: PostDraft): string {
  return (draft.platform || "reddit").toLowerCase();
}

function draftStatus(draft: PostDraft): string {
  return (draft.status || "draft").toLowerCase();
}

function isCalendarDraft(draft: PostDraft): boolean {
  const platform = draftPlatform(draft);
  return platform === "x" || platform === "twitter" || platform === "linkedin" || Boolean(draft.scheduled_at);
}

function dateKey(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function formatDayLabel(date: Date): string {
  return date.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" });
}

function formatTime(value?: string | null): string {
  if (!value) return "Suggested slot";
  return new Date(value).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

function defaultScheduleSlot(): string {
  const date = new Date();
  date.setDate(date.getDate() + 1);
  date.setHours(10, 0, 0, 0);
  return date.toISOString();
}

function csvValue(value: string | number | null | undefined): string {
  return `"${String(value ?? "").replace(/"/g, '""')}"`;
}

function safeFilePart(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "content";
}

function calendarStatusLabel(status: string): string {
  if (status === "scheduled") return "Scheduled";
  if (status === "needs_edit") return "Needs edit";
  if (status === "rejected") return "Rejected";
  return "Suggested";
}

function calendarStatusVariant(status: string): "success" | "warning" | "error" | "neutral" {
  if (status === "scheduled") return "success";
  if (status === "needs_edit") return "warning";
  if (status === "rejected") return "error";
  return "warning";
}

function trimToLength(text: string, maxLength: number): string {
  const compact = text.replace(/\s+/g, " ").trim();
  if (compact.length <= maxLength) {
    return compact;
  }
  return `${compact.slice(0, Math.max(0, maxLength - 3)).trim()}...`;
}

function rewritePostCopy(
  title: string,
  body: string,
  preset: PostRewritePreset,
  platform: string,
): { title: string; body: string } {
  const maxLength = platform === "x" || platform === "twitter" ? 260 : 900;
  if (preset === "shorter") {
    return {
      title: trimToLength(title, 90),
      body: trimToLength(body, maxLength),
    };
  }

  if (preset === "less_salesy") {
    const cleaned = body
      .replace(/\b(game[- ]?changer|revolutionary|best in class|must[- ]?have|limited time)\b/gi, "useful")
      .replace(/\b(buy now|sign up today|don't miss out)\b/gi, "take a closer look")
      .replace(/!{2,}/g, ".");
    return {
      title: title.replace(/\bultimate\b/gi, "practical"),
      body: trimToLength(cleaned, maxLength),
    };
  }

  if (preset === "stronger_hook") {
    const hook = platform === "linkedin"
      ? "A small detail most teams miss:"
      : "Worth checking before you decide:";
    return {
      title: title.startsWith("A small detail") || title.startsWith("Worth checking") ? title : `${hook} ${title}`,
      body: trimToLength(`${hook}\n\n${body}`, maxLength),
    };
  }

  const professionalBody = body
    .replace(/\bkinda\b/gi, "somewhat")
    .replace(/\bgonna\b/gi, "going to")
    .replace(/\bwanna\b/gi, "want to")
    .replace(/\bguys\b/gi, "teams");
  return {
    title: trimToLength(title, 100),
    body: trimToLength(professionalBody, maxLength),
  };
}

function splitPostRationale(value?: string | null): { note: string; media: string } {
  const raw = value || "";
  const markerIndex = raw.indexOf(MEDIA_PLAN_MARKER);
  if (markerIndex === -1) {
    return { note: raw, media: "" };
  }
  return {
    note: raw.slice(0, markerIndex).trim(),
    media: raw.slice(markerIndex + MEDIA_PLAN_MARKER.length).trim(),
  };
}

function combinePostRationale(note: string, media: string): string | null {
  const cleanNote = note.trim();
  const cleanMedia = media.trim();
  if (!cleanNote && !cleanMedia) {
    return null;
  }
  return cleanMedia ? `${cleanNote || "Review note"}${MEDIA_PLAN_MARKER}${cleanMedia}` : cleanNote;
}

export default function ContentPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { token } = useAuth();
  const { success, error } = useToast();
  const selectedProjectId = useSelectedProjectId();
  const {
    savingReply,
    savingPost,
    generateReplyDraft,
    copyToClipboard,
    copyAndOpen,
    markAsPosted: markOpportunityPosted,
    saveReplyDraft: persistReplyDraft,
    savePostDraft: persistPostDraft,
  } = useDraftOps(token);
  const requestedProjectId = parsePositiveInt(searchParams.get("project_id"));
  const requestedOpportunityId = parsePositiveInt(searchParams.get("opportunity"));
  const requestedTab = searchParams.get("tab");
  const pendingOpportunityIdRef = useRef<number | null>(null);
  const handledOpportunityIdRef = useRef<number | null>(null);
  const loadDraftsRequestRef = useRef(0);
  const postDraftMutationRef = useRef(0);

  const [activeTab, setActiveTab] = useState("replies");
  const [drafts, setDrafts] = useState<ReplyDraftRow[]>([]);
  const [postedDrafts, setPostedDrafts] = useState<ReplyDraftRow[]>([]);
  const [postDrafts, setPostDrafts] = useState<PostDraft[]>([]);
  const [project, setProject] = useState<ProjectContext | null>(null);
  const [loading, setLoading] = useState(true);
  const [generatingPost, setGeneratingPost] = useState(false);
  const [plannerPlatform, setPlannerPlatform] = useState<PlannerPlatform>("x");
  const [plannerWindow, setPlannerWindow] = useState<PlannerWindow>(7);
  const [plannerCampaign, setPlannerCampaign] = useState<PlannerCampaign>("brand_awareness");
  const [plannerVoice, setPlannerVoice] = useState<PlannerVoice>("professional");
  const [plannerTemplate, setPlannerTemplate] = useState<PlannerTemplate>("product_tip");
  const [plannerBrief, setPlannerBrief] = useState("");
  const [calendarPlatformFilter, setCalendarPlatformFilter] = useState<CalendarPlatformFilter>("all");
  const [calendarStatusFilter, setCalendarStatusFilter] = useState<CalendarStatusFilter>("all");
  const [calendarLayout, setCalendarLayout] = useState<CalendarLayout>("board");
  const [generatingPlan, setGeneratingPlan] = useState(false);
  const [approvingCalendar, setApprovingCalendar] = useState(false);
  const [schedulingDraftId, setSchedulingDraftId] = useState<number | null>(null);
  const [draggingDraftId, setDraggingDraftId] = useState<number | null>(null);

  const [selectedReply, setSelectedReply] = useState<ReplyDraftRow | null>(null);
  const [replyContent, setReplyContent] = useState("");
  const [regeneratingPreset, setRegeneratingPreset] = useState<ReplyStylePreset | null>(null);

  const [selectedPost, setSelectedPost] = useState<PostDraft | null>(null);
  const [postTitle, setPostTitle] = useState("");
  const [postBody, setPostBody] = useState("");
  const [postReviewNote, setPostReviewNote] = useState("");
  const [postMediaBrief, setPostMediaBrief] = useState("");
  const [uploadingCalendarAsset, setUploadingCalendarAsset] = useState(false);

  const [publishedPosts, setPublishedPosts] = useState<PublishedPost[]>([]);
  const [redditAccounts, setRedditAccounts] = useState<RedditAccount[]>([]);
  const [postingReddit, setPostingReddit] = useState(false);
  const [showPostConfirm, setShowPostConfirm] = useState(false);
  const [postingDraftId, setPostingDraftId] = useState<number | null>(null);
  const [postSubreddit, setPostSubreddit] = useState("");
  const [safetyBlock, setSafetyBlock] = useState<string | null>(null);

  // Tracked-link creation (reply ROI attribution)
  const [linkDraft, setLinkDraft] = useState<ReplyDraftRow | null>(null);
  const [linkDestination, setLinkDestination] = useState("");
  const [creatingLink, setCreatingLink] = useState(false);

  // Amplify (X thread / LinkedIn post from a reply draft)
  const [amplifyingId, setAmplifyingId] = useState<number | null>(null);

  const [threadOpen, setThreadOpen] = useState(true);
  const [rationaleOpen, setRationaleOpen] = useState(false);

  useEffect(() => {
    if (requestedTab && ["replies", "posts", "calendar", "published", "templates"].includes(requestedTab)) {
      setActiveTab(requestedTab);
    }
  }, [requestedTab]);

  useEffect(() => {
    if (requestedProjectId && requestedProjectId !== selectedProjectId) {
      setStoredProjectId(requestedProjectId);
    }
  }, [requestedProjectId, selectedProjectId]);

  useEffect(() => {
    if (!token) {
      return;
    }
    if (requestedProjectId && requestedProjectId !== selectedProjectId) {
      return;
    }
    void loadDrafts();
  }, [token, requestedProjectId, selectedProjectId]);

  async function loadDrafts() {
    const requestId = ++loadDraftsRequestRef.current;
    const postDraftMutationVersion = postDraftMutationRef.current;
    const projectId = selectedProjectId;
    setLoading(true);
    try {
      const [dashboardRes, draftingRes, postedRes, postsRes, accountsRes, publishedRes] = await Promise.allSettled([
        apiRequest<any>(withProjectId("/v1/dashboard", projectId), {}, token),
        apiRequest<ReplyDraftRow[]>(withProjectId("/v1/drafts/replies?status=drafting", projectId), {}, token),
        apiRequest<ReplyDraftRow[]>(withProjectId("/v1/drafts/replies?status=posted", projectId), {}, token),
        apiRequest<PostDraft[]>(withProjectId("/v1/drafts/posts", projectId), {}, token),
        apiRequest<{ items: RedditAccount[] }>(`/v1/reddit/accounts`, {}, token),
        apiRequest<{ items: PublishedPost[] }>(withProjectId("/v1/reddit/published", projectId), {}, token),
      ]);

      if (loadDraftsRequestRef.current !== requestId) {
        return;
      }

      if (dashboardRes.status === "fulfilled") {
        const focusProject =
          dashboardRes.value.projects?.find((item: ProjectContext) => item.id === projectId) ||
          dashboardRes.value.projects?.[0] ||
          null;
        setProject(focusProject ? { id: focusProject.id, name: focusProject.name } : null);
      }
      setDrafts(draftingRes.status === "fulfilled" ? draftingRes.value : []);
      setPostedDrafts(postedRes.status === "fulfilled" ? postedRes.value : []);
      if (postDraftMutationRef.current === postDraftMutationVersion) {
        setPostDrafts(postsRes.status === "fulfilled" ? postsRes.value : []);
      }
      setRedditAccounts(accountsRes.status === "fulfilled" ? (accountsRes.value.items ?? []) : []);
      setPublishedPosts(publishedRes.status === "fulfilled" ? (publishedRes.value.items ?? []) : []);
    } catch (err) {
      setDrafts([]);
      setPostedDrafts([]);
      setPostDrafts([]);
      setRedditAccounts([]);
      setPublishedPosts([]);
    }
    if (loadDraftsRequestRef.current === requestId) {
      setLoading(false);
    }
  }

  async function postToReddit(draftId: number, overrideSafety = false) {
    if (!project || !token) return;
    const draft = postDrafts.find((d) => d.id === draftId);
    const account = redditAccounts[0];
    if (!draft || !account) return;
    const subreddit = postSubreddit.trim().replace(/^r\//i, "");
    if (subreddit.length < 2) {
      error("Subreddit required", "Enter the subreddit to post into (e.g. r/startups).");
      return;
    }
    setPostingReddit(true);
    try {
      await apiPostToReddit(token, {
        reddit_account_id: account.id,
        project_id: project.id,
        type: "post",
        subreddit,
        title: draft.title,
        content: draft.body,
        ...(overrideSafety ? { override_safety: true } : {}),
      });

      success("Posted to Reddit", "Your post has been published");
      setSafetyBlock(null);
      setShowPostConfirm(false);
      await loadDrafts();
    } catch (err: unknown) {
      // 422 = account-safety guard (warm-up daily cap). Surface the detail and
      // let the user explicitly retry with override_safety.
      if (isApiError(err) && err.status === 422) {
        setSafetyBlock(getErrorMessage(err));
      } else {
        error("Could not post to Reddit", getErrorMessage(err));
      }
    }
    setPostingReddit(false);
  }

  function closePostConfirm() {
    setShowPostConfirm(false);
    setSafetyBlock(null);
  }

  async function handleCreateTrackedLink() {
    if (!token || !project || !linkDraft) return;
    const destination = linkDestination.trim();
    if (!/^https?:\/\//i.test(destination)) {
      error("Invalid URL", "Destination must start with http:// or https://");
      return;
    }
    setCreatingLink(true);
    try {
      const link = await createTrackedLink(token, {
        project_id: project.id,
        destination_url: destination,
        reply_draft_id: linkDraft.id,
        opportunity_id: linkDraft.opportunity_id ?? null,
      });
      const url = shortLinkUrl(link);
      let copied = true;
      try {
        await copyText(url);
      } catch {
        copied = false;
      }
      success(
        copied ? "Tracked link created and copied" : "Tracked link created",
        `${url} — using it is opt-in: Redditors distrust obvious trackers, so only paste it where a link genuinely helps.`
      );
      setLinkDraft(null);
      setLinkDestination("");
    } catch (err: unknown) {
      error("Could not create tracked link", getErrorMessage(err));
    }
    setCreatingLink(false);
  }

  async function handleAmplify(draft: ReplyDraftRow, target: AmplifyTarget) {
    if (!token) return;
    setAmplifyingId(draft.id);
    try {
      const created = await createAmplifyDraft(token, { reply_draft_id: draft.id, target });
      rememberAmplifyDraft(created);
      success(
        target === "x" ? "X thread drafted" : "LinkedIn post drafted",
        "Opening the amplify editor..."
      );
      router.push(`/app/content-studio?amplifyDraft=${created.id}`);
    } catch (err: unknown) {
      error("Could not amplify draft", getErrorMessage(err));
    } finally {
      setAmplifyingId(null);
    }
  }

  async function regenerateReply(stylePreset: ReplyStylePreset) {
    if (!selectedReply || !project) {
      return;
    }
    setRegeneratingPreset(stylePreset);
    try {
      const draft = await generateReplyDraft(selectedReply.opportunity_id, project.id, {
        platform: selectedReply.platform || "reddit",
        stylePreset,
      });
      if (!draft) {
        return;
      }
      const nextDraft: ReplyDraftRow = {
        ...selectedReply,
        id: draft.id,
        content: draft.content,
        rationale: draft.rationale || "",
        version: draft.version,
        created_at: draft.created_at,
      };
      setDrafts((rows) => [
        nextDraft,
        ...rows.filter((row) => row.opportunity_id !== selectedReply.opportunity_id),
      ]);
      setSelectedReply(nextDraft);
      setReplyContent(nextDraft.content);
    } finally {
      setRegeneratingPreset(null);
    }
  }

  async function copyWeeklyReport() {
    const projectName = project?.name || "Current project";
    const readyCount = drafts.filter((draft) => assessReplyQuality(draft.content, draft.platform).level === "ready").length;
    const reviewCount = drafts.length - readyCount;
    const report = [
      `${projectName} - Weekly Content Summary`,
      "",
      `Reply drafts: ${drafts.length}`,
      `Ready to post: ${readyCount}`,
      `Needs review: ${reviewCount}`,
      `Original post drafts: ${postDrafts.length}`,
      `Published items: ${totalPublished}`,
      "",
      "Top reply drafts:",
      ...drafts.slice(0, 5).map((draft, index) => {
        const quality = assessReplyQuality(draft.content, draft.platform);
        return `${index + 1}. ${draft.opportunity_title || "Reply Draft"} (${quality.label}, ${quality.score}/100)`;
      }),
    ].join("\n");
    try {
      await copyText(report);
      success("Report copied", "Weekly summary copied to clipboard.");
    } catch {
      error("Could not copy report", "Clipboard access was denied.");
    }
  }

  async function generatePostDraft() {
    if (!project) {
      return;
    }
    setGeneratingPost(true);
    try {
      const draft = await apiRequest<PostDraft>(
        "/v1/drafts/posts",
        {
          method: "POST",
          body: JSON.stringify({ project_id: project.id }),
        },
        token
      );
      success("Original post drafted");
      setPostDrafts((rows) => [draft, ...rows]);
      openPostDraft(draft);
      setActiveTab("posts");
    } catch (err: unknown) {
      error("Could not generate post draft", getErrorMessage(err));
    }
    setGeneratingPost(false);
  }

  async function generateContentCalendar() {
    if (!project || !token) {
      return;
    }
    const mutationVersion = ++postDraftMutationRef.current;
    setGeneratingPlan(true);
    try {
      const created = await createContentPlan(token, {
        project_id: project.id,
        platform: plannerPlatform,
        horizon_days: plannerWindow,
        campaign_goal: plannerCampaign,
        campaign_brief: plannerBrief.trim() || null,
        voice_style: plannerVoice,
        content_template: plannerTemplate,
      });
      if (postDraftMutationRef.current !== mutationVersion) {
        return;
      }
      setPostDrafts((rows) => [
        ...created,
        ...rows.filter((row) => !created.some((draft) => draft.id === row.id)),
      ]);
      setActiveTab("calendar");
      success(
        "Content plan generated",
        `${created.length} ${PLATFORM_LABELS[plannerPlatform]} suggestion${created.length === 1 ? "" : "s"} added to the calendar.`
      );
    } catch (err: unknown) {
      error("Could not generate content plan", getErrorMessage(err));
    } finally {
      setGeneratingPlan(false);
    }
  }

  async function approveSchedule(draft: PostDraft) {
    if (!token) {
      return;
    }
    setSchedulingDraftId(draft.id);
    try {
      const updated = await schedulePostDraft(token, draft.id, draft.scheduled_at || defaultScheduleSlot());
      setPostDrafts((rows) => rows.map((row) => (row.id === updated.id ? updated : row)));
      setSelectedPost((current) => (current?.id === updated.id ? updated : current));
      success("Scheduled", "This post is now approved on your content calendar.");
    } catch (err: unknown) {
      error("Could not schedule post", getErrorMessage(err));
    } finally {
      setSchedulingDraftId(null);
    }
  }

  async function rescheduleCalendarDraft(draft: PostDraft, date: Date) {
    if (!token) {
      return;
    }
    const existingSlot = new Date(draft.scheduled_at || defaultScheduleSlot());
    const nextSlot = new Date(date);
    nextSlot.setHours(existingSlot.getHours(), existingSlot.getMinutes(), 0, 0);
    setSchedulingDraftId(draft.id);
    try {
      const updated = await schedulePostDraft(token, draft.id, nextSlot.toISOString());
      setPostDrafts((rows) => rows.map((row) => (row.id === updated.id ? updated : row)));
      setSelectedPost((current) => (current?.id === updated.id ? updated : current));
      success("Post moved", `Scheduled for ${formatDayLabel(nextSlot)}.`);
    } catch (err: unknown) {
      error("Could not move post", getErrorMessage(err));
    } finally {
      setSchedulingDraftId(null);
      setDraggingDraftId(null);
    }
  }

  async function markCalendarDraftStatus(draft: PostDraft, status: "draft" | "needs_edit" | "rejected") {
    if (!token) {
      return;
    }
    setSchedulingDraftId(draft.id);
    try {
      const updated = await updatePostDraft(token, draft.id, {
        title: selectedPost?.id === draft.id ? postTitle : draft.title,
        body: selectedPost?.id === draft.id ? postBody : draft.body,
        rationale: selectedPost?.id === draft.id
          ? combinePostRationale(postReviewNote, postMediaBrief)
          : draft.rationale,
        status,
      });
      setPostDrafts((rows) => rows.map((row) => (row.id === updated.id ? updated : row)));
      setSelectedPost((current) => (current?.id === updated.id ? updated : current));
      success("Review status updated", calendarStatusLabel(status));
    } catch (err: unknown) {
      error("Could not update status", getErrorMessage(err));
    } finally {
      setSchedulingDraftId(null);
    }
  }

  async function approveCalendarPlan() {
    if (!token) {
      return;
    }
    const draftsToApprove = calendarDrafts.filter((draft) => draftStatus(draft) === "draft");
    if (draftsToApprove.length === 0) {
      success("Calendar already approved", "All visible calendar posts are scheduled.");
      return;
    }

    setApprovingCalendar(true);
    try {
      const results = await Promise.allSettled(
        draftsToApprove.map((draft) => schedulePostDraft(token, draft.id, draft.scheduled_at || defaultScheduleSlot()))
      );
      const approved = results
        .filter((result): result is PromiseFulfilledResult<PostDraft> => result.status === "fulfilled")
        .map((result) => result.value);

      if (approved.length > 0) {
        const approvedById = new Map(approved.map((draft) => [draft.id, draft]));
        setPostDrafts((rows) => rows.map((row) => approvedById.get(row.id) ?? row));
      }

      const failed = results.length - approved.length;
      if (failed > 0) {
        error("Some posts could not be scheduled", `${approved.length} approved, ${failed} need another try.`);
      } else {
        success("Calendar approved", `${approved.length} post${approved.length === 1 ? "" : "s"} scheduled.`);
      }
    } catch (err: unknown) {
      error("Could not approve calendar", getErrorMessage(err));
    } finally {
      setApprovingCalendar(false);
    }
  }

  async function approveReadyCalendarPosts() {
    if (!token) {
      return;
    }
    const draftsToApprove = calendarDrafts.filter((draft) => {
      if (draftStatus(draft) !== "draft") {
        return false;
      }
      return assessReplyQuality(draft.body, draftPlatform(draft)).level === "ready";
    });
    if (draftsToApprove.length === 0) {
      error("No ready posts", "Review the posts marked Needs review before approving them.");
      return;
    }

    setApprovingCalendar(true);
    try {
      const results = await Promise.allSettled(
        draftsToApprove.map((draft) => schedulePostDraft(token, draft.id, draft.scheduled_at || defaultScheduleSlot()))
      );
      const approved = results
        .filter((result): result is PromiseFulfilledResult<PostDraft> => result.status === "fulfilled")
        .map((result) => result.value);

      if (approved.length > 0) {
        const approvedById = new Map(approved.map((draft) => [draft.id, draft]));
        setPostDrafts((rows) => rows.map((row) => approvedById.get(row.id) ?? row));
      }

      const failed = results.length - approved.length;
      if (failed > 0) {
        error("Some ready posts could not be approved", `${approved.length} approved, ${failed} need another try.`);
      } else {
        success("Ready posts approved", `${approved.length} post${approved.length === 1 ? "" : "s"} scheduled.`);
      }
    } catch (err: unknown) {
      error("Could not approve ready posts", getErrorMessage(err));
    } finally {
      setApprovingCalendar(false);
    }
  }

  async function copyCalendarSchedule() {
    if (calendarDrafts.length === 0) {
      error("No calendar posts", "Generate a plan before copying the schedule.");
      return;
    }

    const lines = [
      `${project?.name || "Project"} Content Calendar`,
      `Window: ${plannerWindow} days`,
      "",
      ...calendarDrafts.map((draft) => {
        const scheduledDate = new Date(draft.scheduled_at || draft.created_at);
        const channel = draftPlatform(draft) === "linkedin" ? "LinkedIn" : "X / Twitter";
        return [
          `${formatDayLabel(scheduledDate)} ${formatTime(draft.scheduled_at)} - ${channel} - ${draftStatus(draft)}`,
          draft.title,
          draft.body,
        ].join("\n");
      }),
    ].join("\n\n");

    try {
      await copyText(lines);
      success("Schedule copied", "Calendar plan copied for manual publishing or import.");
    } catch {
      error("Could not copy schedule", "Clipboard access was denied.");
    }
  }

  function exportCalendarCsv() {
    if (calendarDrafts.length === 0) {
      error("No calendar posts", "Generate a plan before exporting the calendar.");
      return;
    }

    const headers = ["scheduled_at", "platform", "status", "title", "body"];
    const rows = calendarDrafts.map((draft) => [
      draft.scheduled_at || draft.created_at,
      draftPlatform(draft) === "linkedin" ? "LinkedIn" : "X / Twitter",
      draftStatus(draft),
      draft.title,
      draft.body,
    ]);
    const csv = [
      headers.map(csvValue).join(","),
      ...rows.map((row) => row.map(csvValue).join(",")),
    ].join("\n");

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${safeFilePart(project?.name || "content")}-calendar-${plannerWindow}d.csv`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    success("Calendar exported", "CSV is ready for Postiz or manual scheduling.");
  }

  async function moveBackToDraft(draft: PostDraft) {
    if (!token) {
      return;
    }
    setSchedulingDraftId(draft.id);
    try {
      const updated = await unschedulePostDraft(token, draft.id);
      setPostDrafts((rows) => rows.map((row) => (row.id === updated.id ? updated : row)));
      setSelectedPost((current) => (current?.id === updated.id ? updated : current));
      success("Moved to draft", "This post is back in review.");
    } catch (err: unknown) {
      error("Could not update schedule", getErrorMessage(err));
    } finally {
      setSchedulingDraftId(null);
    }
  }

  function openReplyDraft(draft: ReplyDraftRow) {
    setSelectedPost(null);
    setSelectedReply(draft);
    setReplyContent(draft.content);
    setThreadOpen(true);
    setRationaleOpen(false);
  }

  function openPostDraft(draft: PostDraft) {
    const rationale = splitPostRationale(draft.rationale);
    setSelectedReply(null);
    setSelectedPost(draft);
    setPostTitle(draft.title);
    setPostBody(draft.body);
    setPostReviewNote(rationale.note);
    setPostMediaBrief(rationale.media);
  }

  function applyPostRewrite(preset: PostRewritePreset) {
    const rewritten = rewritePostCopy(postTitle, postBody, preset, selectedPostPlatform);
    setPostTitle(rewritten.title);
    setPostBody(rewritten.body);
    success("Draft rewritten", preset === "less_salesy" ? "Promotional phrasing was softened." : "Review the updated copy before saving.");
  }

  async function uploadCalendarAsset(file: File | null) {
    if (!file || !token || !project) {
      return;
    }
    setUploadingCalendarAsset(true);
    try {
      const result = await uploadAnalysisFile(token, file, project.id);
      const summary = [
        `Asset: ${result.file.file_name}`,
        `Type: ${result.file.file_type}`,
        `Analysis: ${String(result.analysis.status || result.file.analysis_status)}`,
      ].join("\n");
      setPostMediaBrief((current) => [current.trim(), summary].filter(Boolean).join("\n\n"));
      success("Asset attached", "Media or source notes were added to this calendar post.");
    } catch (err: unknown) {
      error("Could not upload asset", getErrorMessage(err));
    } finally {
      setUploadingCalendarAsset(false);
    }
  }

  useEffect(() => {
    if (!requestedOpportunityId || loading) {
      return;
    }
    if (requestedProjectId && selectedProjectId !== requestedProjectId) {
      return;
    }

    const existingDraft = drafts.find((draft) => draft.opportunity_id === requestedOpportunityId);
    if (existingDraft && handledOpportunityIdRef.current !== requestedOpportunityId) {
      openReplyDraft(existingDraft);
      handledOpportunityIdRef.current = requestedOpportunityId;
    }
  }, [drafts, loading, requestedOpportunityId, requestedProjectId, selectedProjectId]);

  useEffect(() => {
    if (!token || !requestedOpportunityId || loading) {
      return;
    }
    if (requestedProjectId && selectedProjectId !== requestedProjectId) {
      return;
    }
    if (handledOpportunityIdRef.current === requestedOpportunityId) {
      return;
    }
    if (drafts.some((draft) => draft.opportunity_id === requestedOpportunityId)) {
      return;
    }
    if (pendingOpportunityIdRef.current === requestedOpportunityId) {
      return;
    }

    const generateMissingDraft = async () => {
      pendingOpportunityIdRef.current = requestedOpportunityId;
      try {
        const draft = await generateReplyDraft(requestedOpportunityId);
        // Mark as handled either way so we don't keep POSTing if the new
        // draft never surfaces in the next loadDrafts() (e.g. permissions
        // filter it out, backend returns empty list, etc.).
        handledOpportunityIdRef.current = requestedOpportunityId;
        if (draft) {
          await loadDrafts();
        }
      } finally {
        pendingOpportunityIdRef.current = null;
      }
    };

    void generateMissingDraft();
  }, [drafts, generateReplyDraft, loading, requestedOpportunityId, requestedProjectId, selectedProjectId, token]);

  async function saveReplyDraft() {
    if (!selectedReply) {
      return;
    }
    const updated = await persistReplyDraft(selectedReply.id, {
      content: replyContent,
      rationale: selectedReply.rationale || null,
    });
    if (!updated) {
      return;
    }
    setDrafts((rows) => rows.map((row) => (row.id === updated.id ? { ...row, content: updated.content, rationale: updated.rationale || "" } : row)));
    setSelectedReply((current) => (current ? { ...current, content: updated.content, rationale: updated.rationale || "" } : current));
  }

  async function savePostDraft() {
    if (!selectedPost) {
      return;
    }
    const updated = await persistPostDraft(selectedPost.id, {
      title: postTitle,
      body: postBody,
      rationale: combinePostRationale(postReviewNote, postMediaBrief),
    });
    if (!updated) {
      return;
    }
    setPostDrafts((rows) => rows.map((row) => (row.id === updated.id ? updated : row)));
    setSelectedPost(updated);
  }

  async function markAsPosted(oppId: number) {
    if (await markOpportunityPosted(oppId)) {
      setSelectedReply(null);
      await loadDrafts();
    }
  }

  const totalPublished = postedDrafts.length + publishedPosts.length;
  const selectedReplyQuality = selectedReply ? assessReplyQuality(replyContent, selectedReply.platform) : null;
  const selectedPostPlatform = selectedPost ? draftPlatform(selectedPost) : "reddit";
  const selectedPostIsCalendar = selectedPost ? isCalendarDraft(selectedPost) : false;
  const selectedPostQuality = selectedPost ? assessReplyQuality(postBody, selectedPostPlatform) : null;
  const originalPostDrafts = useMemo(
    () => postDrafts.filter((draft) => draftPlatform(draft) === "reddit"),
    [postDrafts]
  );
  const calendarDrafts = useMemo(
    () => postDrafts
      .filter(isCalendarDraft)
      .sort((a, b) => {
        const aTime = a.scheduled_at ? new Date(a.scheduled_at).getTime() : new Date(a.created_at).getTime();
        const bTime = b.scheduled_at ? new Date(b.scheduled_at).getTime() : new Date(b.created_at).getTime();
        return aTime - bTime;
      }),
    [postDrafts]
  );
  const calendarStatusStats = useMemo(() => ({
    draft: calendarDrafts.filter((draft) => draftStatus(draft) === "draft").length,
    scheduled: calendarDrafts.filter((draft) => draftStatus(draft) === "scheduled").length,
    needsEdit: calendarDrafts.filter((draft) => draftStatus(draft) === "needs_edit").length,
    rejected: calendarDrafts.filter((draft) => draftStatus(draft) === "rejected").length,
  }), [calendarDrafts]);
  const scheduledCalendarCount = calendarStatusStats.scheduled;
  const suggestedCalendarCount = calendarStatusStats.draft + calendarStatusStats.needsEdit;
  const nextCalendarDraft = calendarDrafts.find((draft) => draftStatus(draft) === "scheduled") ?? calendarDrafts[0] ?? null;
  const visibleCalendarDrafts = useMemo(
    () =>
      calendarDrafts.filter((draft) => {
        const platform = draftPlatform(draft);
        const status = draftStatus(draft) as CalendarStatusFilter;
        return (
          (calendarPlatformFilter === "all" || platform === calendarPlatformFilter) &&
          (calendarStatusFilter === "all" || status === calendarStatusFilter)
        );
      }),
    [calendarDrafts, calendarPlatformFilter, calendarStatusFilter],
  );
  const calendarQualityStats = useMemo(() => {
    let ready = 0;
    let review = 0;
    let risky = 0;
    for (const draft of calendarDrafts) {
      const quality = assessReplyQuality(draft.body, draftPlatform(draft));
      if (quality.level === "ready") {
        ready += 1;
      } else if (quality.level === "review") {
        review += 1;
      } else {
        risky += 1;
      }
    }
    return { ready, review, risky };
  }, [calendarDrafts]);
  const calendarAnalytics = useMemo(() => {
    const qualityScores = calendarDrafts.map((draft) => assessReplyQuality(draft.body, draftPlatform(draft)).score);
    const averageQuality =
      qualityScores.length > 0 ? Math.round(qualityScores.reduce((total, score) => total + score, 0) / qualityScores.length) : 0;
    const approvalRate =
      calendarDrafts.length > 0 ? Math.round((calendarStatusStats.scheduled / calendarDrafts.length) * 100) : 0;
    const xCount = calendarDrafts.filter((draft) => draftPlatform(draft) === "x").length;
    const linkedinCount = calendarDrafts.filter((draft) => draftPlatform(draft) === "linkedin").length;
    return { averageQuality, approvalRate, xCount, linkedinCount };
  }, [calendarDrafts, calendarStatusStats.scheduled]);
  const calendarReadinessPercent =
    calendarDrafts.length > 0 ? Math.round((calendarQualityStats.ready / calendarDrafts.length) * 100) : 0;
  const visibleSuggestedCount = visibleCalendarDrafts.filter((draft) => draftStatus(draft) === "draft").length;
  const calendarDays = useMemo(() => {
    const today = new Date();
    today.setDate(today.getDate() + 1);
    today.setHours(0, 0, 0, 0);
    return Array.from({ length: plannerWindow }, (_, index) => {
      const date = new Date(today);
      date.setDate(today.getDate() + index);
      const key = dateKey(date);
      const items = visibleCalendarDrafts.filter((draft) => {
        const value = draft.scheduled_at || draft.created_at;
        return dateKey(new Date(value)) === key;
      });
      return { date, key, items };
    });
  }, [visibleCalendarDrafts, plannerWindow]);

  return (
    <div className="space-y-8">
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <PageHeader
          title="Content Studio"
          description="Manage reply drafts, original posts, and published activity from one workflow."
          actions={
            <div className="flex flex-wrap items-center justify-end gap-2">
              <Button variant="outline" onClick={() => void copyWeeklyReport()} disabled={loading}>
                <ClipboardList className="h-4 w-4" />
                Copy Report
              </Button>
              <Button onClick={generatePostDraft} disabled={generatingPost || !project}>
                {generatingPost && <Loader2 className="h-4 w-4 animate-spin" />}
                New Original Post
              </Button>
            </div>
          }
          tabs={
            <TabsList>
              <TabsTrigger value="replies">
                Reply Queue
                {drafts.length > 0 && (
                  <Badge variant="secondary" className="ml-1.5">{drafts.length}</Badge>
                )}
              </TabsTrigger>
              <TabsTrigger value="posts">
                Original Posts
                {originalPostDrafts.length > 0 && (
                  <Badge variant="secondary" className="ml-1.5">{originalPostDrafts.length}</Badge>
                )}
              </TabsTrigger>
              <TabsTrigger value="calendar">
                Calendar
                {calendarDrafts.length > 0 && (
                  <Badge variant="secondary" className="ml-1.5">{calendarDrafts.length}</Badge>
                )}
              </TabsTrigger>
              <TabsTrigger value="published">
                Published
                {totalPublished > 0 && (
                  <Badge variant="secondary" className="ml-1.5">{totalPublished}</Badge>
                )}
              </TabsTrigger>
              <TabsTrigger value="templates">Templates</TabsTrigger>
            </TabsList>
          }
        />

        {loading && (
          <div className="grid grid-cols-1 gap-4">
            {[1, 2, 3].map((i) => (
              <Card key={i}>
                <CardContent className="py-4">
                  <div className="flex items-center gap-4">
                    <Skeleton className="h-10 w-10 rounded-full" />
                    <div className="flex-1 space-y-2">
                      <Skeleton className="h-4 w-3/5" />
                      <Skeleton className="h-3 w-4/5" />
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
        {/* Replies Tab */}
        {!loading && (
          <TabsContent value="replies">
          {drafts.length === 0 ? (
            <EmptyState
              icon={MessageSquare}
              title="No reply drafts yet"
              description="Generate response drafts from Social Radar. They will appear here for review, revision, and manual publishing."
              action={{
                label: "Open Social Radar",
                onClick: () => router.push("/app/discovery"),
              }}
            />
          ) : (
            <div className="space-y-2">
              {drafts.map((draft) => (
                <Card
                  key={draft.id}
                  className="cursor-pointer transition-colors hover:bg-accent/50"
                  onClick={() => openReplyDraft(draft)}
                >
                  <CardContent className="flex items-center gap-4 py-4">
                    {/* Left section */}
                    <div className="flex items-center gap-2 shrink-0">
                      <PlatformIcon platform={draft.platform || "reddit"} />
                      {draft.opportunity_subreddit && (
                        <Badge variant="outline">{replySourceLabel(draft)}</Badge>
                      )}
                      <Badge variant="secondary">v{draft.version}</Badge>
                    </div>

                    {/* Center section */}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">
                        {draft.opportunity_title || "Reply Draft"}
                      </p>
                      <p className="text-xs text-muted-foreground truncate">
                        {draft.content.substring(0, 100)}{draft.content.length > 100 ? "..." : ""}
                      </p>
                    </div>

                    {/* Right section */}
                    <div className="flex items-center gap-2 shrink-0">
                      {(() => {
                        const quality = assessReplyQuality(draft.content, draft.platform);
                        return (
                          <Badge variant="outline" className={cn("hidden sm:inline-flex", qualityBadgeClass(quality.level))}>
                            {quality.label} {quality.score}
                          </Badge>
                        );
                      })()}
                      {draft.score != null && <ScoreBadge score={draft.score} />}
                      <DropdownMenu>
                        <DropdownMenuTrigger
                          render={
                            <Button variant="ghost" size="icon-xs">
                              <MoreHorizontal />
                            </Button>
                          }
                          onClick={(e: React.MouseEvent) => e.stopPropagation()}
                        />
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem
                            onClick={(e: React.MouseEvent) => {
                              e.stopPropagation();
                              copyToClipboard(draft.content);
                            }}
                          >
                            <Copy /> Copy
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            onClick={(e: React.MouseEvent) => {
                              e.stopPropagation();
                              openReplyDraft(draft);
                            }}
                          >
                            <Pencil /> Edit
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            onClick={(e: React.MouseEvent) => {
                              e.stopPropagation();
                              setLinkDestination("");
                              setLinkDraft(draft);
                            }}
                          >
                            <Link2 /> Create tracked link
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            disabled={amplifyingId === draft.id}
                            onClick={(e: React.MouseEvent) => {
                              e.stopPropagation();
                              void handleAmplify(draft, "x");
                            }}
                          >
                            <Megaphone /> Amplify to X thread
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            disabled={amplifyingId === draft.id}
                            onClick={(e: React.MouseEvent) => {
                              e.stopPropagation();
                              void handleAmplify(draft, "linkedin");
                            }}
                          >
                            <Megaphone /> Amplify to LinkedIn
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            onClick={(e: React.MouseEvent) => {
                              e.stopPropagation();
                              void markAsPosted(draft.opportunity_id);
                            }}
                          >
                            <CheckCircle /> Mark as Posted
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      )}

      {/* Posts Tab */}
      {!loading && (
        <TabsContent value="posts">
          {originalPostDrafts.length === 0 ? (
            <EmptyState
              icon={FileEdit}
              title="No original post drafts yet"
              description="Use the studio to draft community-native posts inspired by Quora-style answers, Reddit posts, or educational updates."
              action={{
                label: "Generate First Post",
                onClick: generatePostDraft,
              }}
            />
          ) : (
            <div className="space-y-2">
              {originalPostDrafts.map((draft) => (
                <Card
                  key={draft.id}
                  className="cursor-pointer transition-colors hover:bg-accent/50"
                  onClick={() => openPostDraft(draft)}
                >
                  <CardContent className="flex items-center gap-4 py-4">
                    {/* Left section */}
                    <div className="flex items-center gap-2 shrink-0">
                      <PlatformIcon platform="reddit" />
                      <Badge variant="secondary">Original Post</Badge>
                      <Badge variant="outline">v{draft.version}</Badge>
                    </div>

                    {/* Center section */}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{draft.title}</p>
                      <p className="text-xs text-muted-foreground truncate">
                        {draft.body.substring(0, 100)}{draft.body.length > 100 ? "..." : ""}
                      </p>
                    </div>

                    {/* Right section */}
                    <div className="flex items-center gap-2 shrink-0">
                      <Button
                        variant="ghost"
                        size="xs"
                        onClick={(event) => {
                          event.stopPropagation();
                          copyToClipboard(`${draft.title}\n\n${draft.body}`);
                        }}
                      >
                        <Copy className="h-3 w-3" /> Copy
                      </Button>
                      <Button
                        size="xs"
                        onClick={(event) => {
                          event.stopPropagation();
                          setPostingDraftId(draft.id);
                          setShowPostConfirm(true);
                        }}
                      >
                        Post to Reddit
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      )}

      {/* Calendar Tab */}
      {!loading && (
        <TabsContent value="calendar">
          <div className="space-y-4">
            <Card>
              <CardContent className="flex flex-col gap-4 py-4 lg:flex-row lg:items-center lg:justify-between">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <CalendarDays className="h-4 w-4 text-primary" />
                    <p className="text-sm font-semibold">Content Calendar</p>
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Generate platform-native posts, review them, then approve the ones you want scheduled.
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <div className="flex rounded-lg border bg-muted/40 p-1">
                    {(["x", "linkedin"] as PlannerPlatform[]).map((platform) => (
                      <Button
                        key={platform}
                        type="button"
                        size="sm"
                        variant={plannerPlatform === platform ? "default" : "ghost"}
                        onClick={() => setPlannerPlatform(platform)}
                      >
                        <PlatformIcon platform={platform} />
                        {PLATFORM_LABELS[platform]}
                      </Button>
                    ))}
                  </div>
                  <div className="flex rounded-lg border bg-muted/40 p-1">
                    {([7, 30] as PlannerWindow[]).map((days) => (
                      <Button
                        key={days}
                        type="button"
                        size="sm"
                        variant={plannerWindow === days ? "default" : "ghost"}
                        onClick={() => setPlannerWindow(days)}
                      >
                        {days === 7 ? "1 week" : "1 month"}
                      </Button>
                    ))}
                  </div>
                  <div className="flex max-w-full overflow-x-auto rounded-lg border bg-muted/40 p-1">
                    {CAMPAIGN_OPTIONS.map((campaign) => (
                      <Button
                        key={campaign.value}
                        type="button"
                        size="sm"
                        variant={plannerCampaign === campaign.value ? "default" : "ghost"}
                        onClick={() => setPlannerCampaign(campaign.value)}
                        className="shrink-0"
                      >
                        <Target className="h-4 w-4" />
                        {campaign.label}
                      </Button>
                    ))}
                  </div>
                  <Button onClick={() => void generateContentCalendar()} disabled={generatingPlan || !project}>
                    {generatingPlan ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                    Generate Plan
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => void copyCalendarSchedule()}
                    disabled={calendarDrafts.length === 0}
                  >
                    <ClipboardList className="h-4 w-4" />
                    Copy Schedule
                  </Button>
                  <Button
                    variant="outline"
                    onClick={exportCalendarCsv}
                    disabled={calendarDrafts.length === 0}
                  >
                    <Download className="h-4 w-4" />
                    Export CSV
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => void approveCalendarPlan()}
                    disabled={approvingCalendar || suggestedCalendarCount === 0}
                  >
                    {approvingCalendar ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle className="h-4 w-4" />}
                    Approve Plan
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => void approveReadyCalendarPosts()}
                    disabled={approvingCalendar || calendarQualityStats.ready === 0 || suggestedCalendarCount === 0}
                  >
                    <ShieldCheck className="h-4 w-4" />
                    Approve ready
                  </Button>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="grid gap-4 py-4 lg:grid-cols-[1.1fr_1fr]">
                <div className="space-y-2">
                  <Label htmlFor="campaign-brief">Campaign brief</Label>
                  <Textarea
                    id="campaign-brief"
                    value={plannerBrief}
                    onChange={(event) => setPlannerBrief(event.target.value)}
                    placeholder="Example: Promote verified Gurgaon properties, focus on avoiding fake listings, and keep the CTA soft."
                    className="min-h-24"
                    maxLength={800}
                  />
                  <p className="text-xs text-muted-foreground">{plannerBrief.length}/800 characters</p>
                </div>
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label>Brand voice</Label>
                    <div className="flex flex-wrap gap-2">
                      {VOICE_OPTIONS.map((option) => (
                        <Button
                          key={option.value}
                          type="button"
                          size="sm"
                          variant={plannerVoice === option.value ? "default" : "outline"}
                          onClick={() => setPlannerVoice(option.value)}
                        >
                          {option.label}
                        </Button>
                      ))}
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label>Content template</Label>
                    <div className="flex flex-wrap gap-2">
                      {TEMPLATE_OPTIONS.map((option) => (
                        <Button
                          key={option.value}
                          type="button"
                          size="sm"
                          variant={plannerTemplate === option.value ? "default" : "outline"}
                          onClick={() => setPlannerTemplate(option.value)}
                        >
                          <LayoutTemplate className="h-4 w-4" />
                          {option.label}
                        </Button>
                      ))}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
              <Card>
                <CardContent className="py-4">
                  <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Suggestions</p>
                  <p className="mt-2 text-2xl font-semibold">{suggestedCalendarCount}</p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="py-4">
                  <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Scheduled</p>
                  <p className="mt-2 text-2xl font-semibold">{scheduledCalendarCount}</p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="py-4">
                  <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Next Slot</p>
                  <p className="mt-2 truncate text-2xl font-semibold">
                    {nextCalendarDraft ? formatDayLabel(new Date(nextCalendarDraft.scheduled_at || nextCalendarDraft.created_at)) : "-"}
                  </p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="py-4">
                  <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Current Window</p>
                  <p className="mt-2 text-2xl font-semibold">{plannerWindow} days</p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="py-4">
                  <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Ready Score</p>
                  <p className="mt-2 text-2xl font-semibold">{calendarReadinessPercent}%</p>
                </CardContent>
              </Card>
            </div>

            <Card>
              <CardContent className="grid gap-3 py-4 md:grid-cols-[1.1fr_1fr_1fr]">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <Megaphone className="h-4 w-4 text-primary" />
                    <p className="text-sm font-semibold">Publishing readiness</p>
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Approved posts stay queued here until platform connectors are enabled.
                  </p>
                </div>
                <div className="rounded-lg border bg-background p-3">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <PlatformIcon platform="x" />
                      <span className="text-sm font-medium">X / Twitter</span>
                    </div>
                    <StatusBadge variant="warning">Manual</StatusBadge>
                  </div>
                  <p className="mt-2 text-xs text-muted-foreground">{calendarDrafts.filter((draft) => draftPlatform(draft) === "x").length} queued</p>
                </div>
                <div className="rounded-lg border bg-background p-3">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <PlatformIcon platform="linkedin" />
                      <span className="text-sm font-medium">LinkedIn</span>
                    </div>
                    <StatusBadge variant="warning">Manual</StatusBadge>
                  </div>
                  <p className="mt-2 text-xs text-muted-foreground">{calendarDrafts.filter((draft) => draftPlatform(draft) === "linkedin").length} queued</p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="grid gap-3 py-4 md:grid-cols-[1fr_3fr]">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <BarChart3 className="h-4 w-4 text-primary" />
                    <p className="text-sm font-semibold">Calendar analytics</p>
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Live checks from the current draft plan.
                  </p>
                </div>
                <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
                  <div className="rounded-lg border bg-background p-3">
                    <p className="text-xs text-muted-foreground">Approval rate</p>
                    <p className="mt-1 text-lg font-semibold">{calendarAnalytics.approvalRate}%</p>
                  </div>
                  <div className="rounded-lg border bg-background p-3">
                    <p className="text-xs text-muted-foreground">Avg. quality</p>
                    <p className="mt-1 text-lg font-semibold">{calendarAnalytics.averageQuality}/100</p>
                  </div>
                  <div className="rounded-lg border bg-background p-3">
                    <p className="text-xs text-muted-foreground">Platform mix</p>
                    <p className="mt-1 text-lg font-semibold">{calendarAnalytics.xCount} X / {calendarAnalytics.linkedinCount} LI</p>
                  </div>
                  <div className="rounded-lg border bg-background p-3">
                    <p className="text-xs text-muted-foreground">Needs action</p>
                    <p className="mt-1 text-lg font-semibold">{calendarStatusStats.needsEdit + calendarStatusStats.rejected}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <div className="grid gap-3 lg:grid-cols-[1fr_1.2fr]">
              <Card>
                <CardContent className="py-4">
                  <div className="flex items-center gap-2">
                    <ListChecks className="h-4 w-4 text-primary" />
                    <p className="text-sm font-semibold">Approval queue</p>
                  </div>
                  <div className="mt-3 grid grid-cols-3 gap-2 text-center">
                    <div className="rounded-lg border bg-background p-3">
                      <p className="text-lg font-semibold">{visibleSuggestedCount}</p>
                      <p className="text-[11px] text-muted-foreground">Pending</p>
                    </div>
                    <div className="rounded-lg border bg-background p-3">
                      <p className="text-lg font-semibold text-emerald-300">{calendarQualityStats.ready}</p>
                      <p className="text-[11px] text-muted-foreground">Ready</p>
                    </div>
                    <div className="rounded-lg border bg-background p-3">
                      <p className="text-lg font-semibold text-amber-300">{calendarQualityStats.review + calendarQualityStats.risky}</p>
                      <p className="text-[11px] text-muted-foreground">Review</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="flex flex-col gap-3 py-4">
                  <div className="flex items-center gap-2">
                    <Filter className="h-4 w-4 text-primary" />
                    <p className="text-sm font-semibold">Calendar filters</p>
                    <Badge variant="secondary">{visibleCalendarDrafts.length} shown</Badge>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {(["board", "list"] as CalendarLayout[]).map((layout) => (
                      <Button
                        key={layout}
                        type="button"
                        size="sm"
                        variant={calendarLayout === layout ? "default" : "outline"}
                        onClick={() => setCalendarLayout(layout)}
                      >
                        {layout === "board" ? "Board view" : "List view"}
                      </Button>
                    ))}
                    {(["all", "x", "linkedin"] as CalendarPlatformFilter[]).map((platform) => (
                      <Button
                        key={platform}
                        type="button"
                        size="sm"
                        variant={calendarPlatformFilter === platform ? "default" : "outline"}
                        onClick={() => setCalendarPlatformFilter(platform)}
                      >
                        {platform === "all" ? "All platforms" : (
                          <>
                            <PlatformIcon platform={platform} />
                            {PLATFORM_LABELS[platform]}
                          </>
                        )}
                      </Button>
                    ))}
                    {(["all", "draft", "scheduled", "needs_edit", "rejected"] as CalendarStatusFilter[]).map((status) => (
                      <Button
                        key={status}
                        type="button"
                        size="sm"
                        variant={calendarStatusFilter === status ? "default" : "outline"}
                        onClick={() => setCalendarStatusFilter(status)}
                      >
                        {CALENDAR_STATUS_LABELS[status]}
                      </Button>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>

            {calendarDrafts.length === 0 ? (
              <EmptyState
                icon={CalendarDays}
                title="No scheduled content yet"
                description="Generate a 1-week or 1-month plan to get suggested X and LinkedIn posts ready for review."
                action={{
                  label: "Generate Plan",
                  onClick: generateContentCalendar,
                }}
              />
            ) : visibleCalendarDrafts.length === 0 ? (
              <EmptyState
                icon={Filter}
                title="No posts match these filters"
                description="Clear the platform or approval filter to review more calendar posts."
                action={{
                  label: "Clear filters",
                  onClick: () => {
                    setCalendarPlatformFilter("all");
                    setCalendarStatusFilter("all");
                  },
                }}
              />
            ) : calendarLayout === "list" ? (
              <div className="space-y-2">
                {visibleCalendarDrafts.map((draft) => {
                  const status = draftStatus(draft);
                  const isScheduled = status === "scheduled";
                  const quality = assessReplyQuality(draft.body, draftPlatform(draft));
                  const rationaleParts = splitPostRationale(draft.rationale);
                  const scheduledDate = new Date(draft.scheduled_at || draft.created_at);
                  return (
                    <Card key={draft.id} className="transition-colors hover:bg-muted/30">
                      <CardContent className="flex flex-col gap-3 py-4 lg:flex-row lg:items-center">
                        <div className="flex items-center gap-3 lg:w-56">
                          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border bg-background">
                            <PlatformIcon platform={draftPlatform(draft)} />
                          </div>
                          <div className="min-w-0">
                            <p className="text-sm font-semibold">{formatDayLabel(scheduledDate)}</p>
                            <p className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                              <Clock3 className="h-3 w-3" />
                              {formatTime(draft.scheduled_at)}
                            </p>
                          </div>
                        </div>

                        <div className="min-w-0 flex-1">
                          <div className="mb-2 flex flex-wrap items-center gap-2">
                            <StatusBadge variant={calendarStatusVariant(status)}>
                              {calendarStatusLabel(status)}
                            </StatusBadge>
                            <Badge variant="outline" className={qualityBadgeClass(quality.level)}>
                              {quality.label} {quality.score}
                            </Badge>
                            {rationaleParts.media && <Badge variant="secondary">Media planned</Badge>}
                          </div>
                          <p className="line-clamp-1 text-sm font-semibold">{draft.title}</p>
                          <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-muted-foreground">{draft.body}</p>
                        </div>

                        <div className="flex flex-wrap gap-2 lg:justify-end">
                          <Button variant="outline" size="sm" onClick={() => openPostDraft(draft)}>
                            Review
                          </Button>
                          <Button variant="outline" size="sm" onClick={() => copyToClipboard(`${draft.title}\n\n${draft.body}`)}>
                            <Copy className="h-3.5 w-3.5" />
                            Copy
                          </Button>
                          {isScheduled ? (
                            <Button
                              variant="outline"
                              size="sm"
                              disabled={schedulingDraftId === draft.id}
                              onClick={() => void moveBackToDraft(draft)}
                            >
                              Move to draft
                            </Button>
                          ) : (
                            <Button size="sm" disabled={schedulingDraftId === draft.id} onClick={() => void approveSchedule(draft)}>
                              {schedulingDraftId === draft.id && <Loader2 className="h-4 w-4 animate-spin" />}
                              Approve
                            </Button>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            ) : (
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                {calendarDays.map((day) => (
                  <div
                    key={day.key}
                    onDragOver={(event) => event.preventDefault()}
                    onDrop={(event) => {
                      event.preventDefault();
                      const draftId = Number(event.dataTransfer.getData("text/plain") || draggingDraftId);
                      const draft = calendarDrafts.find((item) => item.id === draftId);
                      if (draft) {
                        void rescheduleCalendarDraft(draft, day.date);
                      }
                    }}
                    className={cn(
                      "min-h-[180px] rounded-lg border bg-card p-3 transition-colors",
                      draggingDraftId && "border-primary/40 bg-primary/5",
                    )}
                  >
                    <div className="mb-3 flex items-center justify-between gap-2">
                      <div>
                        <p className="text-sm font-semibold">{formatDayLabel(day.date)}</p>
                        <p className="text-xs text-muted-foreground">{day.items.length} item{day.items.length === 1 ? "" : "s"}</p>
                      </div>
                    </div>
                    {day.items.length === 0 ? (
                      <div className="flex h-24 items-center justify-center rounded-lg border border-dashed text-xs text-muted-foreground">
                        Open slot
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {day.items.map((draft) => {
                          const status = draftStatus(draft);
                          const isScheduled = status === "scheduled";
                          const quality = assessReplyQuality(draft.body, draftPlatform(draft));
                          return (
                            <div
                              key={draft.id}
                              role="button"
                              tabIndex={0}
                              draggable
                              onDragStart={(event) => {
                                setDraggingDraftId(draft.id);
                                event.dataTransfer.setData("text/plain", String(draft.id));
                                event.dataTransfer.effectAllowed = "move";
                              }}
                              onDragEnd={() => setDraggingDraftId(null)}
                              onClick={() => openPostDraft(draft)}
                              onKeyDown={(event) => {
                                if (event.key === "Enter" || event.key === " ") {
                                  openPostDraft(draft);
                                }
                              }}
                              className={cn(
                                "rounded-lg border bg-background p-3 text-left transition-colors hover:bg-muted/50",
                                draggingDraftId === draft.id && "opacity-60",
                              )}
                            >
                              <div className="mb-2 flex items-center justify-between gap-2">
                                <div className="flex items-center gap-1.5">
                                  <GripVertical className="h-3.5 w-3.5 text-muted-foreground" />
                                  <PlatformIcon platform={draftPlatform(draft)} />
                                  <span className="text-xs font-medium">{draftPlatform(draft) === "linkedin" ? "LinkedIn" : "X"}</span>
                                </div>
                                <StatusBadge variant={calendarStatusVariant(status)}>
                                  {calendarStatusLabel(status)}
                                </StatusBadge>
                              </div>
                              <Badge variant="outline" className={cn("mb-2", qualityBadgeClass(quality.level))}>
                                {quality.label} {quality.score}
                              </Badge>
                              <p className="line-clamp-2 text-sm font-medium leading-snug">{draft.title}</p>
                              <p className="mt-1 line-clamp-3 text-xs leading-relaxed text-muted-foreground">
                                {draft.body}
                              </p>
                              <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                                <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                                  <Clock3 className="h-3 w-3" />
                                  {formatTime(draft.scheduled_at)}
                                </span>
                                <div className="flex items-center gap-1">
                                  {isScheduled ? (
                                    <Button
                                      variant="outline"
                                      size="xs"
                                      disabled={schedulingDraftId === draft.id}
                                      onClick={(event) => {
                                        event.stopPropagation();
                                        void moveBackToDraft(draft);
                                      }}
                                    >
                                      Draft
                                    </Button>
                                  ) : (
                                    <Button
                                      size="xs"
                                      disabled={schedulingDraftId === draft.id}
                                      onClick={(event) => {
                                        event.stopPropagation();
                                        void approveSchedule(draft);
                                      }}
                                    >
                                      {schedulingDraftId === draft.id && <Loader2 className="h-3 w-3 animate-spin" />}
                                      Approve
                                    </Button>
                                  )}
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </TabsContent>
      )}

      {/* Published Tab */}
      {!loading && (
        <TabsContent value="published">
          {postedDrafts.length === 0 && publishedPosts.length === 0 ? (
            <EmptyState
              icon={CheckCircle}
              title="No published content yet"
              description="Your published replies and posts will appear here."
            />
          ) : (
            <div className="space-y-2">
              {postedDrafts.map((draft) => (
                <Card key={`reply-${draft.id}`}>
                  <CardContent className="flex items-center gap-4 py-4">
                    <div className="flex items-center gap-2 shrink-0">
                      <PlatformIcon platform={draft.platform || "reddit"} />
                      <StatusBadge variant="success">Posted</StatusBadge>
                      {draft.opportunity_subreddit && (
                        <Badge variant="outline">{replySourceLabel(draft)}</Badge>
                      )}
                    </div>

                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">
                        {draft.opportunity_title || "Published Reply"}
                      </p>
                      <p className="text-xs text-muted-foreground truncate">
                        {draft.content.substring(0, 100)}{draft.content.length > 100 ? "..." : ""}
                      </p>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      {draft.permalink && (
                        <a
                          href={platformUrl(draft.permalink, draft.platform)}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <Button variant="outline" size="xs">
                            <ExternalLink className="h-3 w-3" /> View Thread
                          </Button>
                        </a>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
              {publishedPosts.map((post) => (
                <Card key={`post-${post.id}`}>
                  <CardContent className="flex items-center gap-4 py-4">
                    <div className="flex items-center gap-2 shrink-0">
                      <PlatformIcon platform="reddit" />
                      <StatusBadge variant="success">{post.status}</StatusBadge>
                      <Badge variant="outline">{post.subreddit?.startsWith("r/") ? post.subreddit : `r/${post.subreddit}`}</Badge>
                    </div>

                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">Original Post</p>
                      <div className="flex gap-3 text-xs text-muted-foreground mt-0.5">
                        <span>{new Date(post.post_date).toLocaleDateString()}</span>
                        {post.upvotes !== undefined && <span>{post.upvotes} upvotes</span>}
                        {post.comments !== undefined && <span>{post.comments} comments</span>}
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      {post.permalink && (
                        <a href={redditUrl(post.permalink)} target="_blank" rel="noopener noreferrer">
                          <Button variant="outline" size="xs">
                            <ExternalLink className="h-3 w-3" /> View on Reddit
                          </Button>
                        </a>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      )}

      {/* Templates Tab */}
      {!loading && (
        <TabsContent value="templates">
          <Card>
            <CardContent className="flex items-center gap-4 py-4">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted shrink-0">
                <LayoutTemplate className="h-5 w-5 text-muted-foreground" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium">Prompt Templates</p>
                <p className="text-xs text-muted-foreground">
                  Manage your prompt templates for reply and post generation.
                </p>
              </div>
              <Link href="/app/prompts">
                <Button variant="outline" size="sm">
                  Open Templates <ArrowRight className="h-3.5 w-3.5" />
                </Button>
              </Link>
            </CardContent>
          </Card>
        </TabsContent>
        )}
      </Tabs>

      {/* Reply Draft SheetPanel */}
      <SheetPanel
        title="Reply Draft"
        description="Review and edit your reply before publishing."
        open={!!selectedReply}
        onOpenChange={(open) => !open && setSelectedReply(null)}
        width="lg"
        footer={
          <div className="flex flex-wrap gap-2 w-full">
            <DropdownMenu>
              <DropdownMenuTrigger
                render={
                  <Button variant="outline" disabled={!selectedReply || regeneratingPreset !== null}>
                    {regeneratingPreset ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
                    Regenerate
                  </Button>
                }
              />
              <DropdownMenuContent align="start">
                {REGENERATE_OPTIONS.map((option) => (
                  <DropdownMenuItem key={option.value} onClick={() => void regenerateReply(option.value)}>
                    {option.label}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
            <Button onClick={() => void saveReplyDraft()} disabled={savingReply} className="flex-1">
              {savingReply && <Loader2 className="h-4 w-4 animate-spin" />}
              Save
            </Button>
            <Button variant="outline" onClick={() => copyToClipboard(replyContent)}>
              <Copy className="h-3.5 w-3.5" /> Copy
            </Button>
            {selectedReply?.permalink && (
              <Button
                variant="outline"
                onClick={() => copyAndOpen(replyContent, selectedReply.permalink || "", selectedReply.platform)}
              >
                Copy &amp; Open Post
              </Button>
            )}
            {selectedReply && (
              <Button variant="outline" onClick={() => void markAsPosted(selectedReply.opportunity_id)}>
                <CheckCircle className="h-3.5 w-3.5" /> Mark as Posted
              </Button>
            )}
          </div>
        }
      >
        {selectedReply && (
          <div className="space-y-4">
            {/* Original Reddit post context — always visible so the reviewer
                can see exactly what they're replying to. */}
            {(selectedReply.opportunity_title ||
              selectedReply.opportunity_subreddit ||
              selectedReply.body_excerpt ||
              selectedReply.permalink) && (
              <div className="rounded-lg border bg-muted/40 p-4 space-y-3">
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <div className="flex items-center gap-2 flex-wrap">
                    {selectedReply.opportunity_subreddit && (
                      <Badge variant="secondary" className="font-mono text-xs">
                        {replySourceLabel(selectedReply)}
                      </Badge>
                    )}
                    {typeof selectedReply.score === "number" && (
                      <ScoreBadge score={selectedReply.score} />
                    )}
                  </div>
                  {selectedReply.permalink && (
                    <a
                      href={platformUrl(selectedReply.permalink, selectedReply.platform)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs font-medium text-primary hover:underline inline-flex items-center gap-1"
                    >
                      View source <ExternalLink className="h-3 w-3" />
                    </a>
                  )}
                </div>
                {selectedReply.opportunity_title && (
                  <h3 className="text-sm font-semibold leading-snug">
                    {selectedReply.opportunity_title}
                  </h3>
                )}
                {selectedReply.body_excerpt && (
                  <div>
                    <div
                      className={cn(
                        "text-xs text-muted-foreground leading-relaxed whitespace-pre-wrap",
                        !threadOpen && "line-clamp-4"
                      )}
                    >
                      {selectedReply.body_excerpt}
                    </div>
                    {selectedReply.body_excerpt.length > 280 && (
                      <button
                        type="button"
                        onClick={() => setThreadOpen((prev) => !prev)}
                        className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
                      >
                        <ChevronDown
                          className={cn(
                            "h-3.5 w-3.5 transition-transform",
                            !threadOpen && "-rotate-90"
                          )}
                        />
                        {threadOpen ? "Show less" : "Show full post"}
                      </button>
                    )}
                  </div>
                )}
              </div>
            )}

            {selectedReplyQuality && (
              <div className="rounded-lg border bg-muted/30 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="h-4 w-4 text-primary" />
                    <p className="text-sm font-medium">Reply quality</p>
                  </div>
                  <Badge variant="outline" className={qualityBadgeClass(selectedReplyQuality.level)}>
                    {selectedReplyQuality.label} - {selectedReplyQuality.score}/100
                  </Badge>
                </div>
                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                  <div>
                    <p className="text-xs font-medium text-muted-foreground">Strengths</p>
                    <ul className="mt-1 space-y-1 text-xs text-muted-foreground">
                      {(selectedReplyQuality.strengths.length ? selectedReplyQuality.strengths : ["Clear enough for review."]).map((item) => (
                        <li key={item}>- {item}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-muted-foreground">Safe outreach guard</p>
                    <ul className="mt-1 space-y-1 text-xs text-muted-foreground">
                      {(selectedReplyQuality.warnings.length ? selectedReplyQuality.warnings : ["No major risk detected."]).map((item) => (
                        <li key={item} className="flex gap-1.5">
                          {selectedReplyQuality.warnings.length > 0 && <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0 text-amber-400" />}
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            )}

            {/* Reply content */}
            <div className="space-y-2">
              <Label>Reply Content</Label>
              <Textarea
                rows={12}
                value={replyContent}
                onChange={(event) => setReplyContent(event.target.value)}
                className="text-sm leading-relaxed"
              />
              <p className="text-xs text-muted-foreground">{replyContent.length} characters</p>
            </div>

            {/* Rationale collapsible */}
            {selectedReply.rationale && (
              <Collapsible open={rationaleOpen} onOpenChange={setRationaleOpen}>
                <CollapsibleTrigger className="flex items-center gap-1.5 text-sm font-medium w-full">
                  <ChevronDown
                    className={cn(
                      "h-4 w-4 transition-transform",
                      !rationaleOpen && "-rotate-90"
                    )}
                  />
                  Why this response works
                </CollapsibleTrigger>
                <CollapsibleContent className="mt-2">
                  <div className="rounded-xl bg-muted p-5">
                    <p className="text-sm text-muted-foreground">{selectedReply.rationale}</p>
                  </div>
                </CollapsibleContent>
              </Collapsible>
            )}
          </div>
        )}
      </SheetPanel>

      {/* Post Draft SheetPanel */}
      <SheetPanel
        title={selectedPostIsCalendar ? "Calendar Post Draft" : "Original Post Draft"}
        description={selectedPostIsCalendar ? "Review, edit, and approve this scheduled social post." : "Edit and manage your original post draft."}
        open={!!selectedPost}
        onOpenChange={(open) => !open && setSelectedPost(null)}
        width="lg"
        footer={
          <div className="flex flex-wrap gap-2 w-full">
            <Button onClick={() => void savePostDraft()} disabled={savingPost} className="flex-1">
              {savingPost && <Loader2 className="h-4 w-4 animate-spin" />}
              Save
            </Button>
            <Button variant="outline" onClick={() => copyToClipboard(`${postTitle}\n\n${postBody}`)}>
              <Copy className="h-3.5 w-3.5" /> Copy
            </Button>
            {selectedPostIsCalendar && selectedPost && draftStatus(selectedPost) !== "scheduled" && (
              <Button onClick={() => void approveSchedule(selectedPost)} disabled={schedulingDraftId === selectedPost.id}>
                {schedulingDraftId === selectedPost.id && <Loader2 className="h-4 w-4 animate-spin" />}
                Approve &amp; schedule
              </Button>
            )}
            {selectedPostIsCalendar && selectedPost && draftStatus(selectedPost) === "scheduled" && (
              <Button variant="outline" onClick={() => void moveBackToDraft(selectedPost)} disabled={schedulingDraftId === selectedPost.id}>
                Move to draft
              </Button>
            )}
            {selectedPostIsCalendar && selectedPost && draftStatus(selectedPost) !== "needs_edit" && (
              <Button
                variant="outline"
                onClick={() => void markCalendarDraftStatus(selectedPost, "needs_edit")}
                disabled={schedulingDraftId === selectedPost.id}
              >
                Needs edit
              </Button>
            )}
            {selectedPostIsCalendar && selectedPost && draftStatus(selectedPost) !== "rejected" && (
              <Button
                variant="outline"
                onClick={() => void markCalendarDraftStatus(selectedPost, "rejected")}
                disabled={schedulingDraftId === selectedPost.id}
              >
                Reject
              </Button>
            )}
            {selectedPostIsCalendar && selectedPost && ["needs_edit", "rejected"].includes(draftStatus(selectedPost)) && (
              <Button
                variant="outline"
                onClick={() => void markCalendarDraftStatus(selectedPost, "draft")}
                disabled={schedulingDraftId === selectedPost.id}
              >
                Return to review
              </Button>
            )}
            {!selectedPostIsCalendar && selectedPostPlatform === "reddit" && (
              <Button
                onClick={() => {
                  setPostingDraftId(selectedPost?.id || null);
                  setShowPostConfirm(true);
                }}
              >
                Post to Reddit
              </Button>
            )}
          </div>
        }
      >
        {selectedPost && (
          <div className="space-y-4">
            {selectedPostIsCalendar && (
              <div className="flex flex-wrap items-center gap-2 rounded-lg border bg-muted/30 p-3">
                <PlatformIcon platform={selectedPostPlatform} />
                <Badge variant="secondary">{selectedPostPlatform === "linkedin" ? "LinkedIn" : "X / Twitter"}</Badge>
                <StatusBadge variant={calendarStatusVariant(draftStatus(selectedPost))}>
                  {calendarStatusLabel(draftStatus(selectedPost))}
                </StatusBadge>
                <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                  <Clock3 className="h-3 w-3" />
                  {formatTime(selectedPost.scheduled_at)}
                </span>
              </div>
            )}
            {selectedPostQuality && (
              <div className="rounded-lg border bg-muted/30 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <BarChart3 className="h-4 w-4 text-primary" />
                    <p className="text-sm font-medium">Post quality</p>
                  </div>
                  <Badge variant="outline" className={qualityBadgeClass(selectedPostQuality.level)}>
                    {selectedPostQuality.label} - {selectedPostQuality.score}/100
                  </Badge>
                </div>
                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                  <div>
                    <p className="text-xs font-medium text-muted-foreground">Strengths</p>
                    <ul className="mt-1 space-y-1 text-xs text-muted-foreground">
                      {(selectedPostQuality.strengths.length ? selectedPostQuality.strengths : ["Clear enough for review."]).map((item) => (
                        <li key={item}>- {item}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-muted-foreground">Review notes</p>
                    <ul className="mt-1 space-y-1 text-xs text-muted-foreground">
                      {(selectedPostQuality.warnings.length ? selectedPostQuality.warnings : ["No major risk detected."]).map((item) => (
                        <li key={item} className="flex gap-1.5">
                          {selectedPostQuality.warnings.length > 0 && <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0 text-amber-400" />}
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            )}
            {selectedPostIsCalendar && (
              <div className="rounded-lg border bg-muted/30 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <PenLine className="h-4 w-4 text-primary" />
                    <p className="text-sm font-medium">AI rewrite assist</p>
                  </div>
                  <Badge variant="outline">Edit before saving</Badge>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {([
                    ["shorter", "Make shorter"],
                    ["professional", "More professional"],
                    ["less_salesy", "Less salesy"],
                    ["stronger_hook", "Stronger hook"],
                  ] as Array<[PostRewritePreset, string]>).map(([preset, label]) => (
                    <Button
                      key={preset}
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => applyPostRewrite(preset)}
                    >
                      <RefreshCw className="h-3.5 w-3.5" />
                      {label}
                    </Button>
                  ))}
                </div>
              </div>
            )}
            <div className="space-y-2">
              <Label>Title</Label>
              <Input
                type="text"
                value={postTitle}
                onChange={(event) => setPostTitle(event.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label>Post Body</Label>
              <Textarea
                rows={14}
                value={postBody}
                onChange={(event) => setPostBody(event.target.value)}
                className="text-sm leading-relaxed"
              />
              <p className="text-xs text-muted-foreground">{postBody.length} characters</p>
            </div>
            {selectedPostIsCalendar && (
              <div className="space-y-2">
                <Label>Review note</Label>
                <Textarea
                  rows={4}
                  value={postReviewNote}
                  onChange={(event) => setPostReviewNote(event.target.value)}
                  placeholder="Add the reason for approval, edits needed, or rejection."
                  className="text-sm leading-relaxed"
                />
              </div>
            )}
            {selectedPostIsCalendar && (
              <div className="space-y-3 rounded-lg border bg-muted/30 p-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <Label>Media plan</Label>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Add creative direction, asset notes, or a handoff brief for the post.
                    </p>
                  </div>
                  {postMediaBrief.trim() && <Badge variant="secondary">Media planned</Badge>}
                </div>
                <Textarea
                  rows={5}
                  value={postMediaBrief}
                  onChange={(event) => setPostMediaBrief(event.target.value)}
                  placeholder="Example: Use a clean Gurgaon property tour visual, show verified listing proof, keep copy premium and trust-focused."
                  className="text-sm leading-relaxed"
                />
                <div className="rounded-lg border border-dashed bg-background p-3">
                  <div className="mb-2 flex items-center gap-2">
                    <UploadCloud className="h-4 w-4 text-primary" />
                    <p className="text-sm font-medium">Attach planning file</p>
                    {uploadingCalendarAsset && <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />}
                  </div>
                  <Input
                    type="file"
                    accept=".pdf,.csv,.tsv,.xlsx,.xls,.xlsm,.txt,.md"
                    disabled={uploadingCalendarAsset}
                    onChange={(event) => {
                      const input = event.currentTarget;
                      const file = input.files?.[0] ?? null;
                      void uploadCalendarAsset(file).finally(() => {
                        input.value = "";
                      });
                    }}
                  />
                  <p className="mt-2 text-xs text-muted-foreground">
                    PDF, CSV, Excel, TXT, and MD files are supported for planning context.
                  </p>
                </div>
              </div>
            )}
            {((selectedPostIsCalendar && postReviewNote) || (!selectedPostIsCalendar && selectedPost.rationale)) && (
              <div className="rounded-xl bg-muted p-5">
                <h4 className="text-sm font-medium">Why this post works</h4>
                <p className="mt-1 text-sm text-muted-foreground">
                  {selectedPostIsCalendar ? postReviewNote : selectedPost.rationale || "Educational, useful, and structured for community-native publishing."}
                </p>
              </div>
            )}
          </div>
        )}
      </SheetPanel>

      {/* Post to Reddit Confirm Dialog */}
      <Dialog open={showPostConfirm} onOpenChange={(open) => !open && closePostConfirm()}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Post to Reddit</DialogTitle>
            <DialogDescription>Review your post before publishing to Reddit.</DialogDescription>
          </DialogHeader>
          {postingDraftId && postDrafts.find((d) => d.id === postingDraftId) && (
            <div className="space-y-4">
              <div className="rounded-xl bg-muted p-5">
                <strong className="block mb-2">
                  {postDrafts.find((d) => d.id === postingDraftId)?.title}
                </strong>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {postDrafts.find((d) => d.id === postingDraftId)?.body.substring(0, 200)}...
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="post-subreddit">Target Subreddit</Label>
                <Input
                  id="post-subreddit"
                  type="text"
                  placeholder="e.g., r/community"
                  value={postSubreddit}
                  onChange={(event) => setPostSubreddit(event.target.value)}
                />
              </div>
              <div className="rounded-lg bg-muted p-3">
                <Label>Connected Reddit Account</Label>
                <p className="mt-1.5 text-sm">
                  {redditAccounts.length > 0
                    ? `@${redditAccounts[0].username}`
                    : <a href="/app/settings" className="text-primary hover:underline">Connect Reddit Account</a>}
                </p>
              </div>
              {safetyBlock && (
                <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/10 p-3">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
                  <p className="text-xs leading-relaxed text-destructive">{safetyBlock}</p>
                </div>
              )}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={closePostConfirm}>
              Cancel
            </Button>
            {safetyBlock ? (
              <Button
                variant="destructive"
                disabled={postingReddit}
                onClick={() => void postToReddit(postingDraftId!, true)}
              >
                {postingReddit && <Loader2 className="h-4 w-4 animate-spin" />}
                Post anyway (override)
              </Button>
            ) : (
              <Button
                disabled={postingReddit || redditAccounts.length === 0 || postSubreddit.trim().length < 2}
                onClick={() => void postToReddit(postingDraftId!)}
              >
                {postingReddit && <Loader2 className="h-4 w-4 animate-spin" />}
                Post Now
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Create Tracked Link Dialog */}
      <Dialog
        open={!!linkDraft}
        onOpenChange={(open) => {
          if (!open) {
            setLinkDraft(null);
            setLinkDestination("");
          }
        }}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Create tracked link</DialogTitle>
            <DialogDescription>
              Generates a short URL that attributes clicks back to this reply. Adding it to your reply is
              opt-in — Redditors distrust obvious trackers, so only include it where a link genuinely helps.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <Label htmlFor="link-destination">Destination URL</Label>
            <Input
              id="link-destination"
              type="url"
              placeholder="https://yoursite.com/pricing"
              value={linkDestination}
              onChange={(event) => setLinkDestination(event.target.value)}
            />
            {linkDraft?.opportunity_title && (
              <p className="text-xs text-muted-foreground truncate">
                Attributed to: {linkDraft.opportunity_title}
              </p>
            )}
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setLinkDraft(null);
                setLinkDestination("");
              }}
            >
              Cancel
            </Button>
            <Button
              disabled={creatingLink || linkDestination.trim().length === 0}
              onClick={() => void handleCreateTrackedLink()}
            >
              {creatingLink && <Loader2 className="h-4 w-4 animate-spin" />}
              <Link2 className="h-3.5 w-3.5" /> Create &amp; copy short URL
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
