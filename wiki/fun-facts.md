# Fun facts

Easter eggs, origin stories, and interesting discoveries in Social AI Reply.

## Project origins

### Name evolution
The project has gone through several name iterations:
- **RedditFlow** - Original name focused on Reddit automation
- **Social AI Reply** - Broader name reflecting multi-platform support
- **360 Flatmates** - The team/company name behind the project

The README still shows both names, reflecting this evolution.

### The "CMO" reference
The project is sometimes called an "AI CMO" (Chief Marketing Officer). This reflects the ambition to automate marketing tasks that a human CMO would handle: finding opportunities, drafting responses, and building brand authority.

## Code discoveries

### The longest file
`app/services/product/relevance.py` at 38,580 bytes is one of the largest source files. It contains the legacy relevance scoring logic that's being replaced by `relevance_v2.py`.

### The oldest surviving code
The `app/db/supabase_client.py` file contains some of the oldest patterns in the codebase, including the HTTP/1.1 workaround for Supabase's CDN issues.

### The HTTP/2 workaround
In `app/db/supabase_client.py`, there's a comment explaining why HTTP/1.1 is forced on PostgREST:
> "HTTP/2 connection pooling breaks against Supabase's CDN — idle pooled connections get closed server-side, and the next use of the pool raises httpx.RemoteProtocolError"

This is a real-world example of debugging production issues.

## Technical trivia

### The embedding service
The default embedding service uses TF-IDF from scikit-learn, which is a classical machine learning technique. The optional sentence-transformers provides modern neural embeddings, but TF-IDF is chosen as default because:
- No model download required
- Works offline
- Fast computation
- Good enough for most use cases

### The relevance formula
The weighted scoring formula:
```
base_score = keyword_score * 0.25
           + semantic_similarity * 0.30
           + intent_score * 0.20
           + pain_point_score * 0.10
           + source_fit_score * 0.10
           + freshness_score * 0.05
           - penalties
```

The weights were likely tuned through experimentation, with semantic similarity getting the highest weight (30%) because meaning matters more than exact keyword matches.

### The hard reject rules
A post is rejected if:
- relevance_score < 70
- semantic_similarity < 0.45
- Fewer than 2 meaningful keyword matches
- Intent is spam/unsafe/irrelevant
- Job posting (unless recruiting-related)
- Too old (>180 days)

These thresholds represent product decisions about what constitutes a "relevant opportunity."

## Development patterns

### The "no auto-posting" principle
The README explicitly states: "All posting is manual — nothing is auto-posted to Reddit." This is a deliberate product decision to avoid spam and maintain authenticity.

### The free-first approach
The project emphasizes "free/open-source-first" and "no paid API dependencies." The default LLM (Gemini) requires an API key, but the template fallback works without any API keys.

### The manual mode for X/LinkedIn
X/Twitter and LinkedIn agents operate in "manual mode" because their free APIs are unreliable. The agents generate content ideas and search queries, but don't fetch live data.

## Naming conventions

### The "copilot" naming
The LLM-driven reply/post generation is called "copilot" rather than "AI writer" or "auto-responder." This reflects the human-in-the-loop design where the AI assists but doesn't replace human judgment.

### The "brand brain" naming
The website analysis system is called "Brand Brain" rather than "website analyzer" or "SEO crawler." This emphasizes the intelligence extraction aspect rather than just technical analysis.

## Interesting implementation details

### The singleton pattern
The Supabase client uses a singleton pattern with `@lru_cache(maxsize=1)`. This ensures only one client instance exists per process.

### The provider registry
LLM providers use a registry pattern where each provider registers itself on import. This makes adding new providers a one-file change.

### The feedback loop
The system learns from user feedback (approve/reject actions) to calibrate future scoring. This creates a personalized relevance model over time.

## Version history

### The React 19 migration
The frontend was migrated from React 18 to React 19 with no code changes required. The existing patterns were already compatible.

### The SQLAlchemy to Supabase migration
The backend migrated from SQLAlchemy ORM to Supabase Python SDK. This was a significant architectural change that touched many files.

## Community aspects

### The "helpful replies" philosophy
The platform is designed to help users craft "helpful replies" rather than "promotional content." This reflects a focus on genuine community engagement.

### The transparency emphasis
The relevance scoring is "transparent" with clear `reason_relevant` and `rejection_reason` fields. Users can understand why opportunities were kept or rejected.

## Development insights

### The rate limiting purpose
Rate limiting exists for "platform stability and abuse protection," not as "commercial, entitlement, or pricing limit." This distinction matters for the product's positioning.

### The initial-phase usage policy
The platform doesn't enforce customer-facing usage limits in the initial phase. This is an explicit product decision to let early users use the platform without artificial restrictions.

---

*360 Flatmates Platform Documentation*
