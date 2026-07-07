"use client";

import { Loader2, Plus, Sparkles, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

export interface SignalItem {
  id: number;
  keyword: string;
}

interface SignalsSectionProps {
  keywords: SignalItem[];
  newKeyword: string;
  onNewKeywordChange: (value: string) => void;
  onAddKeyword: () => void;
  addingKeyword: boolean;
  onGenerateKeywords: () => void;
  generatingKeywords: boolean;
  onDeleteKeyword: (keyword: SignalItem) => void;
}

/** Search Signals card: add/generate/delete discovery keywords. */
export function SignalsSection({
  keywords,
  newKeyword,
  onNewKeywordChange,
  onAddKeyword,
  addingKeyword,
  onGenerateKeywords,
  generatingKeywords,
  onDeleteKeyword,
}: SignalsSectionProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          Search Signals
          <Badge variant="secondary" className="text-[11px] px-1.5 py-0">
            {keywords.length}
          </Badge>
        </CardTitle>
        <CardAction>
          <Button variant="outline" size="sm" onClick={onGenerateKeywords} disabled={generatingKeywords}>
            {generatingKeywords ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            Suggest signals
          </Button>
        </CardAction>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex gap-2">
          <Input
            type="text"
            value={newKeyword}
            onChange={(event) => onNewKeywordChange(event.target.value)}
            placeholder="Add a keyword, customer pain, or topic"
            onKeyDown={(event) => event.key === "Enter" && onAddKeyword()}
            className="flex-1"
          />
          <Button size="sm" onClick={onAddKeyword} disabled={addingKeyword}>
            {addingKeyword ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
            Add
          </Button>
        </div>
        {keywords.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {keywords.map((keyword) => (
              <Badge key={keyword.id} variant="secondary" className="inline-flex items-center gap-1.5">
                {keyword.keyword}
                <button
                  onClick={() => onDeleteKeyword(keyword)}
                  aria-label={`Remove ${keyword.keyword}`}
                  className="ml-0.5 inline-flex rounded-sm text-muted-foreground hover:text-foreground"
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">
            Add the words your customers use. These help the scan find better conversations.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
