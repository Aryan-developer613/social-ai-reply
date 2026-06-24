import { apiRequest } from "../api";

export interface AnalyticsV2Summary {
  total_opportunities: number;
  total_drafts: number;
  total_published: number;
  avg_score: number;
  by_platform: Record<string, number>;
  by_status: Record<string, number>;
}

export interface ROIReport {
  total_clicks: number;
  total_links: number;
  top_links: Array<{
    id: number;
    code: string;
    destination_url: string;
    clicks: number;
    label: string | null;
  }>;
}

export async function getAnalyticsV2(token: string, companyId?: number) {
  const params = companyId ? `?company_id=${companyId}` : "";
  return apiRequest<AnalyticsV2Summary>(
    `/v1/analytics/v2${params}`, { headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function getROIReport(token: string) {
  return apiRequest<ROIReport>(
    `/v1/analytics/roi`, { headers: { Authorization: `Bearer ${token}` } }
  );
}
