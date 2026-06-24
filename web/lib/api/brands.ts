import { apiRequest } from "../api";
import type { BrandProfile } from "../api";

export type { BrandProfile };

export async function getBrandProfile(token: string, projectId: number) {
  return apiRequest<BrandProfile>(
    `/v1/brand/${projectId}`, { headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function updateBrandProfile(token: string, projectId: number, data: Partial<BrandProfile>) {
  return apiRequest<BrandProfile>(
    `/v1/brand/${projectId}`,
    { method: "PUT", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(data) }
  );
}

export async function analyzeBrandWebsite(token: string, projectId: number, websiteUrl: string) {
  return apiRequest<{ status: string; agent: string; message: string }>(
    `/v1/brand/${projectId}/analyze`,
    { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify({ website_url: websiteUrl }) }
  );
}
