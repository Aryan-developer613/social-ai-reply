# UGC Agent

Creates short video briefs from pain points and customer testimonials.

## Purpose

The UGC Agent generates briefs for user-generated content, particularly short-form videos. It identifies customer pain points and creates structured briefs for video content creation.

## How it works

```mermaid
graph LR
    A[Pain Points] --> B[Brief Generation]
    B --> C[Video Structure]
    C --> D[Script Outline]
    D --> E[Production Notes]
    E --> F[Video Brief]
```

### Processing pipeline

1. **Pain point analysis** - Identifies customer challenges from opportunities
2. **Brief creation** - Structures video content around pain points
3. **Script generation** - Creates outline for video scripts
4. **Production notes** - Adds filming and editing guidance
5. **Brief delivery** - Saves brief for content creators

## Key abstractions

| Component | Location | Purpose |
|-----------|----------|---------|
| `UGCAgent` | `app/services/agents/ugc_agent.py` | Main agent orchestrator |
| `VideoBriefGenerator` | Service component | Brief creation logic |

## Integration points

### Inputs
- Customer pain points from opportunities
- Product benefits and features
- Brand voice guidelines

### Outputs
- Video briefs with scripts
- Production guidelines
- Platform recommendations
- Hashtag suggestions

### Consumers
- **Content Studio** - Displays UGC briefs
- **Video creators** - Uses briefs for production

## Configuration

### Video formats
- TikTok (15-60 seconds)
- Instagram Reels (15-60 seconds)
- YouTube Shorts (60 seconds)
- LinkedIn Video (30-90 seconds)

### Brief components
- Hook (first 3 seconds)
- Problem statement
- Solution presentation
- Call to action
- Production notes

## Usage examples

### Manual run
1. Go to Content Studio
2. Select "UGC Briefs"
3. Click "Generate Briefs"

### API endpoint
```bash
POST /v1/ugc/generate
{
  "company_id": 1,
  "video_format": "tiktok"
}
```

## Performance

- **Generation time**: 10-20 seconds per brief
- **Briefs per run**: 5-15
- **Quality**: Depends on LLM provider

## Limitations

- Briefs require human creativity for execution
- Cannot guarantee video performance
- Production quality depends on creators
- Platform trends change rapidly

---

*360 Flatmates Platform Documentation*
