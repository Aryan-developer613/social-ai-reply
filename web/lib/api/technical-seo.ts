import { apiRequest } from "../api";

export interface TechnicalSeoIssue {
  id: number;
  title: string;
  body: string | null;
  platform: string;
  opportunity_type: string;
  score: number;
  status: string;
  created_at: string;
}

export interface TechnicalSeoAuditResult {
  last_run: {
    id: number;
    status: string;
    started_at: string;
    finished_at: string | null;
  } | null;
  issues: TechnicalSeoIssue[];
  issue_count: number;
}

export async function getTechnicalSeoAudit(token: string, companyId: number, limit = 50, offset = 0) {
  return apiRequest<TechnicalSeoAuditResult>(
    `/v1/technical-seo/audit?company_id=${companyId}&limit=${limit}&offset=${offset}`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function runTechnicalSeoAudit(token: string, companyId: number) {
  return apiRequest<{ status: string; agent: string }>(
    `/v1/technical-seo/run`,
    { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify({ company_id: companyId }) }
  );
}
