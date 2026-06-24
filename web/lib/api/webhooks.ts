import { apiRequest } from "../api";
import type { WebhookEndpoint } from "../api";

export type { WebhookEndpoint };

export async function getWebhooks(token: string) {
  return apiRequest<WebhookEndpoint[]>(
    `/v1/webhooks`, { headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function createWebhook(token: string, data: { target_url: string; event_types: string[]; is_active?: boolean }) {
  return apiRequest<WebhookEndpoint>(
    `/v1/webhooks`,
    { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(data) }
  );
}

export async function updateWebhook(token: string, webhookId: number, data: Partial<WebhookEndpoint>) {
  return apiRequest<WebhookEndpoint>(
    `/v1/webhooks/${webhookId}`,
    { method: "PATCH", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(data) }
  );
}

export async function deleteWebhook(token: string, webhookId: number) {
  return apiRequest<{ ok: boolean }>(
    `/v1/webhooks/${webhookId}`, { method: "DELETE", headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function testWebhook(token: string, webhookId: number, data?: { payload?: Record<string, unknown> }) {
  return apiRequest<{ status: string; response_code: number }>(
    `/v1/webhooks/${webhookId}/test`,
    { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(data ?? {}) }
  );
}
