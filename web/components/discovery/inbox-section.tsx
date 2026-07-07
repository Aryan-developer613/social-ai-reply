"use client";

import { useEffect } from "react";
import { Check, Keyboard, Loader2, MessageSquare, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { EmptyState } from "@/components/shared/empty-state";
import { cn } from "@/lib/utils";
import type { Opportunity } from "@/lib/api";

import { FiltersBar, type FilterConfig } from "./filters-bar";
import { InboxDetailPane } from "./inbox-detail-pane";
import { InboxRow } from "./inbox-row";
import { DEFAULT_STATUS_TABS, type StatusTab } from "./opportunity-list";
import { StageFilterTabs } from "./stage-filter-tabs";

const SHORTCUTS: Array<{ keys: string; action: string }> = [
  { keys: "j / k", action: "Next / previous conversation" },
  { keys: "a", action: "Save selected" },
  { keys: "s", action: "Save selected" },
  { keys: "i", action: "Ignore selected" },
  { keys: "Enter", action: "Create reply draft" },
];

interface InboxSectionProps {
  /** Final visible list: status + search + stage filtered, sorted score desc. */
  opportunities: Opportunity[];
  /** Total loaded opportunities before any filtering — for empty-state copy. */
  totalCount: number;
  statusTabs?: StatusTab[];
  statusFilter: string;
  onStatusFilterChange: (value: string) => void;
  /** Stage → count over the status/search-filtered list (before stage filter). */
  stageCounts: Record<string, number>;
  /** Size of the status/search-filtered list (the "All" chip count). */
  stageTotal: number;
  stageFilter: string;
  onStageFilterChange: (value: string) => void;
  search: { value: string; onChange: (value: string) => void };
  filters?: FilterConfig[];
  highIntentOnly: boolean;
  onHighIntentOnlyChange: (value: boolean) => void;
  showDuplicates: boolean;
  onShowDuplicatesChange: (value: boolean) => void;
  duplicatesHiddenCount: number;
  selectedOpportunity: Opportunity | null;
  onSelect: (id: number) => void;
  checkedIds: ReadonlySet<number>;
  onToggleChecked: (id: number) => void;
  onToggleAllVisible: () => void;
  onBulkApprove: () => void;
  onBulkIgnore: () => void;
  bulkBusy: boolean;
  /** ISO timestamp of the previous visit; rows created after it get a new dot. */
  lastSeenAt: string | null;
  generatingReplyId: number | null;
  updatingStatus: boolean;
  onGenerateReply: (opportunity: Opportunity) => void;
  onApprove: (opportunity: Opportunity) => void;
  onIgnore: (opportunity: Opportunity) => void;
  emptyAction?: { label: string; onClick: () => void };
}

function isNewSince(createdAt: string, lastSeenAt: string | null): boolean {
  if (!lastSeenAt) {
    return false;
  }
  const created = Date.parse(createdAt);
  const seen = Date.parse(lastSeenAt);
  return Number.isFinite(created) && Number.isFinite(seen) && created > seen;
}

/**
 * Email-inbox style triage view: stage/status filters and bulk actions on top,
 * then a two-pane layout — compact selectable rows on the left, detail pane
 * for the selected opportunity on the right. On small screens the panes stack:
 * list first, tapped row's detail below it.
 */
export function InboxSection({
  opportunities,
  totalCount,
  statusTabs = DEFAULT_STATUS_TABS,
  statusFilter,
  onStatusFilterChange,
  stageCounts,
  stageTotal,
  stageFilter,
  onStageFilterChange,
  search,
  filters,
  highIntentOnly,
  onHighIntentOnlyChange,
  showDuplicates,
  onShowDuplicatesChange,
  duplicatesHiddenCount,
  selectedOpportunity,
  onSelect,
  checkedIds,
  onToggleChecked,
  onToggleAllVisible,
  onBulkApprove,
  onBulkIgnore,
  bulkBusy,
  lastSeenAt,
  generatingReplyId,
  updatingStatus,
  onGenerateReply,
  onApprove,
  onIgnore,
  emptyAction,
}: InboxSectionProps) {
  const selectedId = selectedOpportunity?.id ?? null;
  const newCount = opportunities.filter((opp) => isNewSince(opp.created_at, lastSeenAt)).length;
  const checkedVisibleCount = opportunities.filter((opp) => checkedIds.has(opp.id)).length;
  const allVisibleChecked = opportunities.length > 0 && checkedVisibleCount === opportunities.length;

  // Keep the selected row in view when selection moves (keyboard or programmatic).
  useEffect(() => {
    if (selectedId === null) {
      return;
    }
    document.getElementById(`inbox-opp-${selectedId}`)?.scrollIntoView({ block: "nearest" });
  }, [selectedId]);

  const detailPane = (
    <InboxDetailPane
      opportunity={selectedOpportunity}
      generating={selectedOpportunity != null && generatingReplyId === selectedOpportunity.id}
      updating={updatingStatus}
      onGenerateReply={onGenerateReply}
      onApprove={onApprove}
      onIgnore={onIgnore}
    />
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          Conversations to Review
          <Badge variant="secondary" className="px-1.5 py-0 text-[11px]">
            {opportunities.length}
          </Badge>
          {newCount > 0 && (
            <Badge className="border-primary/20 bg-primary/10 px-1.5 py-0 text-[11px] text-primary" variant="outline">
              {newCount} new since last visit
            </Badge>
          )}
        </CardTitle>
        <CardAction>
          <div className="flex items-center gap-2">
            <FiltersBar search={search} filters={filters} />
            <Popover>
              <PopoverTrigger
                className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full border bg-muted text-xs font-semibold text-muted-foreground transition-colors hover:bg-muted/80"
                aria-label="Keyboard shortcuts"
                title="Keyboard shortcuts"
              >
                ?
              </PopoverTrigger>
              <PopoverContent align="end" className="w-64 p-3">
                <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-foreground">
                  <Keyboard className="h-3.5 w-3.5" /> Keyboard shortcuts
                </p>
                <ul className="space-y-1.5">
                  {SHORTCUTS.map((shortcut) => (
                    <li key={shortcut.keys} className="flex items-center justify-between gap-3 text-xs">
                      <kbd className="rounded border bg-muted px-1.5 py-0.5 font-mono text-[11px]">
                        {shortcut.keys}
                      </kbd>
                      <span className="text-muted-foreground">{shortcut.action}</span>
                    </li>
                  ))}
                </ul>
              </PopoverContent>
            </Popover>
          </div>
        </CardAction>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Buying-stage filter chips */}
        <StageFilterTabs counts={stageCounts} totalCount={stageTotal} value={stageFilter} onChange={onStageFilterChange} />

        <div className="flex flex-wrap items-center gap-1.5">
          <button
            type="button"
            onClick={() => onHighIntentOnlyChange(!highIntentOnly)}
            className={cn(
              "inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium transition-colors",
              highIntentOnly
                ? "border-primary bg-primary/10 text-primary"
                : "border-transparent bg-muted text-muted-foreground hover:bg-muted/80"
            )}
          >
            High intent only
          </button>
          <button
            type="button"
            onClick={() => onShowDuplicatesChange(!showDuplicates)}
            className={cn(
              "inline-flex items-center gap-1 rounded-full border px-3 py-1 text-xs font-medium transition-colors",
              showDuplicates
                ? "border-primary bg-primary/10 text-primary"
                : "border-transparent bg-muted text-muted-foreground hover:bg-muted/80"
            )}
          >
            {showDuplicates ? "Duplicates visible" : "Duplicates hidden"}
            {!showDuplicates && duplicatesHiddenCount > 0 && (
              <span className="text-[11px] opacity-75">({duplicatesHiddenCount} hidden)</span>
            )}
          </button>
        </div>

        {/* Status filter pills */}
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

        {/* Bulk action bar */}
        {opportunities.length > 0 && (
          <div className="flex flex-wrap items-center gap-3 rounded-lg border bg-muted/30 px-3 py-2">
            <label className="flex cursor-pointer items-center gap-2 text-xs font-medium text-muted-foreground">
              <input
                type="checkbox"
                checked={allVisibleChecked}
                onChange={onToggleAllVisible}
                className="h-3.5 w-3.5 cursor-pointer accent-primary"
              />
              Select all visible
            </label>
            {checkedVisibleCount > 0 && (
              <>
                <span className="text-xs text-muted-foreground">{checkedVisibleCount} selected</span>
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="sm" onClick={onBulkApprove} disabled={bulkBusy}>
                    {bulkBusy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Check className="h-3.5 w-3.5" />}
                    Save
                  </Button>
                  <Button variant="outline" size="sm" onClick={onBulkIgnore} disabled={bulkBusy}>
                    {bulkBusy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <X className="h-3.5 w-3.5" />}
                    Ignore
                  </Button>
                </div>
              </>
            )}
          </div>
        )}

        {opportunities.length === 0 ? (
          <EmptyState
            icon={MessageSquare}
            title={totalCount === 0 ? "No conversations yet" : "No matches for this filter"}
            description={
              totalCount === 0
                ? "Add signals, find sources, then run a scan to bring conversations here."
                : "Try changing the stage, status, or search filters."
            }
            action={emptyAction}
          />
        ) : (
          <>
            {/* Two-pane inbox (desktop) / stacked list (mobile) */}
            <div className="grid overflow-hidden rounded-xl border lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
              <div className="max-h-[420px] overflow-y-auto lg:max-h-[600px] lg:border-r" role="listbox" aria-label="Conversation inbox">
                {opportunities.map((opp) => (
                  <InboxRow
                    key={opp.id}
                    opportunity={opp}
                    selected={opp.id === selectedId}
                    checked={checkedIds.has(opp.id)}
                    isNew={isNewSince(opp.created_at, lastSeenAt)}
                    onSelect={() => onSelect(opp.id)}
                    onToggleChecked={() => onToggleChecked(opp.id)}
                  />
                ))}
              </div>
              <div className="hidden max-h-[600px] lg:block">{detailPane}</div>
            </div>

            {/* Mobile: detail of the tapped row, below the list */}
            {selectedOpportunity && <div className="rounded-xl border lg:hidden">{detailPane}</div>}
          </>
        )}
      </CardContent>
    </Card>
  );
}
