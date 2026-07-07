"use client";

import { useEffect, useState } from "react";
import { MessageSquare } from "lucide-react";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/shared/empty-state";
import { cn } from "@/lib/utils";
import type { Opportunity } from "@/lib/api";

import { OpportunityCard } from "./opportunity-card";

export interface StatusTab {
  label: string;
  value: string;
}

/**
 * Default status tabs. "All" means the active funnel — it excludes "rejected"
 * (a secondary bucket for posts the scoring pipeline found but didn't think
 * were a good fit; users can review them and promote back to "New").
 */
export const DEFAULT_STATUS_TABS: StatusTab[] = [
  { label: "All", value: "" },
  { label: "New", value: "new" },
  { label: "Saved", value: "saved" },
  { label: "Drafting", value: "drafting" },
  { label: "Posted", value: "posted" },
  { label: "Ignored", value: "ignored" },
  { label: "Rejected", value: "rejected" },
];

const DEFAULT_PAGE_SIZE = 20;

interface OpportunityListProps {
  /** Opportunities already filtered by the page (status / search / etc.). */
  opportunities: Opportunity[];
  /** Total number of opportunities before filtering — used for empty-state copy. */
  totalCount: number;
  statusTabs?: StatusTab[];
  statusFilter: string;
  onStatusFilterChange: (value: string) => void;
  generatingReplyId: number | null;
  onGenerateReply: (opportunity: Opportunity) => void;
  /** Optional empty-state action (e.g. "Run Scan"). */
  emptyAction?: { label: string; onClick: () => void };
  pageSize?: number;
}

/** Opportunity queue: status tabs, paginated card list, and empty states. */
export function OpportunityList({
  opportunities,
  totalCount,
  statusTabs = DEFAULT_STATUS_TABS,
  statusFilter,
  onStatusFilterChange,
  generatingReplyId,
  onGenerateReply,
  emptyAction,
  pageSize = DEFAULT_PAGE_SIZE,
}: OpportunityListProps) {
  const [page, setPage] = useState(0);

  const totalPages = Math.max(1, Math.ceil(opportunities.length / pageSize));

  // Reset/clamp pagination when the filtered list shrinks or the filter changes.
  useEffect(() => {
    setPage(0);
  }, [statusFilter]);
  useEffect(() => {
    setPage((current) => Math.min(current, totalPages - 1));
  }, [totalPages]);

  const pageItems = opportunities.slice(page * pageSize, (page + 1) * pageSize);

  return (
    <div className="space-y-4">
      {/* Status Filter Pills */}
      <div className="flex flex-wrap gap-1.5">
        {statusTabs.map((tab) => (
          <button
            key={tab.value}
            type="button"
            onClick={() => onStatusFilterChange(tab.value)}
            className={cn(
              "inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium transition-colors",
              statusFilter === tab.value
                ? "border-primary bg-primary/10 text-primary"
                : "border-transparent bg-muted text-muted-foreground hover:bg-muted/80"
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Opportunity List */}
      {opportunities.length === 0 ? (
        <EmptyState
          icon={MessageSquare}
          title={totalCount === 0 ? "No conversations yet" : "No matches for this filter"}
          description={
            totalCount === 0
              ? "Add signals, find sources, then run a scan to bring conversations here."
              : "Try changing the status filter or search."
          }
          action={emptyAction}
        />
      ) : (
        <>
          <div className="space-y-2">
            {pageItems.map((opp) => (
              <OpportunityCard
                key={opp.id}
                opportunity={opp}
                generating={generatingReplyId === opp.id}
                onGenerateReply={onGenerateReply}
              />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between pt-1">
              <p className="text-xs text-muted-foreground">
                Page {page + 1} of {totalPages} ({opportunities.length} conversations)
              </p>
              <div className="flex items-center gap-2">
                <Button variant="outline" size="sm" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page >= totalPages - 1}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
