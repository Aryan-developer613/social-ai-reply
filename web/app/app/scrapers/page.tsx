"use client";

import { FormEvent, useEffect, useState, useRef } from "react";
import { Loader2, Globe, MessageSquare, Send, Save, Trash2, Plus, Zap, CheckCircle2, XCircle, AlertTriangle } from "lucide-react";

import { useAuth } from "@/components/auth/auth-provider";
import { useToast } from "@/stores/toast";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { PageHeader } from "@/components/shared/page-header";
import {
  getScrapers,
  createOrUpdateScraper,
  deleteScraper,
  chatWithAssistant,
  testScraper,
  getPresets,
  type CustomScraper,
  type ScraperTestResponse,
  type ScraperPreset,
} from "@/lib/api/scrapers";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

const DEFAULT_FORM = {
  platform: "instagram",
  api_key: "",
  api_host: "",
  search_endpoint: "",
  search_param_name: "",
  comments_endpoint: "",
  comments_param_name: "",
  items_json_path: "data.items",
  is_active: true,
};

export default function ScrapersPage() {
  const { token } = useAuth();
  const { success, error } = useToast();

  const [loading, setLoading] = useState(true);
  const [scrapers, setScrapers] = useState<CustomScraper[]>([]);
  
  // Form state
  const [activeScraper, setActiveScraper] = useState<CustomScraper | null>(null);
  const [formData, setFormData] = useState(DEFAULT_FORM);
  const [isSaving, setIsSaving] = useState(false);
  
  // Chat state
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: "assistant", content: "Hi! I can help you configure a custom RapidAPI scraper. What platform do you want to set up? Do you already have an API from RapidAPI in mind?" }
  ]);
  const [chatInput, setChatInput] = useState("");
  const [isChatting, setIsChatting] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Test connection state
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<ScraperTestResponse | null>(null);

  // Presets state
  const [presets, setPresets] = useState<Record<string, ScraperPreset[]>>({});
  const [presetsLoaded, setPresetsLoaded] = useState(false);

  useEffect(() => {
    if (!token) return;
    loadScrapers();
    if (!presetsLoaded) {
      getPresets(token).then(setPresets).catch(() => {}).finally(() => setPresetsLoaded(true));
    }
  }, [token]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  async function loadScrapers() {
    setLoading(true);
    try {
      const data = await getScrapers(token!);
      setScrapers(data);
    } catch (err) {
      error("Failed to load scrapers", err instanceof Error ? err.message : "Unknown error");
    }
    setLoading(false);
  }

  function handleSelectScraper(scraper: CustomScraper) {
    setActiveScraper(scraper);
    setFormData({
      platform: scraper.platform,
      api_key: "", // Hide key for security, require re-entry if changing
      api_host: scraper.api_host,
      search_endpoint: scraper.search_endpoint,
      search_param_name: scraper.search_param_name,
      comments_endpoint: scraper.comments_endpoint || "",
      comments_param_name: scraper.comments_param_name || "",
      items_json_path: scraper.items_json_path,
      is_active: scraper.is_active,
    });
  }

  function handleNewScraper() {
    setActiveScraper(null);
    setFormData(DEFAULT_FORM);
    setTestResult(null);
  }

  function handleApplyPreset(preset: ScraperPreset) {
    setFormData(prev => ({
      ...prev,
      api_host: preset.api_host,
      search_endpoint: preset.search_endpoint,
      search_param_name: preset.search_param_name,
      items_json_path: preset.items_json_path,
      comments_endpoint: preset.comments_endpoint || "",
      comments_param_name: preset.comments_param_name || "",
    }));
    setTestResult(null);
    success("Preset applied", `Applied ${preset.name} configuration. Don't forget to add your API key!`);
  }

  async function handleTestConnection() {
    if (!token || !formData.api_host || !formData.search_endpoint) return;
    setIsTesting(true);
    setTestResult(null);
    try {
      const result = await testScraper(token, {
        api_host: formData.api_host,
        api_key: formData.api_key || null,
        search_endpoint: formData.search_endpoint,
        search_param_name: formData.search_param_name,
        items_json_path: formData.items_json_path,
      });
      setTestResult(result);
      if (result.success) {
        success("Connection OK", `API responded with ${result.items_found} items.`);
        // Auto-suggest JSON path if user's is wrong
        if (result.suggested_json_path && result.warnings.length > 0) {
          setFormData(prev => ({ ...prev, items_json_path: result.suggested_json_path! }));
        }
      } else {
        error("Connection failed", result.error || "API did not respond.");
      }
    } catch (err) {
      error("Test failed", err instanceof Error ? err.message : "Unknown error");
    }
    setIsTesting(false);
  }

  async function handleSave(e: FormEvent) {
    e.preventDefault();
    if (!token) return;
    setIsSaving(true);
    try {
      const payload = {
        platform: formData.platform,
        api_key: formData.api_key || null, // Allow keeping existing key if empty
        api_host: formData.api_host,
        search_endpoint: formData.search_endpoint,
        search_param_name: formData.search_param_name,
        comments_endpoint: formData.comments_endpoint || null,
        comments_param_name: formData.comments_param_name || null,
        items_json_path: formData.items_json_path,
        is_active: formData.is_active,
      };
      await createOrUpdateScraper(token, payload);
      success("Saved", `Scraper configuration for ${formData.platform} updated.`);
      await loadScrapers();
      // Keep form open
    } catch (err) {
      error("Save failed", err instanceof Error ? err.message : "Unknown error");
    }
    setIsSaving(false);
  }

  async function handleDelete(id: number) {
    if (!token || !confirm("Are you sure you want to delete this scraper config?")) return;
    try {
      await deleteScraper(token, id);
      success("Deleted", "Scraper configuration removed.");
      handleNewScraper();
      await loadScrapers();
    } catch (err) {
      error("Delete failed", err instanceof Error ? err.message : "Unknown error");
    }
  }

  async function handleSendChat(e: FormEvent) {
    e.preventDefault();
    if (!token || !chatInput.trim()) return;

    const userMsg = chatInput.trim();
    setChatInput("");
    setMessages(prev => [...prev, { role: "user", content: userMsg }]);
    setIsChatting(true);

    try {
      const res = await chatWithAssistant(token, userMsg, messages);
      setMessages(prev => [...prev, { role: "assistant", content: res.reply }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: "assistant", content: "Sorry, I encountered an error. Please try again." }]);
    }
    setIsChatting(false);
  }

  return (
    <div className="flex h-full flex-col gap-6 p-8">
      <PageHeader
        title="Custom Scrapers (BYOS)"
        description="Bring Your Own Scraper: Add your RapidAPI keys to dynamically replace our standard scrapers."
      />

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-[calc(100vh-12rem)]">
        
        {/* Left Column: Form & List */}
        <div className="lg:col-span-7 flex flex-col gap-6 overflow-y-auto pr-2">
          
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <div>
                <CardTitle>Configured Scrapers</CardTitle>
                <CardDescription>Select a scraper to edit or create a new one.</CardDescription>
              </div>
              <Button size="sm" variant="outline" onClick={handleNewScraper}>
                <Plus className="w-4 h-4 mr-2" />
                New Scraper
              </Button>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex justify-center p-4"><Loader2 className="w-6 h-6 animate-spin text-muted-foreground" /></div>
              ) : scrapers.length === 0 ? (
                <div className="text-sm text-muted-foreground p-4 text-center border border-dashed rounded-md">
                  No custom scrapers configured.
                </div>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {scrapers.map(s => (
                    <Button 
                      key={s.id} 
                      variant={activeScraper?.id === s.id ? "default" : "secondary"}
                      onClick={() => handleSelectScraper(s)}
                      className="capitalize"
                    >
                      <Globe className="w-4 h-4 mr-2" />
                      {s.platform}
                    </Button>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="flex-1">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>{activeScraper ? `Edit ${activeScraper.platform} Scraper` : "New Scraper Configuration"}</CardTitle>
                  <CardDescription>Define the API endpoints and JSON paths for the RapidAPI host.</CardDescription>
                </div>
                {presets[formData.platform]?.length > 0 && (
                  <Select onValueChange={(v) => {
                    const preset = presets[formData.platform]?.find(p => p.name === v);
                    if (preset) handleApplyPreset(preset);
                  }}>
                    <SelectTrigger className="w-[200px]">
                      <SelectValue placeholder="Use a preset..." />
                    </SelectTrigger>
                    <SelectContent>
                      {presets[formData.platform]?.map(p => (
                        <SelectItem key={p.name} value={p.name}>{p.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              </div>
            </CardHeader>
            <CardContent>
              <form id="scraper-form" onSubmit={handleSave} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Platform</Label>
                    <Select value={formData.platform || ""} onValueChange={v => setFormData({...formData, platform: v as string})}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="instagram">Instagram</SelectItem>
                        <SelectItem value="twitter">Twitter</SelectItem>
                        <SelectItem value="linkedin">LinkedIn</SelectItem>
                        <SelectItem value="reddit">Reddit</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>API Key (RapidAPI)</Label>
                    <Input 
                      type="password" 
                      placeholder={activeScraper ? "•••••••••••• (Leave blank to keep)" : "Enter API Key"} 
                      value={formData.api_key}
                      onChange={e => setFormData({...formData, api_key: e.target.value})}
                      required={!activeScraper}
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>API Host</Label>
                  <Input 
                    placeholder="e.g. instagram-scraper2.p.rapidapi.com" 
                    value={formData.api_host}
                    onChange={e => setFormData({...formData, api_host: e.target.value})}
                    required
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Search Endpoint</Label>
                    <Input 
                      placeholder="e.g. /search_users" 
                      value={formData.search_endpoint}
                      onChange={e => setFormData({...formData, search_endpoint: e.target.value})}
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Search Param Name</Label>
                    <Input 
                      placeholder="e.g. search_query" 
                      value={formData.search_param_name}
                      onChange={e => setFormData({...formData, search_param_name: e.target.value})}
                      required
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>Items JSON Path</Label>
                  <Input 
                    placeholder="e.g. data.items" 
                    value={formData.items_json_path}
                    onChange={e => setFormData({...formData, items_json_path: e.target.value})}
                    required
                  />
                  <p className="text-xs text-muted-foreground">The dot-notation path to the array of posts/users in the response.</p>
                </div>

                <div className="grid grid-cols-2 gap-4 pt-4 border-t">
                  <div className="space-y-2">
                    <Label>Comments Endpoint (Optional)</Label>
                    <Input 
                      placeholder="e.g. /post_comments" 
                      value={formData.comments_endpoint}
                      onChange={e => setFormData({...formData, comments_endpoint: e.target.value})}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Comments Param Name</Label>
                    <Input 
                      placeholder="e.g. post_id" 
                      value={formData.comments_param_name}
                      onChange={e => setFormData({...formData, comments_param_name: e.target.value})}
                    />
                  </div>
                </div>

                <div className="flex items-center gap-2 pt-2">
                  <input 
                    type="checkbox" 
                    id="is_active" 
                    checked={formData.is_active}
                    onChange={e => setFormData({...formData, is_active: e.target.checked})}
                    className="rounded border-gray-300"
                  />
                  <Label htmlFor="is_active" className="cursor-pointer">Active</Label>
                </div>
              </form>
            </CardContent>
            {/* Test result + warnings */}
            {testResult && (
              <div className={`mx-4 mb-2 p-3 rounded-md text-sm border ${testResult.success ? 'bg-emerald-500/10 border-emerald-500/30' : 'bg-red-500/10 border-red-500/30'}`}>
                <div className="flex items-center gap-2 font-medium mb-1">
                  {testResult.success
                    ? <><CheckCircle2 className="w-4 h-4 text-emerald-500" /> Connected — {testResult.items_found} items found</>
                    : <><XCircle className="w-4 h-4 text-red-500" /> Failed ({testResult.status_code}): {testResult.error?.slice(0, 100)}</>
                  }
                </div>
                {testResult.suggested_json_path && (
                  <p className="text-xs text-muted-foreground">Suggested JSON path: <code className="bg-muted px-1 rounded">{testResult.suggested_json_path}</code></p>
                )}
                {testResult.sample_keys.length > 0 && (
                  <p className="text-xs text-muted-foreground mt-1">Response keys: <code className="bg-muted px-1 rounded">{testResult.sample_keys.join(', ')}</code></p>
                )}
                {testResult.warnings.map((w, i) => (
                  <div key={i} className="flex items-start gap-1.5 mt-1.5 text-xs text-amber-600 dark:text-amber-400">
                    <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                    <span>{w}</span>
                  </div>
                ))}
              </div>
            )}
            <CardFooter className="flex justify-between border-t p-4 bg-muted/20">
              <div className="flex gap-2">
                {activeScraper && (
                  <Button variant="destructive" size="sm" onClick={() => handleDelete(activeScraper.id)}>
                    <Trash2 className="w-4 h-4 mr-2" />
                    Delete
                  </Button>
                )}
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={handleTestConnection} 
                  disabled={isTesting || !formData.api_host || !formData.search_endpoint}
                >
                  {isTesting ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Zap className="w-4 h-4 mr-2" />}
                  Test Connection
                </Button>
              </div>
              <Button type="submit" form="scraper-form" disabled={isSaving}>
                {isSaving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                Save Configuration
              </Button>
            </CardFooter>
          </Card>
        </div>

        {/* Right Column: AI Assistant Chat */}
        <div className="lg:col-span-5 h-full flex flex-col">
          <Card className="flex-1 flex flex-col overflow-hidden border-primary/20 shadow-sm">
            <CardHeader className="bg-primary/5 py-3 px-4 border-b">
              <div className="flex items-center gap-2">
                <MessageSquare className="w-5 h-5 text-primary" />
                <CardTitle className="text-base font-medium">Setup Assistant</CardTitle>
              </div>
              <CardDescription className="text-xs">
                Need help mapping an API? Paste a JSON response here!
              </CardDescription>
            </CardHeader>
            <CardContent className="flex-1 p-0 overflow-hidden relative flex flex-col">
              <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
                {messages.map((msg, idx) => (
                  <div key={idx} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                    <div className={`max-w-[85%] rounded-lg p-3 text-sm ${msg.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted"}`}>
                      {msg.content}
                    </div>
                  </div>
                ))}
                {isChatting && (
                  <div className="flex justify-start">
                    <div className="max-w-[85%] rounded-lg p-3 text-sm bg-muted flex items-center gap-2">
                      <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
                      <span className="text-muted-foreground">Thinking...</span>
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
            <CardFooter className="p-3 border-t bg-background">
              <form onSubmit={handleSendChat} className="flex w-full gap-2">
                <Textarea 
                  value={chatInput}
                  onChange={e => setChatInput(e.target.value)}
                  placeholder="Ask a question or paste JSON..."
                  className="min-h-[40px] h-10 max-h-32 py-2 resize-none"
                  onKeyDown={e => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSendChat(e);
                    }
                  }}
                />
                <Button type="submit" size="icon" disabled={isChatting || !chatInput.trim()}>
                  <Send className="w-4 h-4" />
                </Button>
              </form>
            </CardFooter>
          </Card>
        </div>

      </div>
    </div>
  );
}