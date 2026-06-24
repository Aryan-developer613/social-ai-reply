import { apiRequest } from "../api";

export interface GeoGap {
  id: number;
  title: string;
  body: string | null;
  platform: string;
  opportunity_type: string;
  score: number;
  status: string;
  created_at: string;
}

export interface GeoReadiness {
  readiness_score: number;
  gap_count: number;
  last_run: {
    id: number;
    status: string;
    started_at: string;
    finished_at: string | null;
  } | null;
}

export async function getGeoGaps(token: string, companyId: number, limit = 50, offset = 0) {
  return apiRequest<GeoGap[]>(
    `/v1/geo/gaps?company_id=${companyId}&limit=${limit}&offset=${offset}`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function getGeoReadiness(token: string, companyId: number) {
  return apiRequest<GeoReadiness>(
    `/v1/geo/readiness?company_id=${companyId}`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function runGeoAudit(token: string, companyId: number) {
  return apiRequest<{ status: string; agent: string }>(
    `/v1/geo/run`,
    { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify({ company_id: companyId }) }
  );
}
