"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Zap, CheckCircle2 } from "lucide-react";

import { useAuth } from "@/components/auth/auth-provider";
import { useSelectedProjectId } from "@/hooks/use-selected-project";
import { useWorkflowStore, STEP_ORDER, STEP_META, type StepId, type StepStatus } from "@/stores/workflow-store";
import { WorkflowNode } from "@/components/workflow/workflow-node";
import { StepCompany } from "@/components/workflow/steps/step-company";
import { StepBrand } from "@/components/workflow/steps/step-brand";
import { StepPersonas } from "@/components/workflow/steps/step-personas";
import { StepCommunities } from "@/components/workflow/steps/step-communities";
import { StepCompetitors } from "@/components/workflow/steps/step-competitors";
import { StepLaunch } from "@/components/workflow/steps/step-launch";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { startPipelineRun, getPipelineRun } from "@/lib/api/pipeline";
import { useToast } from "@/stores/toast";

export default function WorkflowPage() {
  const { token } = useAuth();
  const router = useRouter();
  const toast = useToast();
  const selectedProjectId = useSelectedProjectId();

  const { activeStep, statuses, toggleStep, openStep, setStatus } = useWorkflowStore();

  // Human-readable summaries for collapsed step headers
  const [summaries, setSummaries] = useState<Record<StepId, string>>({
    company:     "Not configured",
    brand:       "No keywords",
    personas:    "None yet",
    communities: "None yet",
    competitors: "No data yet",
    launch:      "Ready to scan",
  });

  // Quick-launch pipeline
  const [quickUrl, setQuickUrl] = useState("");
  const [quickRunning, setQuickRunning] = useState(false);
  const [quickProgress, setQuickProgress] = useState(0);

  function updateSummary(id: StepId, summary: string) {
    setSummaries((prev) => ({ ...prev, [id]: summary }));
  }

  function advanceTo(id: StepId) {
    const idx = STEP_ORDER.indexOf(id);
    const next = STEP_ORDER[idx + 1];
    if (next) openStep(next);
  }

  const readiness = [
    { label: "Company Setup",  ok: statuses.company     !== "empty", href: "#" },
    { label: "Brand Keywords", ok: statuses.brand        !== "empty", href: "#" },
    { label: "Personas",       ok: statuses.personas     !== "empty", href: "#" },
    { label: "Communities",    ok: statuses.communities  !== "empty", href: "#" },
    { label: "Competitor Intel",ok: statuses.competitors !== "empty", href: "#" },
  ];
  const doneCount = readiness.filter((r) => r.ok).length;

  async function runQuickPipeline() {
    if (!quickUrl.trim() || !token) return;
    setQuickRunning(true);
    setQuickProgress(5);
    try {
      let url = quickUrl.trim();
      if (!/^https?:\/\//i.test(url)) url = `https://${url}`;
      const run = await startPipelineRun(token, url, selectedProjectId, "week");
      const iv = setInterval(async () => {
        try {
          const updated = await getPipelineRun(token, run.id);
          setQuickProgress(updated.progress ?? 0);
          if (updated.status === "ready" || updated.status === "executed" || updated.status === "failed") {
            clearInterval(iv);
            setQuickRunning(false);
            if (updated.status === "failed") {
              toast.error("Pipeline failed", updated.error_message ?? "Unknown error");
            } else {
              toast.success("Pipeline complete!", `${updated.drafts_count} draft replies ready.`);
              router.push(`/app/content?project_id=${updated.project_id}`);
            }
          }
        } catch { /* ignore */ }
      }, 2000);
    } catch (err) {
      toast.error("Failed to launch", err instanceof Error ? err.message : "Unknown error");
      setQuickRunning(false);
    }
  }

  if (!token) {
    return (
      <div className="flex items-center justify-center py-20 text-muted-foreground text-sm">
        <Loader2 className="h-4 w-4 animate-spin mr-2" />
        Loading…
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Pipeline Setup</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Configure your brand once — then scan social for opportunities on demand.
        </p>
      </div>

      {/* Quick-launch panel */}
      <div className="rounded-xl border bg-card p-5 space-y-4">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
            <Zap className="h-4 w-4 text-primary" />
          </div>
          <div>
            <p className="text-sm font-semibold">Full Auto-Pilot</p>
            <p className="text-xs text-muted-foreground">
              Drop a URL — we'll analyze, build keywords, discover communities, and generate reply drafts
            </p>
          </div>
        </div>

        <div className="flex gap-2">
          <Input
            value={quickUrl}
            onChange={(e) => setQuickUrl(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && void runQuickPipeline()}
            placeholder="https://yourproduct.com"
            className="flex-1 h-10"
            disabled={quickRunning}
          />
          <Button onClick={runQuickPipeline} disabled={quickRunning || !quickUrl.trim()} className="shrink-0">
            {quickRunning ? (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" />
                {quickProgress > 0 ? `${quickProgress}%` : "Running…"}
              </>
            ) : (
              <>
                <Zap className="h-3.5 w-3.5 mr-1" />
                Launch
              </>
            )}
          </Button>
        </div>

        {quickRunning && (
          <div className="h-1 bg-muted rounded-full overflow-hidden">
            <div
              className="h-full bg-primary transition-all duration-500 rounded-full"
              style={{ width: `${quickProgress}%` }}
            />
          </div>
        )}

        {/* Pipeline health dots */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            {readiness.map((item) => (
              <div
                key={item.label}
                title={`${item.label}: ${item.ok ? "configured" : "not set up"}`}
                className={cn(
                  "h-1.5 w-8 rounded-full transition-colors",
                  item.ok ? "bg-primary" : "bg-muted"
                )}
              />
            ))}
          </div>
          <span className="text-xs text-muted-foreground">
            {doneCount}/{readiness.length} configured
            {doneCount === readiness.length && (
              <span className="ml-1.5 text-primary inline-flex items-center gap-0.5">
                <CheckCircle2 className="h-3 w-3" /> Ready
              </span>
            )}
          </span>
        </div>
      </div>

      {/* Divider */}
      <div className="flex items-center gap-3">
        <div className="flex-1 h-px bg-border" />
        <span className="text-xs text-muted-foreground uppercase tracking-wider">or configure step by step</span>
        <div className="flex-1 h-px bg-border" />
      </div>

      {/* Step-by-step tree */}
      <div>
        {STEP_ORDER.map((stepId, index) => {
          const meta = STEP_META[stepId];
          const status = statuses[stepId];
          const summary = summaries[stepId];

          return (
            <WorkflowNode
              key={stepId}
              stepId={stepId}
              index={index}
              label={meta.label}
              description={meta.description}
              status={status}
              isActive={activeStep === stepId}
              isLast={index === STEP_ORDER.length - 1}
              onToggle={() => toggleStep(stepId)}
              summary={<span className="text-xs">{summary}</span>}
            >
              {stepId === "company" && (
                <StepCompany
                  token={token}
                  onStatusChange={(s) => setStatus("company", s)}
                  onSummary={(s) => updateSummary("company", s)}
                  onContinue={() => advanceTo("company")}
                />
              )}

              {stepId === "brand" && (
                <StepBrand
                  token={token}
                  projectId={selectedProjectId}
                  onStatusChange={(s) => setStatus("brand", s)}
                  onSummary={(s) => updateSummary("brand", s)}
                  onContinue={() => advanceTo("brand")}
                />
              )}

              {stepId === "personas" && (
                <StepPersonas
                  token={token}
                  projectId={selectedProjectId}
                  onStatusChange={(s) => setStatus("personas", s)}
                  onSummary={(s) => updateSummary("personas", s)}
                  onContinue={() => advanceTo("personas")}
                />
              )}

              {stepId === "communities" && (
                <StepCommunities
                  token={token}
                  projectId={selectedProjectId}
                  onStatusChange={(s) => setStatus("communities", s)}
                  onSummary={(s) => updateSummary("communities", s)}
                  onContinue={() => advanceTo("communities")}
                />
              )}

              {stepId === "competitors" && (
                <StepCompetitors
                  token={token}
                  projectId={selectedProjectId}
                  onStatusChange={(s) => setStatus("competitors", s)}
                  onContinue={() => advanceTo("competitors")}
                />
              )}

              {stepId === "launch" && (
                <StepLaunch
                  token={token}
                  projectId={selectedProjectId}
                  readiness={readiness}
                  onStatusChange={(s) => {
                    setStatus("launch", s);
                    if (s === "done") updateSummary("launch", "Scan complete");
                  }}
                />
              )}
            </WorkflowNode>
          );
        })}
      </div>
    </div>
  );
}
