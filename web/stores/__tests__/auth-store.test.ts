import { describe, it, expect, beforeEach } from "vitest";
import { useAuthStore, STORAGE_KEY } from "../auth-store";
import { useUIStore } from "../ui-store";
import { setStoredProjectId, getStoredProjectId } from "@/lib/project";

// Regression test for the bug where clearAuth() removed localStorage keys
// that didn't exist ("rf-selected-project", "rf-sidebar-open", ...) instead
// of the real project-id key and ui-store's transient state — so logging out
// never actually cleared the selected project or transient UI state.
describe("auth-store clearAuth", () => {
  beforeEach(() => {
    window.localStorage.clear();
    useAuthStore.setState({ token: "t", user: null, workspace: null, error: null, loading: false });
    useUIStore.setState({ sidebarOpen: true, notifPanelOpen: true });
  });

  it("clears the real stored project id", () => {
    setStoredProjectId(42);
    expect(getStoredProjectId()).toBe(42);

    useAuthStore.getState().clearAuth();

    expect(getStoredProjectId()).toBeNull();
  });

  it("resets transient UI state (sidebar/notif panel open)", () => {
    expect(useUIStore.getState().sidebarOpen).toBe(true);
    expect(useUIStore.getState().notifPanelOpen).toBe(true);

    useAuthStore.getState().clearAuth();

    expect(useUIStore.getState().sidebarOpen).toBe(false);
    expect(useUIStore.getState().notifPanelOpen).toBe(false);
  });

  it("clears auth token and the auth storage key", () => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ access_token: "t" }));

    useAuthStore.getState().clearAuth();

    expect(useAuthStore.getState().token).toBeNull();
    expect(window.localStorage.getItem(STORAGE_KEY)).toBeNull();
  });
});
