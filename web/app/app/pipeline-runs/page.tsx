"use client";

import { useEffect, useState, useCallback } from "react";
import { Loader2, Terminal, RefreshCw, AlertCircle } from "lucide-react";

import { useAuth } from "@/components/auth/auth-provider";
import { useSelectedProjectId } from "@/hooks/use-selected-project";
import { useToast } from "@/stores/toast";
import { apiRequest } from "@/lib/api";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/shared/page-header";
import { CompanyNav } from "@/components/company/company-nav";
import { EmptyState } from "@/components/shared/empty-state";
import { StatusBadge } from "@/components/shared/status-badge";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface PipelineRun {
  id: string;
  project_id: number;
  status: string;
  progress: number;
  personas_count: number;
  keywords_count: number;
  subreddits_count: number;
  opportunities_count: number;
  created_at: string;
}

interface PipelineRunDetail {
  error_message?: string | null;
  results?: {
    brand_summary?: string | null;
  };
}

export default function PipelineRunsPage() {
  const { token } = useAuth();
  const projectId = useSelectedProjectId();
  const { error } = useToast();
  
  const [loading, setLoading] = useState(true);
  const [runs, setRuns] = useState<PipelineRun[]>([]);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [expandedData, setExpandedData] = useState<PipelineRunDetail | null>(null);
  const [loadingDetails, setLoadingDetails] = useState(false);

  const loadRuns = useCallback(async (silent = false) => {
    if (!token || !projectId) return;
    if (!silent) setLoading(true);
    try {
      const data = await apiRequest<{ items: PipelineRun[] }>(`/v1/auto-pipeline?project_id=${projectId}`, {}, token);
      setRuns(data.items || []);
    } catch (err) {
      error("Failed to load pipeline runs", err instanceof Error ? err.message : "Unknown error");
    }
    if (!silent) setLoading(false);
  }, [token, projectId, error]);

  useEffect(() => {
    void loadRuns();
  }, [loadRuns]);

  async function toggleExpand(id: string) {
    if (expandedId === id) {
      setExpandedId(null);
      setExpandedData(null);
      return;
    }
    
    setExpandedId(id);
    setLoadingDetails(true);
    try {
      const data = await apiRequest<PipelineRunDetail>(`/v1/auto-pipeline/${id}`, {}, token);
      setExpandedData(data);
    } catch (err) {
      error("Failed to load run details", err instanceof Error ? err.message : "Unknown error");
      setExpandedId(null);
    }
    setLoadingDetails(false);
  }

  return (
    <div className="space-y-6">
      <CompanyNav />
      <PageHeader
        title="Run History"
        description="History of automated intelligence gathering runs."
        actions={
          <Button
            variant="outline"
            size="sm"
            onClick={() => void loadRuns(false)}
            disabled={loading}
          >
            {loading && <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" />}
            <RefreshCw className="h-3.5 w-3.5 mr-1" />
            Refresh
          </Button>
        }
      />

      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-20 rounded-xl" />
          ))}
        </div>
      ) : runs.length === 0 ? (
        <EmptyState
          icon={Terminal}
          title="No pipeline runs yet"
          description="Go to Workflow to trigger an intelligence gathering run."
        />
      ) : (
        <div className="space-y-4">
          {runs.map((run) => (
            <Card key={run.id} className="overflow-hidden">
              <div 
                className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 cursor-pointer hover:bg-muted/30 transition-colors"
                onClick={() => void toggleExpand(run.id)}
              >
                <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4 flex-1">
                  <div className="flex items-center gap-2 shrink-0">
                    <StatusBadge
                      variant={run.status === "executed" || run.status === "completed" ? "success" : run.status === "failed" ? "error" : "primary"}
                    >
                      {run.status}
                    </StatusBadge>
                    <span className="text-sm font-medium text-muted-foreground whitespace-nowrap">
                      {new Date(run.created_at).toLocaleString()}
                    </span>
                  </div>
                  
                  <div className="flex items-center gap-4 text-xs text-muted-foreground overflow-x-auto pb-1 sm:pb-0">
                    <span className="whitespace-nowrap">Personas: <strong className="text-foreground">{run.personas_count}</strong></span>
                    <span className="whitespace-nowrap">Keywords: <strong className="text-foreground">{run.keywords_count}</strong></span>
                    <span className="whitespace-nowrap">Opportunities: <strong className="text-foreground">{run.opportunities_count}</strong></span>
                  </div>
                </div>
                
                <Button variant="ghost" size="sm" className="shrink-0 self-start sm:self-auto">
                  {expandedId === run.id ? "Hide Details" : "View Details"}
                </Button>
              </div>
              
              {expandedId === run.id && (
                <div className="border-t border-border bg-muted/10 p-4">
                  {loadingDetails ? (
                    <div className="flex justify-center p-4">
                      <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                    </div>
                  ) : expandedData ? (
                    <div className="space-y-4">
                      {expandedData.error_message && (
                        <div className="flex gap-2 p-3 text-sm text-destructive bg-destructive/10 rounded-md">
                          <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                          <p>{expandedData.error_message}</p>
                        </div>
                      )}
                      
                      {expandedData.results?.brand_summary && (
                        <div>
                          <h4 className="text-sm font-semibold mb-2">Generated Brand Summary</h4>
                          <div className="bg-card border rounded-md p-3 text-sm">
                            {expandedData.results.brand_summary}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="text-sm text-muted-foreground text-center p-4">
                      Could not load details.
                    </div>
                  )}
                </div>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
