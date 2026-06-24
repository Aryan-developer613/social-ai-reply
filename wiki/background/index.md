# Background

Design decisions, pitfalls, and migration context for Social AI Reply.

## Design decisions

### No auto-posting
The platform does not auto-post to Reddit or any social network. All posting is manual. This is a deliberate product decision to:
- Avoid spam and platform violations
- Maintain authenticity and trust
- Give users control over their voice
- Comply with platform terms of service

### Free-first approach
The platform emphasizes free/open-source-first with no paid API dependencies. The default LLM (Gemini) requires an API key, but the template fallback works without any API keys. This ensures:
- Low barrier to entry
- No vendor lock-in
- Community accessibility
- Development flexibility

### Manual mode for X/LinkedIn
X/Twitter and LinkedIn agents operate in manual mode because their free APIs are unreliable. The agents generate content ideas and search queries, but don't fetch live data. This avoids:
- API reliability issues
- Rate limit problems
- Authentication complexity
- Cost unpredictability

### Transparent scoring
The relevance scoring is transparent with clear `reason_relevant` and `rejection_reason` fields. Users can understand why opportunities were kept or rejected. This builds:
- Trust in the system
- Ability to tune scoring
- Debugging capability
- User confidence

## Migration history

### SQLAlchemy to Supabase
The backend migrated from SQLAlchemy ORM to Supabase Python SDK. Key changes:
- All database queries now use `supabase-py`
- No more ORM models
- Direct table operations
- Simpler data access layer

### React 18 to React 19
The frontend was upgraded from React 18 to React 19. Changes:
- Updated package versions
- No code changes required
- Existing patterns compatible
- Improved performance

## Pitfalls

### Database connection
- HTTP/2 connection pooling breaks against Supabase CDN
- Idle pooled connections get closed server-side
- Solution: Force HTTP/1.1 on PostgREST session

### Rate limiting
- In-memory rate limiter is per-process
- Multiple workers multiply effective limits
- Solution: Use shared backend for scaling

### LLM provider fallback
- Template provider works without API keys
- But generates less nuanced content
- Solution: Configure real LLM for best results

### Scheduler limitations
- Uses FastAPI BackgroundTasks
- Not suitable for production scale
- Solution: Consider Celery/RQ for scale

## Technical debt

### Legacy scoring
- `relevance.py` contains legacy scoring logic
- `relevance_v2.py` is the new implementation
- Legacy kept as rollback path
- Controlled by `USE_LEGACY_SCORING` flag

### Frontend styles
- Legacy plain-CSS files under `web/styles/`
- Being phased out in favor of Tailwind
- Some components still use old styles
- Migration ongoing

### Test coverage
- Some areas lack test coverage
- Integration tests limited
- E2E tests manual
- Coverage improving

## Architecture evolution

### Multi-agent system
Started with single Reddit agent, expanded to 10 specialized agents. Each agent:
- Focuses on specific channel
- Runs independently
- Shares relevance engine
- Feeds central feed

### LLM provider system
Evolved from single OpenAI provider to modular system. Benefits:
- Multiple providers supported
- Easy to add new providers
- Graceful fallback
- Cost optimization

### Database layer
Migrated from SQLAlchemy to Supabase SDK. Benefits:
- Simpler queries
- No ORM overhead
- Direct SDK usage
- Better Supabase integration

## Future considerations

### Scalability
- Consider Celery for background tasks
- Redis for shared rate limiting
- Database connection pooling
- CDN for static assets

### Features
- More platform integrations
- Advanced analytics
- Team collaboration
- API marketplace

### Quality
- More test coverage
- Performance optimization
- Security hardening
- Documentation improvement

---

*360 Flatmates Platform Documentation*
