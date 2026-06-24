import { create } from "zustand";

const SIDEBAR_WIDTH_KEY = "rf-sidebar-width";
const SIDEBAR_COLLAPSED_KEY = "rf-sidebar-collapsed";
const SIDEBAR_SECTIONS_KEY = "rf-collapsed-sections";

const DEFAULT_WIDTH = 224;
const MIN_WIDTH = 224;
const MAX_WIDTH = 380;
const COLLAPSED_WIDTH = 64;

function loadSidebarWidth(): number {
  if (typeof window === "undefined") return DEFAULT_WIDTH;
  const stored = localStorage.getItem(SIDEBAR_WIDTH_KEY);
  if (stored) {
    const n = Number(stored);
    if (Number.isFinite(n) && n >= MIN_WIDTH && n <= MAX_WIDTH) return n;
  }
  return DEFAULT_WIDTH;
}

function loadSidebarCollapsed(): boolean {
  if (typeof window === "undefined") return false;
  return localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === "1";
}

function loadCollapsedSections(): Set<string> {
  if (typeof window === "undefined") return new Set();
  const stored = localStorage.getItem(SIDEBAR_SECTIONS_KEY);
  if (stored) {
    try {
      return new Set(JSON.parse(stored) as string[]);
    } catch {
      // ignore
    }
  }
  return new Set();
}

function saveCollapsedSections(sections: Set<string>) {
  if (typeof window === "undefined") return;
  localStorage.setItem(SIDEBAR_SECTIONS_KEY, JSON.stringify([...sections]));
}

interface UIState {
  sidebarOpen: boolean;
  notifPanelOpen: boolean;
  sidebarCollapsed: boolean;
  sidebarWidth: number;
  collapsedSections: Set<string>;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  setNotifPanelOpen: (open: boolean) => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  toggleSidebarCollapsed: () => void;
  setSidebarWidth: (width: number) => void;
  toggleSection: (section: string) => void;
  resetTransient: () => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: false,
  notifPanelOpen: false,
  sidebarCollapsed: loadSidebarCollapsed(),
  sidebarWidth: loadSidebarWidth(),
  collapsedSections: loadCollapsedSections(),
  toggleSidebar() {
    set((s) => ({ sidebarOpen: !s.sidebarOpen }));
  },
  setSidebarOpen(open) {
    set({ sidebarOpen: open });
  },
  setNotifPanelOpen(open) {
    set({ notifPanelOpen: open });
  },
  setSidebarCollapsed(collapsed) {
    if (typeof window !== "undefined") {
      localStorage.setItem(SIDEBAR_COLLAPSED_KEY, collapsed ? "1" : "0");
    }
    set({ sidebarCollapsed: collapsed });
  },
  toggleSidebarCollapsed() {
    set((s) => {
      const next = !s.sidebarCollapsed;
      if (typeof window !== "undefined") {
        localStorage.setItem(SIDEBAR_COLLAPSED_KEY, next ? "1" : "0");
      }
      return { sidebarCollapsed: next };
    });
  },
  setSidebarWidth(width) {
    if (typeof window !== "undefined") {
      localStorage.setItem(SIDEBAR_WIDTH_KEY, String(width));
    }
    set({ sidebarWidth: width });
  },
  toggleSection(section) {
    set((s) => {
      const next = new Set(s.collapsedSections);
      if (next.has(section)) {
        next.delete(section);
      } else {
        next.add(section);
      }
      saveCollapsedSections(next);
      return { collapsedSections: next };
    });
  },
  resetTransient() {
    // Reset transient UI state on logout (Issue #58).
    set({ sidebarOpen: false, notifPanelOpen: false });
  },
}));

export { COLLAPSED_WIDTH, MIN_WIDTH, MAX_WIDTH };
