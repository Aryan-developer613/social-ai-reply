# Reference

Configuration, data models, and dependencies for Social AI Reply.

## Sections

### [Configuration](configuration.md)
Environment variables, settings, and configuration options.

### [Data models](data-models.md)
Database schema, Pydantic models, and type definitions.

### [Dependencies](dependencies.md)
Python and Node.js dependencies with versions and purposes.

## Quick reference

### Environment variables
```bash
# Required
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SECRET_KEY=your_key
SUPABASE_PUBLISHABLE_KEY=your_key
SUPABASE_JWT_SECRET=your_secret
ENCRYPTION_KEY=your_key
FRONTEND_URL=http://localhost:3000
CORS_ORIGINS_RAW=http://localhost:3000

# Optional (LLM)
GEMINI_API_KEY=your_key
OPENAI_API_KEY=your_key
ANTHROPIC_API_KEY=your_key
PERPLEXITY_API_KEY=your_key
OLLAMA_BASE_URL=http://localhost:11434
LLM_PROVIDER=gemini

# Optional (Reddit)
REDDIT_CLIENT_ID=your_id
REDDIT_CLIENT_SECRET=your_secret
REDDIT_REDIRECT_URI=http://localhost:8000/callback
```

### Database tables
- `account_users` - User accounts
- `workspaces` - Workspaces
- `projects` - Projects
- `brand_profiles` - Brand intelligence
- `opportunities` - Discovered opportunities
- `reply_drafts` - Generated replies
- `agent_runs` - Agent execution history

### API endpoints
- `POST /v1/auth/register` - Register
- `POST /v1/auth/login` - Login
- `GET /v1/projects` - List projects
- `GET /v1/opportunities` - List opportunities
- `POST /v1/agents/run` - Run agent

## Tools

### Development
- **uv** - Python package manager
- **npm** - Node.js package manager
- **Ruff** - Python linter
- **ESLint** - TypeScript linter

### Testing
- **pytest** - Python testing
- **Vitest** - TypeScript testing
- **curl** - API testing

### Deployment
- **Railway** - Backend hosting
- **Netlify** - Frontend hosting
- **Supabase** - Database and auth

## Resources

### Documentation
- [FastAPI docs](https://fastapi.tiangolo.com/)
- [Next.js docs](https://nextjs.org/docs)
- [Supabase docs](https://supabase.com/docs)
- [Tailwind CSS docs](https://tailwindcss.com/docs)

### Community
- GitHub Issues
- Discord community
- Stack Overflow

---

*360 Flatmates Platform Documentation*
