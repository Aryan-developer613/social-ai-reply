import { apiRequest } from "../api";
import type { SecretRecord } from "../api";

export type { SecretRecord };

export async function getSecrets(token: string) {
  return apiRequest<SecretRecord[]>(
    `/v1/secrets`, { headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function createSecret(token: string, data: { provider: string; label: string; secret_value: string }) {
  return apiRequest<SecretRecord>(
    `/v1/secrets`,
    { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(data) }
  );
}

export async function deleteSecret(token: string, secretId: number) {
  return apiRequest<void>(
    `/v1/secrets/${secretId}`, { method: "DELETE", headers: { Authorization: `Bearer ${token}` } }
  );
}
