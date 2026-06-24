import { apiRequest } from "../api";

export interface ArticleBrief {
  id: number;
  title: string;
  body: string | null;
  platform: string;
  opportunity_type: string;
  score: number;
  status: string;
  draft_article: string | null;
  created_at: string;
}

export async function getArticleBriefs(token: string, companyId: number, limit = 50, offset = 0) {
  return apiRequest<ArticleBrief[]>(
    `/v1/articles?company_id=${companyId}&limit=${limit}&offset=${offset}`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function runArticlesAgent(token: string, companyId: number) {
  return apiRequest<{ status: string; agent: string }>(
    `/v1/articles/run`,
    { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify({ company_id: companyId }) }
  );
}

export async function exportArticle(token: string, opportunityId: number) {
  return apiRequest<{ markdown: string }>(
    `/v1/articles/${opportunityId}/export`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function regenerateArticle(token: string, opportunityId: number) {
  return apiRequest<{ status: string; brief: string }>(
    `/v1/articles/${opportunityId}/regenerate`,
    { method: "POST", headers: { Authorization: `Bearer ${token}` } }
  );
}
