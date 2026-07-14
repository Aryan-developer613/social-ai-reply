import { apiRequest } from "../api";

import type { ReplyDraft, PostDraft, PromptTemplate } from "../api";

export type { ReplyDraft, PostDraft, PromptTemplate };

export async function generateReply(
  token: string,
  opportunityId: number,
  projectId?: number | null,
  promptTemplateId?: number | null,
  options?: {
    voice_profile_id?: number | null;
    platform?: string | null;
    variants?: number;
    style_preset?: "shorter" | "more_helpful" | "more_professional" | "less_promotional" | null;
  }
) {
  const body: Record<string, unknown> = { opportunity_id: opportunityId };
  if (promptTemplateId) body.prompt_template_id = promptTemplateId;
  if (options?.voice_profile_id) body.voice_profile_id = options.voice_profile_id;
  if (options?.platform) body.platform = options.platform;
  if (options?.style_preset) body.style_preset = options.style_preset;
  if (options?.variants && options.variants > 1) body.variants = options.variants;
  const qs = projectId ? `?project_id=${projectId}` : "";
  return apiRequest<ReplyDraft>(
    `/v1/drafts/replies${qs}`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(body) }
  );
}

export async function getReplyDrafts(token: string, projectId?: number | null, status?: string) {
  const params = new URLSearchParams();
  if (projectId) params.set("project_id", String(projectId));
  if (status) params.set("status", status);
  const qs = params.toString() ? `?${params.toString()}` : "";
  return apiRequest<ReplyDraft[]>(
    `/v1/drafts/replies${qs}`, { headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function updateReplyDraft(
  token: string,
  draftId: number,
  data: { content: string; rationale?: string | null }
) {
  return apiRequest<ReplyDraft>(
    `/v1/drafts/replies/${draftId}`, { method: "PUT", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(data) }
  );
}

export async function updatePostDraft(
  token: string,
  draftId: number,
  data: { title: string; body: string; rationale?: string | null; status?: "draft" | "scheduled" | "needs_edit" | "rejected" | "published" | null }
) {
  return apiRequest<PostDraft>(
    `/v1/drafts/posts/${draftId}`, { method: "PUT", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(data) }
  );
}

export async function createPostDraft(token: string, projectId: number, data?: { title?: string; body?: string; subreddit?: string }) {
  const payload = { project_id: projectId, ...data };
  return apiRequest<PostDraft>(
    `/v1/drafts/posts`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(payload) }
  );
}

export async function createContentPlan(
  token: string,
  data: {
    project_id: number;
    platform: "x" | "twitter" | "linkedin" | "instagram" | "threads" | "facebook";
    horizon_days: number;
    count?: number;
    start_at?: string | null;
    preferred_hour_utc?: number;
    campaign_goal?: "brand_awareness" | "lead_generation" | "product_launch" | "competitor_switch" | "education";
    campaign_brief?: string | null;
    voice_style?: "professional" | "friendly" | "premium" | "witty";
    content_template?: "product_tip" | "comparison" | "founder_story" | "case_study" | "offer_post";
  }
) {
  return apiRequest<PostDraft[]>(
    `/v1/drafts/posts/plan`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(data) }
  );
}

export async function schedulePostDraft(token: string, draftId: number, scheduledAt: string) {
  return apiRequest<PostDraft>(
    `/v1/drafts/posts/${draftId}/schedule`,
    { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify({ scheduled_at: scheduledAt }) }
  );
}

export async function unschedulePostDraft(token: string, draftId: number) {
  return apiRequest<PostDraft>(
    `/v1/drafts/posts/${draftId}/unschedule`,
    { method: "POST", headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function manualPublishPostDraft(
  token: string,
  draftId: number,
  data?: { published_url?: string | null; publish_note?: string | null }
) {
  return apiRequest<PostDraft>(
    `/v1/drafts/posts/${draftId}/manual-publish`,
    { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(data ?? {}) }
  );
}

export async function getPostDrafts(token: string, projectId?: number | null) {
  const qs = projectId ? `?project_id=${projectId}` : "";
  return apiRequest<PostDraft[]>(
    `/v1/drafts/posts${qs}`, { headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function getPrompts(token: string, projectId?: number | null) {
  const suffix = projectId ? `?project_id=${projectId}` : "";
  return apiRequest<PromptTemplate[]>(
    `/v1/prompts${suffix}`, { headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function createPrompt(token: string, data: { prompt_type: string; name: string; system_prompt: string; instructions: string; project_id?: number }) {
  return apiRequest<PromptTemplate>(
    `/v1/prompts`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(data) }
  );
}

export async function updatePrompt(token: string, promptId: number, data: Partial<{ prompt_type: string; name: string; system_prompt: string; instructions: string }>) {
  return apiRequest<PromptTemplate>(
    `/v1/prompts/${promptId}`, { method: "PUT", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(data) }
  );
}

export async function deletePrompt(token: string, promptId: number) {
  return apiRequest<void>(
    `/v1/prompts/${promptId}`, { method: "DELETE", headers: { Authorization: `Bearer ${token}` } }
  );
}
