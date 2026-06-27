import { create } from "zustand";

export type StepId =
  | "company"
  | "brand"
  | "personas"
  | "communities"
  | "competitors"
  | "launch";

export type StepStatus = "empty" | "partial" | "done";

interface WorkflowState {
  /** Which step is currently expanded */
  activeStep: StepId | null;
  /** Per-step status derived from API data */
  statuses: Record<StepId, StepStatus>;
  /** Open a specific step */
  openStep: (id: StepId) => void;
  /** Close all steps */
  closeAll: () => void;
  /** Toggle a step open/closed */
  toggleStep: (id: StepId) => void;
  /** Update status after a step saves/loads */
  setStatus: (id: StepId, status: StepStatus) => void;
}

const DEFAULT_STATUSES: Record<StepId, StepStatus> = {
  company: "empty",
  brand: "empty",
  personas: "empty",
  communities: "empty",
  competitors: "empty",
  launch: "empty",
};

export const useWorkflowStore = create<WorkflowState>((set) => ({
  activeStep: "company",
  statuses: { ...DEFAULT_STATUSES },

  openStep(id) {
    set({ activeStep: id });
  },

  closeAll() {
    set({ activeStep: null });
  },

  toggleStep(id) {
    set((s) => ({ activeStep: s.activeStep === id ? null : id }));
  },

  setStatus(id, status) {
    set((s) => ({ statuses: { ...s.statuses, [id]: status } }));
  },
}));

export const STEP_ORDER: StepId[] = [
  "company",
  "brand",
  "personas",
  "communities",
  "competitors",
  "launch",
];

export const STEP_META: Record<StepId, { label: string; description: string }> = {
  company:     { label: "Company Setup",    description: "Name, website, audience, brand voice" },
  brand:       { label: "Brand Keywords",   description: "AI signals that drive scanning" },
  personas:    { label: "Personas",         description: "Buyer archetypes used for relevance scoring" },
  communities: { label: "Communities",      description: "Subreddits and platforms to monitor" },
  competitors: { label: "Competitor Intel", description: "Track competitor mentions and sentiment" },
  launch:      { label: "Launch Scan",      description: "Run the pipeline and review opportunities" },
};
