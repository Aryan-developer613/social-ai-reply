"use client";

import { useEffect, useRef, useState } from "react";
import { Zap, ArrowRight, Building2, Users, Search, BarChart3, Activity } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { useAuth } from "@/components/auth/auth-provider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { ResearchConsole, keywordText, type KeywordLike } from "@/components/workflow/research-console";
import { cn } from "@/lib/utils";
import { supabase } from "@/lib/supabase";

import { useProjectStore } from "@/stores/project-store";

type PipelineState = "idle" | "running" | "complete" | "error";

interface LogEntry {
  id: number;
  text: string;
  level: "info" | "success" | "warn" | "error";
  time: Date;
}

interface WorkflowCompany {
  name?: string | null;
  description?: string | null;
}

export default function WorkflowPage() {
  const { token } = useAuth();
  const setProjectId = useProjectStore((s) => s.setProjectId);
  
  const [url, setUrl] = useState("");
  const [analysisUrl, setAnalysisUrl] = useState("");
  const [state, setState] = useState<PipelineState>("idle");
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [currentStep, setCurrentStep] = useState<string>("Initializing...");
  const [projectId, setLocalProjectId] = useState<number | null>(null);
  
  // Data accumulated from the stream
  const [company, setCompany] = useState<WorkflowCompany | null>(null);
  const [keywords, setKeywords] = useState<KeywordLike[]>([]);
  const [competitors, setCompetitors] = useState<string[]>([]);
  const [opportunitiesCount, setOpportunitiesCount] = useState<number>(0);
  const [reportMarkdown, setReportMarkdown] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState("");

  const sourceRef = useRef<EventSource | null>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs]);

  async function resolveAnalysisToken(): Promise<string | null> {
    if (token) {
      return token;
    }
    const {
      data: { session },
    } = await supabase.auth.getSession();
    return session?.access_token ?? null;
  }

  async function startAnalysis() {
    const trimmedUrl = url.trim();
    if (!trimmedUrl) return;
    const authToken = await resolveAnalysisToken();
    if (!authToken) {
      setState("error");
      setErrorMessage("Your session is still loading. Please refresh the page or sign in again.");
      return;
    }
    
    // Reset state
    setState("running");
    setErrorMessage("");
    setAnalysisUrl(trimmedUrl);
    setLogs([]);
    setCompany(null);
    setKeywords([]);
    setCompetitors([]);
    setOpportunitiesCount(0);
    setReportMarkdown(null);
    setLocalProjectId(null);
    setCurrentStep("Connecting to SignalFlow...");

    if (sourceRef.current) {
      sourceRef.current.close();
    }

    const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
    const endpoint = `${baseUrl}/v1/analyze/stream?url=${encodeURIComponent(trimmedUrl)}&token=${encodeURIComponent(authToken)}`;
    
    const es = new EventSource(endpoint);
    sourceRef.current = es;

    let logId = 0;

    es.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data);

        if (data.type === "log") {
          setLogs((prev) => [...prev.slice(-49), {
            id: ++logId,
            text: data.msg,
            level: data.level || "info",
            time: new Date(),
          }]);
        } else if (data.type === "data") {
          if (data.key === "company_name") setCompany((prev) => ({ ...prev, name: data.value }));
          else if (data.key === "report") setReportMarkdown(data.value);
          else if (data.key === "opportunities_count") setOpportunitiesCount(data.value);
          else if (data.key === "project_id" && data.value) {
            const nextProjectId = Number(data.value);
            setProjectId(nextProjectId);
            setLocalProjectId(nextProjectId);
          }
        } else if (data.type === "section") {
          setCurrentStep(data.label);
        } else if (data.type === "complete") {
          setCompany(data.company);
          setKeywords(data.keywords || []);
          setCompetitors(data.competitors || []);
          setOpportunitiesCount(data.opportunities_count || 0);
          setReportMarkdown(data.report);
          if (data.project_id) {
            const nextProjectId = Number(data.project_id);
            setProjectId(nextProjectId);
            setLocalProjectId(nextProjectId);
          }
          setState("complete");
          es.close();
        } else if (data.type === "error") {
          setState("error");
          setErrorMessage(data.msg || "Analysis failed. Please check the URL and try again.");
          setLogs((prev) => [...prev, {
            id: ++logId,
            text: data.msg,
            level: "error",
            time: new Date(),
          }]);
          es.close();
        }
      } catch (err) {
        console.error("Failed to parse SSE message", err);
      }
    };

    es.onerror = () => {
      setState("error");
      setErrorMessage("Could not reach the analysis stream. Check that the backend is running, then try again.");
      setLogs((prev) => [...prev, {
        id: ++logId,
        text: "Connection lost or server error.",
        level: "error",
        time: new Date(),
      }]);
      es.close();
    };
  }

  // --- RENDERING ---

  if (state === "idle" || state === "error") {
    return (
      <div className="max-w-3xl mx-auto mt-20 space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
        <div className="text-center space-y-4">
          <div className="mx-auto h-16 w-16 rounded-2xl bg-primary/10 flex items-center justify-center mb-6">
            <Activity className="h-8 w-8 text-primary" />
          </div>
          <h1 className="text-4xl font-extrabold tracking-tight">SignalFlow Intelligence</h1>
          <p className="text-lg text-muted-foreground max-w-xl mx-auto">
            Zero-input social listening. Just drop a URL and our parallel enrichment agents will build your profile, generate personas, and scan the web for high-intent opportunities.
          </p>
        </div>

        <div className="bg-card border rounded-2xl p-2 shadow-sm flex items-center transition-all focus-within:ring-2 focus-within:ring-primary/20 focus-within:border-primary">
          <div className="pl-4 pr-2 text-muted-foreground">
            <Search className="h-5 w-5" />
          </div>
          <Input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                void startAnalysis();
              }
            }}
            placeholder="https://your-startup.com"
            className="flex-1 border-0 shadow-none focus-visible:ring-0 text-lg h-14"
            autoFocus
          />
          <Button 
            size="lg" 
            onClick={() => void startAnalysis()}
            disabled={!url.trim()}
            className="rounded-xl px-8 h-12 font-medium"
          >
            Analyze
            <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        </div>
        
        {state === "error" && (
          <div className="text-center text-red-500 font-medium">
            {errorMessage || "Analysis failed. Please check the URL and try again."}
          </div>
        )}
      </div>
    );
  }

  if (state === "running") {
    return (
      <div className="max-w-2xl mx-auto mt-20 space-y-10 animate-in fade-in duration-500">
        <div className="text-center space-y-4">
          <div className="relative mx-auto h-20 w-20 flex items-center justify-center">
            <div className="absolute inset-0 rounded-full border-4 border-primary/20 animate-pulse"></div>
            <div className="absolute inset-0 rounded-full border-t-4 border-primary animate-spin"></div>
            <Zap className="h-8 w-8 text-primary" />
          </div>
          <h2 className="text-2xl font-bold">{currentStep}</h2>
          <p className="text-muted-foreground">Parallel agents are analyzing the web...</p>
        </div>

        <div className="bg-black/95 rounded-2xl border p-4 shadow-2xl overflow-hidden font-mono text-xs">
          <div className="flex items-center gap-2 mb-4 border-b border-white/10 pb-2">
            <div className="flex gap-1.5">
              <div className="h-3 w-3 rounded-full bg-red-500/80"></div>
              <div className="h-3 w-3 rounded-full bg-yellow-500/80"></div>
              <div className="h-3 w-3 rounded-full bg-green-500/80"></div>
            </div>
            <span className="text-white/40 ml-2">signalflow-agent-stream</span>
          </div>
          <div className="h-64 overflow-y-auto space-y-1.5 pr-2">
            {logs.map((log) => (
              <div key={log.id} className="flex gap-3 text-white/80">
                <span className="text-white/30 shrink-0">
                  {log.time.toLocaleTimeString([], { hour12: false, hour: '2-digit', minute:'2-digit', second:'2-digit' })}
                </span>
                <span className={cn(
                  log.level === "success" && "text-emerald-400",
                  log.level === "warn" && "text-yellow-400",
                  log.level === "error" && "text-red-400 font-bold",
                  log.level === "info" && "text-white/80"
                )}>
                  {log.text}
                </span>
              </div>
            ))}
            <div ref={logsEndRef} />
          </div>
        </div>
      </div>
    );
  }

  // COMPLETE STATE
  return (
    <div className="max-w-5xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
      
      {/* Results Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="h-10 w-10 rounded-xl bg-primary/10 flex items-center justify-center">
              <Building2 className="h-5 w-5 text-primary" />
            </div>
            <h1 className="text-3xl font-bold tracking-tight">
              {company?.name || "Company Profile"}
            </h1>
          </div>
          <p className="text-muted-foreground max-w-2xl">
            {company?.description || "Analysis complete. Review the extracted intelligence below."}
          </p>
        </div>
        
        <div className="flex items-center gap-4 bg-card border rounded-xl p-4 shadow-sm">
          <div className="text-center px-4 border-r">
            <p className="text-2xl font-bold text-primary">{opportunitiesCount}</p>
            <p className="text-xs text-muted-foreground uppercase font-semibold">Opportunities</p>
          </div>
          <div className="text-center px-4">
            <p className="text-2xl font-bold">{keywords.length}</p>
            <p className="text-xs text-muted-foreground uppercase font-semibold">Keywords</p>
          </div>
        </div>
      </div>

      <ResearchConsole
        token={token}
        projectId={projectId}
        company={company}
        keywords={keywords}
        websiteUrl={analysisUrl || url}
      />

      {/* Tabs */}
      <Tabs defaultValue="report" className="w-full">
        <TabsList className="mb-6 w-full justify-start border-b rounded-none pb-px h-auto bg-transparent">
          <TabsTrigger value="report" className="rounded-b-none data-[state=active]:border-b-2 data-[state=active]:border-primary data-[state=active]:shadow-none bg-transparent">
            <BarChart3 className="h-4 w-4 mr-2" />
            Executive Report
          </TabsTrigger>
          <TabsTrigger value="intel" className="rounded-b-none data-[state=active]:border-b-2 data-[state=active]:border-primary data-[state=active]:shadow-none bg-transparent">
            <Users className="h-4 w-4 mr-2" />
            Extracted Intel
          </TabsTrigger>
        </TabsList>
        
        <TabsContent value="report" className="mt-0">
          <div className="rounded-2xl border bg-card p-8 shadow-sm">
            {reportMarkdown ? (
              <div className="prose prose-slate dark:prose-invert max-w-none prose-headings:font-bold prose-h1:text-3xl prose-a:text-primary">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{reportMarkdown}</ReactMarkdown>
              </div>
            ) : (
              <div className="text-center text-muted-foreground py-10">
                Report failed to generate.
              </div>
            )}
          </div>
        </TabsContent>
        
        <TabsContent value="intel" className="mt-0">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="rounded-2xl border bg-card p-6 shadow-sm space-y-4">
              <h3 className="text-lg font-bold flex items-center gap-2">
                <Search className="h-5 w-5 text-primary" />
                Discovered Keywords
              </h3>
              <div className="flex flex-wrap gap-2">
                {keywords.map((kw, i) => (
                  <span key={i} className="px-3 py-1 bg-secondary text-secondary-foreground rounded-full text-sm font-medium">
                    {keywordText(kw)}
                  </span>
                ))}
                {keywords.length === 0 && <span className="text-muted-foreground text-sm">No keywords found.</span>}
              </div>
            </div>
            
            <div className="rounded-2xl border bg-card p-6 shadow-sm space-y-4">
              <h3 className="text-lg font-bold flex items-center gap-2">
                <Activity className="h-5 w-5 text-primary" />
                Competitors Identified
              </h3>
              <div className="flex flex-wrap gap-2">
                {competitors.map((comp, i) => (
                  <span key={i} className="px-3 py-1 border border-border bg-background rounded-full text-sm font-medium text-muted-foreground">
                    {comp}
                  </span>
                ))}
                {competitors.length === 0 && <span className="text-muted-foreground text-sm">No competitors found.</span>}
              </div>
            </div>
          </div>
        </TabsContent>
      </Tabs>
      
      <div className="text-center pt-8">
        <Button variant="outline" onClick={() => setState("idle")}>
          Analyze Another Product
        </Button>
      </div>
    </div>
  );
}
