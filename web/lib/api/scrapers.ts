import { apiRequest } from "../api";

export interface CustomScraper {
  id: number;
  workspace_id: number;
  platform: string;
  api_host: string;
  search_endpoint: string;
  search_param_name: string;
  comments_endpoint: string | null;
  comments_param_name: string | null;
  items_json_path: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CustomScraperCreateRequest {
  platform: string;
  api_key?: string | null;
  api_host: string;
  search_endpoint: string;
  search_param_name: string;
  comments_endpoint?: string | null;
  comments_param_name?: string | null;
  items_json_path: string;
  is_active?: boolean;
}

export async function getScrapers(token: string): Promise<CustomScraper[]> {
  return apiRequest<CustomScraper[]>("/v1/scrapers", { token });
}

export async function createOrUpdateScraper(
  token: string,
  payload: CustomScraperCreateRequest
): Promise<CustomScraper> {
  return apiRequest<CustomScraper>("/v1/scrapers", {
    method: "POST",
    token,
    body: payload,
  });
}

export async function deleteScraper(token: string, id: number): Promise<void> {
  return apiRequest<void>(`/v1/scrapers/${id}`, {
    method: "DELETE",
    token,
  });
}
