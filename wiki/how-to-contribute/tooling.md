# Tooling

Build system, linters, code generators, and CI tooling in Social AI Reply.

## Build system

### Backend
- **uv** for Python package management
- **FastAPI** for API server
- **Uvicorn** for ASGI server

**Commands:**
```bash
# Install dependencies
uv sync --extra dev

# Run development server
uv run uvicorn app.main:app --reload

# Run production server
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Frontend
- **npm** for package management
- **Next.js** for React framework
- **TypeScript** for type safety

**Commands:**
```bash
# Install dependencies (from web/ directory)
cd web && npm install

# Run development server
npm run dev

# Build for production
npm run build

# Start production server
npm start
```

## Linters

### Python (Ruff)
- **Target:** Python 3.11
- **Line length:** 120
- **Rules:** E, F, W, I, N, UP, B, SIM, TCH
- **E501 ignored** (line length)

**Commands:**
```bash
# Check linting
uv run ruff check app/ tests/

# Auto-fix linting
uv run ruff check --fix app/ tests/

# Format code
uv run ruff format app/ tests/
```

**Configuration:** `pyproject.toml`
```toml
[tool.ruff]
target-version = "py311"
line-length = 120
select = ["E", "F", "W", "I", "N", "UP", "B", "SIM", "TCH"]
ignore = ["E501"]
```

### TypeScript (ESLint)
- **Config:** Next.js ESLint config
- **Rules:** Strict TypeScript rules

**Commands:**
```bash
# Check linting
npm run lint

# Auto-fix linting
npm run lint -- --fix
```

## Code formatting

### Python (Ruff format)
```bash
# Format code
uv run ruff format app/ tests/

# Check formatting
uv run ruff format --check app/ tests/
```

### TypeScript (Prettier)
```bash
# Format code
npx prettier --write "web/**/*.{ts,tsx,js,jsx}"

# Check formatting
npx prettier --check "web/**/*.{ts,tsx,js,jsx}"
```

## Type checking

### Python (mypy)
- Optional type checking
- Run manually or in CI

```bash
# Check types
uv run mypy app/

# Check with strict mode
uv run mypy --strict app/
```

### TypeScript
- Built into TypeScript compiler
- Run via `npm run build`

```bash
# Type check
npx tsc --noEmit

# Build with type checking
npm run build
```

## Testing tools

### Backend
- **pytest** for testing framework
- **pytest-cov** for coverage
- **pytest-asyncio** for async tests

```bash
# Run tests
uv run pytest -q

# Run with coverage
uv run pytest --cov=app tests/

# Run specific test
uv run pytest tests/unit/test_security.py -v
```

### Frontend
- **Vitest** for unit testing
- **React Testing Library** for component testing

```bash
# Run tests
npm run test

# Run with coverage
npm run test -- --coverage
```

## CI/CD

### GitHub Actions
- **Linting** on every push
- **Testing** on every PR
- **Build verification** for frontend
- **Code coverage** reporting

**Workflow files:** `.github/workflows/`

### Pre-commit hooks
- Run linting before commit
- Run type checks
- Verify test passing

**Setup:**
```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install
```

## Code generation

### API client generation
- OpenAPI specification for API
- Auto-generated client code

### Database migrations
- SQL files in `app/db/migrations/`
- Manual application to Supabase

## Documentation tools

### API documentation
- FastAPI auto-generates OpenAPI docs
- Available at `/docs` and `/redoc`

### Wiki generation
- Factory wiki skill
- Auto-generated documentation

## Development utilities

### Environment management
- `.env` files for configuration
- `.env.local` for frontend local config
- `.env.example` for documentation

### Database tools
- Supabase dashboard for management
- SQL Editor for migrations
- Table editor for data management

## IDE setup

### VS Code
- Recommended extensions:
  - Python
  - Pylance
  - ESLint
  - Prettier
  - Tailwind CSS IntelliSense

### Settings
```json
{
  "python.defaultInterpreterPath": ".venv/bin/python",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true
  }
}
```

## Performance tools

### Backend profiling
- `cProfile` for profiling
- `line_profiler` for line-by-line profiling
- `memory_profiler` for memory usage

### Frontend profiling
- React DevTools Profiler
- Lighthouse for performance auditing
- Bundle analyzer for bundle size

## Security tools

### Dependency scanning
- GitHub Dependabot
- `pip-audit` for Python dependencies
- `npm audit` for Node.js dependencies

### Code scanning
- `bandit` for Python security linting
- ESLint security rules for TypeScript

## Deployment tools

### Railway (backend)
- `railway.toml` configuration
- Nixpacks builder
- Automatic deployments

### Netlify (frontend)
- `netlify.toml` configuration
- Next.js plugin
- Automatic deployments

---

*360 Flatmates Platform Documentation*
