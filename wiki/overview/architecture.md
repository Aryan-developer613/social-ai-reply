# Architecture

Social AI Reply uses a layered architecture with clear separation between frontend, backend, and infrastructure components.

## System overview

```mermaid
graph TD
    subgraph Frontend ["Next.js 16 Frontend"]
        UI[React 19 UI]
        State[Zustand State]
        API[API Client]
    end
    
    subgraph Backend ["FastAPI Backend"]
        Routes[API Routes]
        Services[Services Layer]
        DB[Database Layer]
    end
    
    subgraph Infrastructure ["Infrastructure"]
        LLM[LLM Providers]
        Scheduler[Agent Scheduler]
        Embeddings[Embedding Service]
    end
    
    subgraph External ["External Services"]
        Supabase[Supabase Postgres]
        Reddit[Reddit API]
        HN[Hacker News API]
    end
    
    UI --> State
    State --> API
    API --> Routes
    Routes --> Services
    Services --> DB
    DB --> Supabase
    Services --> LLM
    Services --> Scheduler
    Services --> Embeddings
    Services --> Reddit
    Services --> HN
```

## Backend architecture

The backend follows a clean layered architecture:

### API layer (`app/api/v1/routes/`)
- FastAPI routers organized by domain (auth, projects, discovery, drafts, etc.)
- All routes live under `/v1` prefix
- Handle HTTP request/response, validation, and authentication
- Delegate business logic to services layer

### Services layer (`app/services/`)
- **Product services** (`product/`): Core business logic
  - Pipeline orchestration (scan → opportunity → draft)
  - LLM-driven copilot for reply/post generation
  - Reddit scraping and opportunity detection
  - Relevance scoring and filtering
  - Account safety and posting controls
- **Agent services** (`agents/`): 10 specialized marketing agents
  - Each agent focuses on a specific channel or task
  - Agents run independently via scheduler
- **Infrastructure services** (`infrastructure/`): Technical foundations
  - LLM provider abstraction
  - Embedding service
  - Scheduler and orchestration
  - HTTP budget management

### Database layer (`app/db/`)
- Supabase Postgres via `supabase-py` client
- Table operations organized by domain in `tables/` directory
- Singleton client with FastAPI dependency injection
- No ORM, direct Supabase SDK usage

## Frontend architecture

```mermaid
graph LR
    subgraph Pages ["Next.js App Router"]
        Public[Public Pages]
        Auth[Auth Pages]
        App[App Pages]
    end
    
    subgraph Components ["React Components"]
        UI[shadcn/ui Primitives]
        AppShell[App Shell]
        AuthProvider[Auth Provider]
    end
    
    subgraph State ["State Management"]
        AuthStore[Auth Store]
        ProjectStore[Project Store]
        UIStore[UI Store]
    end
    
    subgraph API ["API Layer"]
        Client[API Client]
        Domain[Domain Modules]
    end
    
    Pages --> Components
    Components --> State
    State --> API
    Client --> Domain
```

### Routing
- **Public pages**: Landing, login, register, password reset
- **App pages**: Authenticated routes under `/app/`
- **Shared layout**: App shell with sidebar navigation

### State management
- **Auth store**: JWT token, user info, workspace
- **Project store**: Selected project ID
- **UI store**: Sidebar and notification panel toggles

### Styling
- Tailwind CSS v4 with design tokens
- shadcn/ui components built on `@base-ui/react`
- Class variance authority for component variants

## Data flow

### Opportunity discovery flow
```mermaid
sequenceDiagram
    participant Scheduler
    participant Agent
    participant Scanner
    participant Relevance
    participant Database
    
    Scheduler->>Agent: Trigger agent run
    Agent->>Scanner: Scan for opportunities
    Scanner->>Scanner: Fetch from Reddit/HN
    Scanner->>Relevance: Score opportunities
    Relevance->>Relevance: Apply weighted formula
    Relevance->>Database: Store scored opportunities
    Database-->>Agent: Return opportunities
    Agent-->>Scheduler: Complete run
```

### Reply generation flow
```mermaid
sequenceDiagram
    participant User
    participant API
    participant Copilot
    participant LLM
    participant Database
    
    User->>API: Request reply draft
    API->>Copilot: Generate reply
    Copilot->>Database: Fetch opportunity & brand
    Copilot->>LLM: Call with context
    LLM-->>Copilot: Return draft
    Copilot->>Database: Store draft
    Copilot-->>API: Return draft
    API-->>User: Show draft
```

## Key abstractions

| Component | Location | Purpose |
|-----------|----------|---------|
| `LLMService` | `app/services/infrastructure/llm/service.py` | Unified facade for LLM operations |
| `VisibilityRunner` | `app/services/infrastructure/llm/service.py` | Multi-provider prompt execution |
| `RelevanceEngine` | `app/services/product/relevance_v2.py` | Weighted scoring and filtering |
| `EmbeddingService` | `app/services/infrastructure/embeddings/` | Local TF-IDF embeddings |
| `Scheduler` | `app/services/infrastructure/scheduler/` | Agent orchestration |
| `AuthProvider` | `web/components/auth/auth-provider.tsx` | Frontend auth state |

## Deployment architecture

```mermaid
graph LR
    subgraph Railway ["Railway (Backend)"]
        FastAPI[FastAPI App]
        Postgres[Supabase Postgres]
    end
    
    subgraph Netlify ["Netlify (Frontend)"]
        NextJS[Next.js App]
    end
    
    subgraph Users ["Users"]
        Browser[Web Browser]
    end
    
    Browser --> NextJS
    NextJS --> FastAPI
    FastAPI --> Postgres
```

- **Backend**: Deployed to Railway from repo root
- **Frontend**: Deployed to Netlify from `web/` directory
- **Database**: Supabase Postgres (managed service)

---

*360 Flatmates Platform Documentation*
