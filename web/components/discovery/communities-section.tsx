"use client";

import { Loader2, Search, Users, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/shared/empty-state";
import { PlatformIcon } from "@/components/shared/platform-icon";
import { ScoreBadge } from "@/components/shared/score-badge";

export interface CommunityItem {
  id: number;
  name: string;
  description?: string | null;
  fit_score?: number;
}

interface CommunitiesSectionProps {
  communities: CommunityItem[];
  onDiscover: () => void;
  discovering: boolean;
  canDiscover: boolean;
  onDeleteCommunity: (community: CommunityItem) => void;
}

/** Sources card: Reddit communities + info about keyword-based platforms. */
export function CommunitiesSection({
  communities,
  onDiscover,
  discovering,
  canDiscover,
  onDeleteCommunity,
}: CommunitiesSectionProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          Sources to Monitor
          <Badge variant="secondary" className="text-[11px] px-1.5 py-0">
            {communities.length} Reddit {communities.length === 1 ? "source" : "sources"}
          </Badge>
        </CardTitle>
        <CardAction>
          <Button variant="outline" size="sm" onClick={onDiscover} disabled={discovering || !canDiscover}>
            {discovering ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
            Find sources
          </Button>
        </CardAction>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Reddit communities */}
        {communities.length === 0 ? (
          <EmptyState
            icon={Users}
            title="No sources yet"
            description="Add search signals first, then find places where your customers are already talking."
          />
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {communities.map((community) => (
              <div key={community.id} className="flex items-center justify-between rounded-lg border bg-card p-3">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <PlatformIcon platform="reddit" />
                    <span className="text-sm font-medium truncate">{community.name}</span>
                  </div>
                  {community.description && (
                    <p className="mt-1 text-xs text-muted-foreground truncate">
                      {community.description.substring(0, 80)}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-2 shrink-0 ml-3">
                  {community.fit_score !== undefined && <ScoreBadge score={community.fit_score} />}
                  <button
                    onClick={() => onDeleteCommunity(community)}
                    aria-label={`Remove ${community.name}`}
                    className="inline-flex rounded-sm text-muted-foreground hover:text-foreground"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Multi-platform info strip */}
        <div className="mt-6 border-t pt-4">
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-xs text-muted-foreground font-medium">Also searched from your signals:</span>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
              <div className="flex items-center gap-1.5">
                <PlatformIcon platform="twitter" />
                <span className="text-xs text-muted-foreground">Twitter</span>
              </div>
              <div className="flex items-center gap-1.5">
                <PlatformIcon platform="hackernews" />
                <span className="text-xs text-muted-foreground">HackerNews</span>
              </div>
              <div className="flex items-center gap-1.5">
                <PlatformIcon platform="github" />
                <span className="text-xs text-muted-foreground">GitHub</span>
              </div>
              <div className="flex items-center gap-1.5">
                <PlatformIcon platform="indiehackers" />
                <span className="text-xs text-muted-foreground">IndieHackers</span>
              </div>
              <div className="flex items-center gap-1.5">
                <PlatformIcon platform="linkedin" />
                <span className="text-xs text-muted-foreground">LinkedIn</span>
              </div>
              <div className="flex items-center gap-1.5">
                <PlatformIcon platform="instagram" />
                <span className="text-xs text-muted-foreground">Instagram</span>
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
