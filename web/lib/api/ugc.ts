import { apiRequest } from "../api";

export interface UgcBrief {
  id: number;
  title: string;
  body: string | null;
  platform: string;
  opportunity_type: string;
  score: number;
  status: string;
  created_at: string;
}

export async function getUgcBriefs(token: string, companyId: number, limit = 50, offset = 0) {
  return apiRequest<UgcBrief[]>(
    `/v1/ugc?company_id=${companyId}&limit=${limit}&offset=${offset}`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function runUgcAgent(token: string, companyId: number) {
  return apiRequest<{ status: string; agent: string }>(
    `/v1/ugc/run`,
    { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify({ company_id: companyId }) }
  );
}

export async function exportUgc(token: string, opportunityId: number) {
  return apiRequest<{ markdown: string }>(
    `/v1/ugc/${opportunityId}/export`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
}
