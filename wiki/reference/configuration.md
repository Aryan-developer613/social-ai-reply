# Configuration

Environment variables, settings, and configuration options for Social AI Reply.

## Backend configuration

### Required variables

```bash
# Supabase
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SECRET_KEY=your_service_role_key
SUPABASE_PUBLISHABLE_KEY=your_anon_key
SUPABASE_JWT_SECRET=your_jwt_secret

# Security
ENCRYPTION_KEY=your_encryption_key

# CORS
FRONTEND_URL=http://localhost:3000
CORS_ORIGINS_RAW=http://localhost:3000
```

### Optional variables

```bash
# LLM providers
GEMINI_API_KEY=your_gemini_key
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_claude_key
PERPLEXITY_API_KEY=your_perplexity_key
OLLAMA_BASE_URL=http://localhost:11434
LLM_PROVIDER=gemini

# Reddit integration
REDDIT_CLIENT_ID=your_reddit_id
REDDIT_CLIENT_SECRET=your_reddit_secret
REDDIT_REDIRECT_URI=http://localhost:8000/callback

# Application
ENVIRONMENT=development
WEB_CONCURRENCY=1
LOG_LEVEL=INFO

# Embeddings
EMBEDDING_MODEL=tfidf
RELEVANCE_THRESHOLD=70
SEMANTIC_THRESHOLD=0.45
DEFAULT_LOOKBACK_DAYS=7
```

## Frontend configuration

### Environment variables

```bash
# API
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://xxxxx.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=your_anon_key
```

### Configuration files

- `web/next.config.mjs` - Next.js configuration
- `web/tailwind.config.ts` - Tailwind CSS configuration
- `web/tsconfig.json` - TypeScript configuration

## Settings module

### `app/core/config.py`

Uses pydantic-settings for typed configuration:

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    supabase_url: str = ""
    supabase_secret_key: str = ""
    supabase_publishable_key: str = ""
    supabase_jwt_secret: str = ""
    
    # LLM
    llm_provider: str = "gemini"
    gemini_api_key: str = ""
    openai_api_key: str = ""
    
    # App
    environment: str = "development"
    frontend_url: str = "http://localhost:3000"
    cors_origins_raw: str = "http://localhost:3000"
    
    model_config = SettingsConfigDict(env_file=".env")
```

### Usage in code

```python
from app.core.config import get_settings

settings = get_settings()
if settings.environment == "production":
    # Production-specific logic
    pass
```

## Rate limiting

### Configuration

In `app/middleware.py`:

```python
RATE_LIMITS = {
    "scan": 5,        # requests per 60s
    "generate": 10,   # requests per 60s
    "auth": 10,       # requests per 300s
    "default": 60,    # requests per 60s
}
```

### Customization

Rate limits are configurable per endpoint. Modify `app/middleware.py` to adjust limits.

## LLM configuration

### Provider selection

```bash
LLM_PROVIDER=gemini  # or openai, claude, perplexity, ollama
```

### Provider-specific settings

```bash
# Gemini
GEMINI_API_KEY=your_key

# OpenAI
OPENAI_API_KEY=your_key
OPENAI_BASE_URL=https://api.openai.com/v1  # Custom endpoint

# Claude
ANTHROPIC_API_KEY=your_key

# Perplexity
PERPLEXITY_API_KEY=your_key

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
```

## Database configuration

### Supabase settings

```bash
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SECRET_KEY=your_service_role_key
SUPABASE_PUBLISHABLE_KEY=your_anon_key
```

### Connection pooling

Supabase handles connection pooling automatically. The client forces HTTP/1.1 to avoid stale connections.

## Deployment configuration

### Railway

- `railway.toml` - Deployment configuration
- `nixpacks.toml` - Build configuration

### Netlify

- `netlify.toml` - Build and deployment configuration

## Development configuration

### Local development

```bash
# Backend
cp .env.example .env
# Edit .env with your credentials

# Frontend
cd web
cp .env.local.example .env.local
# Edit .env.local with your credentials
```

### Environment switching

```bash
# Development
ENVIRONMENT=development

# Production
ENVIRONMENT=production
```

## Feature flags

### Current flags

- `USE_LEGACY_SCORING` - Use legacy relevance scoring
- `ENFORCE_PLAN_LIMITS` - Enforce usage limits (currently false)

### Adding new flags

1. Add to `app/core/config.py`
2. Use in code: `if settings.new_flag:`
3. Document in `.env.example`

## Configuration validation

### Startup validation

The application validates configuration on startup:

```python
@model_validator(mode="after")
def validate_production_settings(self) -> "Settings":
    if self.environment == "production" and not self.supabase_url:
        raise ValueError("SUPABASE_URL is required in production.")
    return self
```

### Runtime validation

Some settings are validated at runtime with appropriate error messages.

---

*360 Flatmates Platform Documentation*
