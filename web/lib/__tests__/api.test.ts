import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { apiRequest, API_BASE } from "../api";
import { useAuthStore } from "@/stores/auth-store";

const refreshSession = vi.fn();

vi.mock("@/lib/supabase", () => ({
  supabase: { auth: { refreshSession: (...args: unknown[]) => refreshSession(...args) } },
}));

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

describe("apiRequest 401-refresh-and-retry flow", () => {
  beforeEach(() => {
    window.localStorage.clear();
    useAuthStore.setState({ token: "old-token", user: null, workspace: null, error: null, loading: false });
    refreshSession.mockReset();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("retries once with the refreshed token and returns the retried response", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(401, { detail: "expired" }))
      .mockResolvedValueOnce(jsonResponse(200, { ok: true }));
    vi.stubGlobal("fetch", fetchMock);

    refreshSession.mockResolvedValue({ data: { session: { access_token: "new-token" } }, error: null });

    const result = await apiRequest<{ ok: boolean }>("/v1/whatever", {}, "old-token");

    expect(result).toEqual({ ok: true });
    expect(fetchMock).toHaveBeenCalledTimes(2);
    const secondCallHeaders = fetchMock.mock.calls[1][1].headers as Headers;
    expect(secondCallHeaders.get("Authorization")).toBe("Bearer new-token");
    // The store is updated with the refreshed token too.
    expect(useAuthStore.getState().token).toBe("new-token");
  });

  it("clears auth and throws when the refresh itself fails", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(401, { detail: "expired" }));
    vi.stubGlobal("fetch", fetchMock);

    refreshSession.mockResolvedValue({ data: { session: null }, error: new Error("refresh failed") });

    await expect(apiRequest("/v1/whatever", {}, "old-token")).rejects.toThrow();

    // Only the original request was attempted — no retry without a fresh token.
    expect(fetchMock).toHaveBeenCalledTimes(1);
    // tryClearAuth() ran: the real auth store's token is now cleared.
    expect(useAuthStore.getState().token).toBeNull();
  });

  it("does not attempt a refresh when no token was supplied", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(401, { detail: "unauthorized" }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(apiRequest("/v1/whatever")).rejects.toThrow();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(refreshSession).not.toHaveBeenCalled();
  });

  it("requests hit the resolved API base", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, { ok: true }));
    vi.stubGlobal("fetch", fetchMock);

    await apiRequest("/v1/whatever", {}, "old-token");

    expect(fetchMock.mock.calls[0][0]).toBe(`${API_BASE}/v1/whatever`);
  });
});
