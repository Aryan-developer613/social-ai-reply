"use client";

import { type ReactNode } from "react";
import { CheckCircle2, Circle, ChevronDown, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import type { StepId, StepStatus } from "@/stores/workflow-store";

interface WorkflowNodeProps {
  stepId: StepId;
  index: number;
  label: string;
  description: string;
  status: StepStatus;
  isActive: boolean;
  isLast: boolean;
  onToggle: () => void;
  children: ReactNode;
  summary?: ReactNode;
}

const STATUS_RING: Record<StepStatus, string> = {
  empty:   "border-border bg-card text-muted-foreground",
  partial: "border-yellow-500/60 bg-yellow-500/10 text-yellow-600 dark:text-yellow-400",
  done:    "border-primary bg-primary/10 text-primary",
};

const STATUS_DOT: Record<StepStatus, ReactNode> = {
  empty:   <Circle className="h-3.5 w-3.5" />,
  partial: <Circle className="h-3.5 w-3.5 fill-yellow-500 text-yellow-500" />,
  done:    <CheckCircle2 className="h-3.5 w-3.5 fill-primary text-primary-foreground" />,
};

export function WorkflowNode({
  index,
  label,
  description,
  status,
  isActive,
  isLast,
  onToggle,
  children,
  summary,
}: WorkflowNodeProps) {
  return (
    <div className="flex gap-4">
      {/* Left rail */}
      <div className="flex flex-col items-center shrink-0 pt-3">
        <button
          onClick={onToggle}
          className={cn(
            "h-8 w-8 rounded-full border-2 flex items-center justify-center text-xs font-bold transition-all shrink-0",
            isActive
              ? "border-primary bg-primary text-primary-foreground shadow-sm shadow-primary/25"
              : STATUS_RING[status]
          )}
          aria-label={`Step ${index + 1}: ${label}`}
        >
          {status === "done" && !isActive ? (
            <CheckCircle2 className="h-4 w-4" />
          ) : (
            index + 1
          )}
        </button>
        {!isLast && (
          <div
            className={cn(
              "w-0.5 flex-1 mt-1 transition-colors",
              status === "done" ? "bg-primary/30" : "bg-border"
            )}
            style={{ minHeight: "24px" }}
          />
        )}
      </div>

      {/* Right panel */}
      <div className="flex-1 min-w-0 pb-6">
        {/* Header */}
        <button
          onClick={onToggle}
          className="w-full text-left group flex items-start justify-between gap-2 pb-3 pt-2"
        >
          <div className="min-w-0">
            <div className="flex items-center gap-2 mb-0.5">
              <span
                className={cn(
                  "text-sm font-semibold",
                  isActive ? "text-foreground" : "text-foreground/80"
                )}
              >
                {label}
              </span>
              {status !== "empty" && (
                <span className="shrink-0">{STATUS_DOT[status]}</span>
              )}
            </div>
            {!isActive && summary ? (
              <div className="text-xs text-muted-foreground">{summary}</div>
            ) : (
              <p className="text-xs text-muted-foreground">{description}</p>
            )}
          </div>
          <div className="shrink-0 mt-1 text-muted-foreground group-hover:text-foreground transition-colors">
            {isActive ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </div>
        </button>

        {/* Content */}
        {isActive && (
          <div
            className={cn(
              "rounded-xl border bg-card/50 p-5 transition-all",
              "border-primary/20 shadow-sm"
            )}
          >
            {children}
          </div>
        )}
      </div>
    </div>
  );
}
