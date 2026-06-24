import { apiRequest } from "../api";

export interface ManualImport {
  id: number;
  company_id: number;
  platform: string;
  source_name: string;
  source_url: string | null;
  content: string;
  author: string | null;
  created_at: string;
}

export async function getManualImports(token: string, companyId: number) {
  return apiRequest<ManualImport[]>(
    `/v1/manual-import?company_id=${companyId}`, { headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function importXPost(token: string, data: { company_id: number; url: string; content?: string }) {
  return apiRequest<ManualImport>(
    `/v1/manual-import/x`,
    { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(data) }
  );
}

export async function importLinkedInPost(token: string, data: { company_id: number; url: string; content?: string }) {
  return apiRequest<ManualImport>(
    `/v1/manual-import/linkedin`,
    { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(data) }
  );
}
