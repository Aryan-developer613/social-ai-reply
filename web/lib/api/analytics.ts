import { apiRequest } from "../api";

export interface ActivityItem {
  id: number;
  action: string;
  entity_type: string | null;
  entity_id: number | null;
  metadata: Record<string, unknown>;
  created_at: string | null;
}

export async function getActivity(token: string) {
  return apiRequest<{ items: ActivityItem[] }>(
    `/v1/activity`, { headers: { Authorization: `Bearer ${token}` } }
  );
}

// Analytics, campaigns domain functions.
// Add analytics and campaign API functions here as they are implemented.
