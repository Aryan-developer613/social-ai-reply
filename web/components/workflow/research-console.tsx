"use client";

import { useEffect, useMemo, useRef, useState, type ChangeEvent } from "react";
import {
  Clipboard,
  AlertCircle,
  AtSign,
  CheckCircle2,
  ExternalLink,
  FileText,
  Globe2,
  Loader2,
  MessageCircle,
  Search,
  UploadCloud,
  type LucideIcon,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  getFileAnalysisReport,
  listAnalysisFiles,
  runEnhancedSearch,
  uploadAnalysisFile,
  type FileAnalysisRecord,
  type FileUploadResponse,
  type SearchProvider,
  type SearchResponse,
} from "@/lib/api";
import { cn } from "@/lib/utils";
import { useToast } from "@/stores/toast";
import { getErrorMessage } from "@/types/errors";

export type KeywordLike = string | { keyword?: string | null };

type ResearchConsoleProps = {
  token: string | null;
  projectId?: number | null;
  company?: {
    name?: string | null;
    description?: string | null;
  } | null;
  keywords?: KeywordLike[];
  websiteUrl?: string;
};

const SEARCH_MODES: Array<{ id: SearchProvider; label: string; icon: LucideIcon }> = [
  { id: "web", label: "Web", icon: Globe2 },
  { id: "reddit", label: "Reddit", icon: MessageCircle },
  { id: "x", label: "X", icon: AtSign },
];

export function keywordText(keyword: KeywordLike): string {
  if (typeof keyword === "string") return keyword;
  return keyword.keyword ?? "";
}

function asNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function asString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function asStringList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === "string" && item.trim().length > 0);
}

function formatDate(value?: string | null): string | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric" }).format(date);
}

function topTerms(analysis: Record<string, unknown>): string[] {
  const terms = analysis.top_terms;
  if (!Array.isArray(terms)) return [];

  return terms
    .map((term) => {
      if (Array.isArray(term)) return String(term[0] ?? "");
      return String(term ?? "");
    })
    .filter(Boolean)
    .slice(0, 6);
}

function analysisStats(analysis: Record<string, unknown>): Array<{ label: string; value: string }> {
  const rows = asNumber(analysis.rows);
  const words = asNumber(analysis.words);
  const pages = asNumber(analysis.pages);
  const characters = asNumber(analysis.characters);
  const columns = asStringList(analysis.columns);

  const stats: Array<{ label: string; value: string }> = [];
  if (rows !== null) stats.push({ label: "Rows", value: rows.toLocaleString() });
  if (columns.length > 0) stats.push({ label: "Columns", value: String(columns.length) });
  if (words !== null) stats.push({ label: "Words", value: words.toLocaleString() });
  if (pages !== null) stats.push({ label: "Pages", value: pages.toLocaleString() });
  if (characters !== null) stats.push({ label: "Characters", value: characters.toLocaleString() });
  return stats;
}

export function ResearchConsole({ token, projectId, company, keywords = [], websiteUrl = "" }: ResearchConsoleProps) {
  const toast = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [provider, setProvider] = useState<SearchProvider>("web");
  const [query, setQuery] = useState("");
  const [queryEdited, setQueryEdited] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [searchResponse, setSearchResponse] = useState<SearchResponse | null>(null);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [fileUpload, setFileUpload] = useState<FileUploadResponse | null>(null);
  const [recentFiles, setRecentFiles] = useState<FileAnalysisRecord[]>([]);
  const [selectedFile, setSelectedFile] = useState<FileAnalysisRecord | null>(null);
  const [isLoadingFiles, setIsLoadingFiles] = useState(false);
  const [isCopyingReport, setIsCopyingReport] = useState(false);

  const keywordTerms = useMemo(
    () => keywords.map(keywordText).filter(Boolean).slice(0, 3),
    [keywords],
  );

  const defaultQuery = useMemo(() => {
    const base = company?.name || websiteUrl.replace(/^https?:\/\//, "").replace(/\/$/, "");
    return [base, ...keywordTerms.slice(0, 2), "customer pain points"].filter(Boolean).join(" ");
  }, [company?.name, keywordTerms, websiteUrl]);

  useEffect(() => {
    if (!queryEdited && defaultQuery) {
      setQuery(defaultQuery);
    }
  }, [defaultQuery, queryEdited]);

  useEffect(() => {
    if (!token) return;

    let cancelled = false;
    setIsLoadingFiles(true);
    listAnalysisFiles(token, projectId ?? undefined)
      .then((files) => {
        if (cancelled) return;
        setRecentFiles(files);
        setSelectedFile((current) => {
          if (current && files.some((file) => file.id === current.id)) {
            return current;
          }
          return files[0] ?? null;
        });
      })
      .catch(() => {
        if (!cancelled) setRecentFiles([]);
      })
      .finally(() => {
        if (!cancelled) setIsLoadingFiles(false);
      });

    return () => {
      cancelled = true;
    };
  }, [projectId, token]);

  async function handleSearch() {
    const trimmed = query.trim();
    if (!token || !trimmed) return;

    setIsSearching(true);
    setSearchError(null);
    try {
      const response = await runEnhancedSearch(token, provider, {
        query: trimmed,
        project_id: projectId ?? undefined,
        limit: 8,
        use_cache: true,
      });
      setSearchResponse(response);
      toast.success("Research complete", `${response.results.length} result${response.results.length === 1 ? "" : "s"} found.`);
    } catch (err) {
      const message = getErrorMessage(err);
      setSearchError(message);
      toast.error("Research failed", message);
    } finally {
      setIsSearching(false);
    }
  }

  async function handleFileUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.currentTarget.files?.[0];
    event.currentTarget.value = "";
    if (!token || !file) return;

    setIsUploading(true);
    try {
      const response = await uploadAnalysisFile(token, file, projectId);
      setFileUpload(response);
      setSelectedFile(response.file);
      setRecentFiles((files) => [response.file, ...files.filter((row) => row.id !== response.file.id)].slice(0, 5));
      const status = asString(response.analysis.status);
      if (status === "missing_dependency") {
        toast.warning("File saved", asString(response.analysis.message) || "A parser dependency is needed for full analysis.");
      } else {
        toast.success("File analyzed", response.file.file_name);
      }
    } catch (err) {
      toast.error("Upload failed", getErrorMessage(err));
    } finally {
      setIsUploading(false);
    }
  }

  async function handleCopyReport() {
    if (!token || !selectedFile) return;

    setIsCopyingReport(true);
    try {
      const report = await getFileAnalysisReport(token, selectedFile.id);
      await navigator.clipboard.writeText(report);
      toast.success("Report copied", "The markdown report is ready to paste.");
    } catch (err) {
      toast.error("Could not copy report", getErrorMessage(err));
    } finally {
      setIsCopyingReport(false);
    }
  }

  const uploadedAnalysis = fileUpload && fileUpload.file.id === selectedFile?.id ? fileUpload.analysis : null;
  const analysis = uploadedAnalysis ?? selectedFile?.analysis_result ?? null;
  const stats = analysis ? analysisStats(analysis) : [];
  const terms = analysis ? topTerms(analysis) : [];
  const preview = analysis ? asString(analysis.preview) : "";
  const message = analysis ? asString(analysis.message) : "";
  const analysisStatus = analysis ? asString(analysis.status) : "";

  return (
    <section className="grid gap-4 lg:grid-cols-[minmax(0,1.15fr)_minmax(300px,0.85fr)]">
      <div className="rounded-xl border bg-card p-5 shadow-sm">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h2 className="text-base font-semibold">Research check</h2>
            <p className="mt-1 text-sm text-muted-foreground">Validate important claims before drafting replies.</p>
          </div>
          {searchResponse?.cached && (
            <Badge variant="secondary" className="w-fit">
              Cached
            </Badge>
          )}
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          {SEARCH_MODES.map((mode) => {
            const Icon = mode.icon;
            const active = provider === mode.id;
            return (
              <Button
                key={mode.id}
                type="button"
                variant={active ? "default" : "outline"}
                size="sm"
                onClick={() => setProvider(mode.id)}
                className="gap-1.5"
              >
                <Icon className="h-3.5 w-3.5" />
                {mode.label}
              </Button>
            );
          })}
        </div>

        <div className="mt-3 flex flex-col gap-2 sm:flex-row">
          <Input
            value={query}
            onChange={(event) => {
              setQueryEdited(true);
              setQuery(event.target.value);
            }}
            onKeyDown={(event) => {
              if (event.key === "Enter") void handleSearch();
            }}
            placeholder="Search topic, competitor, or customer problem"
            className="h-9"
          />
          <Button type="button" onClick={() => void handleSearch()} disabled={!token || !query.trim() || isSearching}>
            {isSearching ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
            Search
          </Button>
        </div>

        <div className="mt-4 min-h-32">
          {searchError ? (
            <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{searchError}</span>
            </div>
          ) : searchResponse ? (
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                <span className="font-medium text-foreground">{searchResponse.provider.toUpperCase()}</span>
                <span>{searchResponse.results.length} results</span>
                {searchResponse.citations.length > 0 && <span>{searchResponse.citations.length} citations</span>}
              </div>

              {searchResponse.results.length > 0 ? (
                <div className="space-y-2">
                  {searchResponse.results.slice(0, 5).map((item, index) => {
                    const date = formatDate(item.created_at);
                    return (
                      <a
                        key={`${item.url}-${index}`}
                        href={item.url}
                        target="_blank"
                        rel="noreferrer"
                        className="block rounded-lg border bg-background p-3 transition-colors hover:bg-muted/60"
                      >
                        <div className="flex min-w-0 items-start justify-between gap-3">
                          <div className="min-w-0">
                            <div className="line-clamp-1 text-sm font-medium text-foreground">{item.title || item.url}</div>
                            <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                              <span>{item.source}</span>
                              {date && <span>{date}</span>}
                              {typeof item.score === "number" && <span>Score {item.score}</span>}
                            </div>
                          </div>
                          <ExternalLink className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                        </div>
                        {item.snippet && <p className="mt-2 line-clamp-2 text-xs leading-5 text-muted-foreground">{item.snippet}</p>}
                      </a>
                    );
                  })}
                </div>
              ) : (
                <div className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">No results found.</div>
              )}
            </div>
          ) : (
            <div className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
              Run a search to collect supporting context.
            </div>
          )}
        </div>
      </div>

      <div className="rounded-xl border bg-card p-5 shadow-sm">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between lg:flex-col xl:flex-row">
          <div>
            <h2 className="text-base font-semibold">Brand documents</h2>
            <p className="mt-1 text-sm text-muted-foreground">Use guidelines, reports, and CSV exports as extra context.</p>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            accept=".pdf,.csv,.tsv,.xlsx,.xlsm,.txt,.md"
            onChange={(event) => void handleFileUpload(event)}
          />
          <div className="flex flex-wrap gap-2">
            {selectedFile && (
              <Button
                type="button"
                variant="outline"
                onClick={() => void handleCopyReport()}
                disabled={!token || isCopyingReport}
                className="w-fit"
              >
                {isCopyingReport ? <Loader2 className="h-4 w-4 animate-spin" /> : <Clipboard className="h-4 w-4" />}
                Copy report
              </Button>
            )}
            <Button
              type="button"
              variant="outline"
              onClick={() => fileInputRef.current?.click()}
              disabled={!token || isUploading}
              className="w-fit"
            >
              {isUploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <UploadCloud className="h-4 w-4" />}
              Upload
            </Button>
          </div>
        </div>

        <div className="mt-4">
          {selectedFile && analysis ? (
            <div className="space-y-3">
              <div className="flex items-start gap-3 rounded-lg border bg-background p-3">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  {analysisStatus === "missing_dependency" ? (
                    <AlertCircle className="h-4 w-4" />
                  ) : (
                    <FileText className="h-4 w-4" />
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="truncate text-sm font-medium">{selectedFile.file_name}</p>
                    <Badge
                      variant={analysisStatus === "analyzed" ? "secondary" : "outline"}
                      className={cn(analysisStatus === "missing_dependency" && "border-yellow-300 text-yellow-700")}
                    >
                      {analysisStatus || selectedFile.analysis_status}
                    </Badge>
                  </div>
                  {message && <p className="mt-1 text-xs text-muted-foreground">{message}</p>}
                </div>
              </div>

              {recentFiles.length > 1 && (
                <div className="space-y-2">
                  <div className="text-xs font-medium text-muted-foreground">Recent files</div>
                  <div className="flex flex-wrap gap-2">
                    {recentFiles.slice(0, 5).map((file) => (
                      <Button
                        key={file.id}
                        type="button"
                        variant={selectedFile.id === file.id ? "secondary" : "outline"}
                        size="sm"
                        onClick={() => {
                          setFileUpload(null);
                          setSelectedFile(file);
                        }}
                        className="max-w-full"
                      >
                        <FileText className="h-3.5 w-3.5" />
                        <span className="max-w-40 truncate">{file.file_name}</span>
                      </Button>
                    ))}
                  </div>
                </div>
              )}

              {stats.length > 0 && (
                <div className="grid grid-cols-2 gap-2">
                  {stats.map((stat) => (
                    <div key={stat.label} className="rounded-lg border bg-background p-3">
                      <div className="text-xs text-muted-foreground">{stat.label}</div>
                      <div className="mt-1 text-sm font-semibold">{stat.value}</div>
                    </div>
                  ))}
                </div>
              )}

              {terms.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {terms.map((term) => (
                    <Badge key={term} variant="outline">
                      {term}
                    </Badge>
                  ))}
                </div>
              )}

              {preview && (
                <div className="max-h-28 overflow-y-auto rounded-lg border bg-background p-3 text-xs leading-5 text-muted-foreground">
                  {preview}
                </div>
              )}

              {analysisStatus === "analyzed" && (
                <div className="flex items-center gap-2 text-xs text-emerald-600">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  File is ready for report context.
                </div>
              )}
            </div>
          ) : (
            <div className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
              {isLoadingFiles ? "Loading documents..." : "PDF, CSV, Excel, TXT, and MD files are supported."}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
