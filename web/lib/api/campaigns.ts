import { apiRequest } from "../api";

export interface Campaign {
  id: number;
  workspace_id: number;
  project_id: number | null;
  name: string;
  status: string;
  start_date: string | null;
  end_date: string | null;
  created_at: string;
  updated_at: string;
}

export async function getCampaigns(token: string, projectId?: number) {
  const params = projectId ? `?project_id=${projectId}` : "";
  return apiRequest<Campaign[]>(
    `/v1/campaigns${params}`, { headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function getCampaign(token: string, campaignId: number) {
  return apiRequest<Campaign>(
    `/v1/campaigns/${campaignId}`, { headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function createCampaign(token: string, data: { name: string; project_id?: number }) {
  return apiRequest<Campaign>(
    `/v1/campaigns`,
    { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(data) }
  );
}

export async function updateCampaign(token: string, campaignId: number, data: Partial<Campaign>) {
  return apiRequest<Campaign>(
    `/v1/campaigns/${campaignId}`,
    { method: "PUT", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(data) }
  );
}

export async function deleteCampaign(token: string, campaignId: number) {
  return apiRequest<void>(
    `/v1/campaigns/${campaignId}`, { method: "DELETE", headers: { Authorization: `Bearer ${token}` } }
  );
}
