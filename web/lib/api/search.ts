import { apiRequest } from "../api";

export type SearchProvider = "web" | "reddit" | "x";

export type SearchCitation = {
  title: string;
  url: string;
  snippet?: string | null;
};

export type SearchItem = {
  title: string;
  url: string;
  source: string;
  snippet?: string | null;
  author?: string | null;
  score?: number | null;
  comments_count?: number | null;
  created_at?: string | null;
  raw?: Record<string, unknown>;
};

export type SearchResponse = {
  provider: string;
  query: string;
  cache_key: string;
  cached: boolean;
  results: SearchItem[];
  citations: SearchCitation[];
};

export type EnhancedSearchPayload = {
  query: string;
  project_id?: number | null;
  limit?: number;
  use_cache?: boolean;
  subreddits?: string[];
};

export async function runEnhancedSearch(
  token: string,
  provider: SearchProvider,
  payload: EnhancedSearchPayload,
): Promise<SearchResponse> {
  return apiRequest<SearchResponse>(
    `/v1/search/${provider}`,
    {
      method: "POST",
      body: JSON.stringify({
        ...payload,
        limit: payload.limit ?? 8,
        use_cache: payload.use_cache ?? true,
      }),
    },
    token,
  );
}
