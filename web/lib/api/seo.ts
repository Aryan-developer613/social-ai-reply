import { apiRequest } from "../api";

export interface SeoIssue {
  id: number;
  title: string;
  body: string | null;
  platform: string;
  opportunity_type: string;
  score: number;
  status: string;
  subreddit_name: string | null;
  created_at: string;
}

export interface SeoAuditResult {
  last_run: {
    id: number;
    status: string;
    started_at: string;
    finished_at: string | null;
    items_fetched: number;
    items_kept: number;
    items_rejected: number;
  } | null;
  issues: SeoIssue[];
  issue_count: number;
}

export async function getSeoAudit(token: string, companyId: number, limit = 50, offset = 0) {
  return apiRequest<SeoAuditResult>(
    `/v1/seo/audit?company_id=${companyId}&limit=${limit}&offset=${offset}`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function getSeoGaps(token: string, companyId: number, limit = 50, offset = 0) {
  return apiRequest<SeoIssue[]>(
    `/v1/seo/gaps?company_id=${companyId}&limit=${limit}&offset=${offset}`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function runSeoAudit(token: string, companyId: number) {
  return apiRequest<{ status: string; agent: string }>(
    `/v1/seo/run`,
    { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify({ company_id: companyId }) }
  );
}
