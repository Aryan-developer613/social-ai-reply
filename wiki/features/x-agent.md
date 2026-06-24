# X Agent

Generates X/Twitter content ideas and search queries for manual engagement.

## Purpose

The X Agent creates content ideas and search queries for X/Twitter engagement. It operates in manual mode because X's free APIs are unreliable, so it generates suggestions rather than fetching live data.

## How it works

```mermaid
graph LR
    A[Brand Context] --> B[Content Ideas]
    B --> C[Search Queries]
    C --> D[Trending Topics]
    D --> E[Engagement Suggestions]
```

### Processing pipeline

1. **Context analysis** - Uses brand profile and keywords
2. **Idea generation** - Creates tweet ideas and threads
3. **Query generation** - Builds search queries for monitoring
4. **Trend analysis** - Identifies relevant trending topics
5. **Suggestion delivery** - Provides actionable engagement ideas

## Key abstractions

| Component | Location | Purpose |
|-----------|----------|---------|
| `XAgent` | `app/services/agents/x_agent.py` | Main agent orchestrator |
| `ContentGenerator` | Service component | Tweet/thread generation |

## Integration points

### Inputs
- Brand voice and keywords
- Business domain
- Current trends (manual input)

### Outputs
- Tweet ideas and threads
- Search queries for monitoring
- Engagement strategy suggestions
- Hashtag recommendations

### Consumers
- **Content Studio** - Displays X content ideas
- **Manual import** - Users copy ideas to X

## Configuration

### Content types
- Single tweets
- Thread ideas
- Reply suggestions
- Quote tweet opportunities

### Engagement strategies
- Thought leadership
- Community engagement
- Product promotion
- Industry commentary

## Usage examples

### Manual run
1. Go to Content Studio
2. Select "X/Twitter"
3. Click "Generate Ideas"

### API endpoint
```bash
POST /v1/x/generate
{
  "company_id": 1,
  "content_type": "thread"
}
```

## Performance

- **Generation time**: 5-15 seconds
- **Ideas per run**: 10-30
- **Quality**: Depends on LLM provider

## Limitations

- Manual mode only (no live API fetching)
- Cannot track engagement metrics
- Ideas require human judgment
- Trending topics need manual input

---

*360 Flatmates Platform Documentation*
