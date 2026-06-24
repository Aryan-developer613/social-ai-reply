# Patterns and conventions

Coding patterns, error handling, and cross-cutting concerns in Social AI Reply.

## Python backend conventions

### Supabase SDK usage (mandatory)
All database operations use the Supabase Python SDK via helpers in `app/db/tables/`. Never use raw SQL or direct ORM access.

**Dependency pattern in routes:**
```python
from supabase import Client
from fastapi import Depends
from app.db.supabase_client import get_supabase

@router.get("/items")
def list_items(supabase: Client = Depends(get_supabase)):
    items = list_items_for_workspace(supabase, workspace_id)
    return [ItemResponse.model_validate(item) for item in items]
```

**Supabase query patterns:**
```python
# Select with filter
result = db.table("opportunities").select("*").eq("project_id", pid).execute()
return result.data[0] if result.data else None

# Insert
result = db.table("projects").insert(data).execute()
return result.data[0]

# Update
result = db.table("workspaces").update(data).eq("id", wid).execute()
return result.data[0] if result.data else None

# Delete
db.table("invitations").delete().eq("id", inv_id).execute()
```

### Pydantic v2 patterns (mandatory)
All request/response schemas use Pydantic v2.

**Response models (from database records):**
```python
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # Required for .model_validate()
    
    id: int
    workspace_id: int
    name: str = Field(min_length=2, max_length=255)
    slug: str
    description: str | None
    status: str
    created_at: datetime
    updated_at: datetime
```

**Request models (from JSON body):**
```python
class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
```

**Validation with model_validator (v2 syntax):**
```python
from pydantic import model_validator

class Settings(BaseSettings):
    supabase_url: str = ""
    supabase_secret_key: str = ""
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    
    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.environment == "production" and not self.supabase_url:
            raise ValueError("SUPABASE_URL is required in production.")
        return self
```

### Type hints for table operations
```python
from typing import Any

def get_entity_by_id(db: Client, entity_id: int) -> dict[str, Any] | None:
    """Get single record or None."""
    result = db.table("entities").select("*").eq("id", entity_id).execute()
    return result.data[0] if result.data else None

def list_entities(db: Client, project_id: int) -> list[dict[str, Any]]:
    """List records."""
    result = db.table("entities").select("*").eq("project_id", project_id).execute()
    return list(result.data)
```

## Error handling

### Custom exception hierarchy
```python
from app.core.exceptions import (
    AppException,
    NotFoundError,
    ForbiddenError,
    ConflictError,
    AuthenticationError,
    BusinessRuleError,
)

# Usage in routes
@router.get("/items/{item_id}")
def get_item(item_id: int):
    item = get_item_by_id(supabase, item_id)
    if not item:
        raise NotFoundError(f"Item {item_id} not found")
    return ItemResponse.model_validate(item)
```

### Error response format
All errors return structured JSON:
```json
{
  "detail": "Error message",
  "error_code": "NOT_FOUND"
}
```

## Frontend conventions

### React 19 patterns
- Use `createRoot` implicitly via Next.js 16 (no legacy `ReactDOM.render`)
- No deprecated APIs (`getDefaultProps`, `propTypes`, `displayName` patterns)
- Class components (like `ErrorBoundary`) work unchanged in React 19
- Server Components are the default; client components use `"use client"` directive

### Type safety
- Error types defined in `web/types/errors.ts`: `ApiError`, `AuthError`, `ValidationError`
- Helper functions: `getErrorMessage()`, `toError()`, `isApiError()`, `isAuthError()`, `isValidationError()`
- All catch blocks use `catch (error: unknown)` with proper type guards
- Zero `: any` types in production frontend code

### State management
- Zustand stores in `web/stores/`
- Auth state: `useAuthStore` → `useAuth` hook
- Project state: `useSelectedProjectId` hook
- UI state: `useUIStore` for sidebar and notifications

## Testing patterns

### Backend tests
- Use Supabase local development or test Supabase project
- Fixtures in `conftest.py`: `client`, `authed_client`, `authed_headers`
- Run with: `uv run pytest -q`

### Frontend tests
- Vitest for unit tests
- Build step serves as type-check: `npm run build`
- Run with: `npm run test`

## Linting

### Python (Ruff)
- Target: Python 3.11
- Line length: 120
- Rules: E, F, W, I, N, UP, B, SIM, TCH
- E501 ignored (line length)
- Run: `uv run ruff check app/ tests/`
- Auto-fix: `uv run ruff check --fix app/ tests/`

### TypeScript
- ESLint with Next.js config
- TypeScript strict mode
- Run: `npm run lint`

## Code organization

### Backend directory structure
```
app/
├── api/v1/routes/     # API endpoints
├── core/              # Config, exceptions, logging
├── db/                # Database layer
├── models/            # Pydantic models
├── schemas/v1/        # Request/response schemas
├── services/          # Business logic
│   ├── agents/        # Marketing agents
│   ├── infrastructure/# Technical services
│   └── product/       # Core business logic
└── utils/             # Utility functions
```

### Frontend directory structure
```
web/
├── app/               # Next.js App Router pages
├── components/        # React components
│   ├── ui/           # shadcn primitives
│   └── auth/         # Auth components
├── lib/              # API client and utilities
├── stores/           # Zustand state stores
├── types/            # TypeScript types
└── styles/           # Global styles
```

## Naming conventions

### Python
- Files: `snake_case.py`
- Classes: `PascalCase`
- Functions: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private: `_prefix` (single underscore)

### TypeScript/React
- Files: `kebab-case.tsx` or `camelCase.ts`
- Components: `PascalCase`
- Functions: `camelCase`
- Constants: `UPPER_SNAKE_CASE` or `camelCase`
- Types/Interfaces: `PascalCase`

## Documentation

### Code comments
- Use docstrings for public functions and classes
- Keep comments concise and focused on "why" not "what"
- Avoid obvious comments that restate the code

### README updates
- Update README.md when adding new features or changing setup
- Keep environment variables documented in `.env.example`

---

*360 Flatmates Platform Documentation*
