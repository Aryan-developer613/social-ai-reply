import { API_BASE, apiRequest } from "../api";
import { ApiError } from "@/types/errors";

export type FileAnalysisRecord = {
  id: number;
  workspace_id: number;
  project_id?: number | null;
  file_name: string;
  file_type: string;
  storage_path: string;
  analysis_status: string;
  analysis_result?: Record<string, unknown> | null;
  created_at: string;
};

export type FileUploadResponse = {
  file: FileAnalysisRecord;
  analysis: Record<string, unknown>;
};

async function parseUploadError(response: Response): Promise<string> {
  try {
    const payload = await response.json();
    const raw = payload.detail ?? payload.message;
    return typeof raw === "string" ? raw : JSON.stringify(raw);
  } catch {
    return `Request failed: ${response.status}`;
  }
}

export async function uploadAnalysisFile(
  token: string,
  file: File,
  projectId?: number | null,
): Promise<FileUploadResponse> {
  const params = new URLSearchParams({ file_name: file.name });
  if (projectId) {
    params.set("project_id", String(projectId));
  }

  const response = await fetch(`${API_BASE}/v1/files/upload?${params.toString()}`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": file.type || "application/octet-stream",
    },
    body: file,
    cache: "no-store",
  });

  if (!response.ok) {
    const message = await parseUploadError(response);
    throw new ApiError(response.status, message, message);
  }

  return response.json() as Promise<FileUploadResponse>;
}

export async function listAnalysisFiles(token: string, projectId?: number | null): Promise<FileAnalysisRecord[]> {
  const query = projectId ? `?project_id=${projectId}` : "";
  return apiRequest<FileAnalysisRecord[]>(`/v1/files${query}`, {}, token);
}

export async function getFileAnalysisReport(token: string, fileId: number): Promise<string> {
  const response = await fetch(`${API_BASE}/v1/files/${fileId}/report`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });

  if (!response.ok) {
    const message = await parseUploadError(response);
    throw new ApiError(response.status, message, message);
  }

  return response.text();
}
