# Getting started

This guide covers prerequisites, installation, and running Social AI Reply locally.

## Prerequisites

### Backend
- Python 3.11 or higher
- `uv` package manager (recommended) or `pip`
- Supabase account and project
- Git

### Frontend
- Node.js 20 or higher
- npm or yarn
- Git

### Optional
- Gemini API key (for better AI quality)
- OpenAI API key (alternative LLM)
- Ollama (for local LLM)
- Reddit API credentials (for account connection)

## Backend setup

### 1. Clone and configure
```bash
git clone https://github.com/360ghar/social-ai-reply.git
cd social-ai-reply
cp .env.example .env
```

### 2. Edit `.env` with your credentials
Required variables:
- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_SECRET_KEY` - Supabase service role key
- `SUPABASE_PUBLISHABLE_KEY` - Supabase anon key
- `SUPABASE_JWT_SECRET` - Supabase JWT secret
- `ENCRYPTION_KEY` - Encryption key for sensitive data
- `FRONTEND_URL` - Frontend URL (e.g., http://localhost:3000)
- `CORS_ORIGINS_RAW` - Allowed origins (e.g., http://localhost:3000)

Optional for better AI:
- `GEMINI_API_KEY` - Gemini API key (default provider)
- `OPENAI_API_KEY` - OpenAI API key
- `OLLAMA_BASE_URL` - Ollama server URL

### 3. Install dependencies
```bash
uv sync --extra dev
```

### 4. Apply database migrations
Run the SQL migration files in `app/db/migrations/` in your Supabase SQL Editor, in order:
```bash
# List migration files to see what needs to be applied
ls app/db/migrations/
```
Apply `001_multi_agent_platform.sql` first, then any additional migration files in chronological order.

### 5. Start the backend
```bash
uv run uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.

## Frontend setup

### 1. Navigate to web directory
```bash
cd web
```

### 2. Configure environment
```bash
cp .env.local.example .env.local
```

Edit `.env.local` with:
- `NEXT_PUBLIC_API_BASE_URL` - Backend URL (e.g., http://localhost:8000)
- `NEXT_PUBLIC_SUPABASE_URL` - Supabase project URL
- `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` - Supabase anon key

### 3. Install dependencies
```bash
npm install
```

### 4. Start the frontend
```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`.

## Verification

### Backend health check
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "checks": {
    "api": "ok",
    "database": "ok"
  }
}
```

### Frontend check
Open `http://localhost:3000` in your browser. You should see the login page.

## Running tests

### Backend tests
```bash
uv run pytest -q
```

### Frontend type check and build
```bash
cd web
npm run build
```

## Development workflow

### Backend development
1. Start the backend with `--reload` for auto-reloading
2. Make changes to Python files
3. Tests run automatically on save (if using IDE integration)
4. Run `uv run ruff check app/ tests/` for linting

### Frontend development
1. Start the frontend with `npm run dev`
2. Make changes to TypeScript/React files
3. Browser auto-refreshes on changes
4. Run `npm run build` to check types

## Common issues

### Backend won't start
- Check that all required environment variables are set
- Verify Supabase credentials are correct
- Ensure port 8000 is not in use

### Frontend won't start
- Check that `NEXT_PUBLIC_API_BASE_URL` points to running backend
- Verify Supabase credentials in `.env.local`
- Ensure port 3000 is not in use

### Database connection issues
- Verify Supabase URL and keys
- Check that migrations have been applied
- Ensure your IP is allowed in Supabase settings

## Next steps

- [Architecture](architecture.md) - Understand system design
- [Glossary](glossary.md) - Learn project terminology
- [How to contribute](../how-to-contribute/index.md) - Start developing

---

*360 Flatmates Platform Documentation*
