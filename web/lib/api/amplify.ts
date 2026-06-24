import { apiRequest } from "../api";

/** An amplified post draft (X thread or LinkedIn post) generated from a reply or opportunity. */
export type AmplifyDraft = {
  id: number;
  project_id: number;
  platform: "x" | "linkedin" | string;
  thread_json: string[];
  content: string | null;
  status: string;
  source_reply_draft_id: number | null;
  source_opportunity_id: number | null;
  created_at: string;
};

export type AmplifyTarget = "x" | "linkedin";

export type PublishedTweet = {
  id: string;
  text: string;
  url: string;
};

export type AmplifyPublishResult = {
  post_draft_id: number;
  platform: string;
  tweet_ids: string[];
  tweets: PublishedTweet[];
};

export async function createAmplifyDraft(
  token: string,
  data: {
    reply_draft_id?: number;
    opportunity_id?: number;
    target: AmplifyTarget;
    voice_profile_id?: number;
  },
): Promise<AmplifyDraft> {
  return apiRequest<AmplifyDraft>("/v1/amplify", { method: "POST", body: JSON.stringify(data) }, token);
}

export async function updateAmplifyDraft(
  token: string,
  postDraftId: number,
  data: { thread_json?: string[]; content?: string },
): Promise<AmplifyDraft> {
  return apiRequest<AmplifyDraft>(
    `/v1/amplify/${postDraftId}`,
    { method: "PUT", body: JSON.stringify(data) },
    token,
  );
}

/** Publish an X thread. Fails with 400 when no X credentials are configured or for LinkedIn drafts. */
export async function publishAmplifyDraft(token: string, postDraftId: number): Promise<AmplifyPublishResult> {
  return apiRequest<AmplifyPublishResult>(`/v1/amplify/${postDraftId}/publish`, { method: "POST" }, token);
}

/** List all amplified drafts for the active project (Issue #7). */
export async function getAmplifyDrafts(token: string): Promise<AmplifyDraft[]> {
  return apiRequest<AmplifyDraft[]>(`/v1/amplify`, {}, token);
}
