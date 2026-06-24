# Social AI Reply / RedditFlow

A multi-agent AI marketing platform that finds relevant social opportunities, generates safe drafts, and helps brands grow without spam.

## What is this

Social AI Reply (also called RedditFlow) is a free/open-source-first AI CMO platform. It finds highly relevant posts across Reddit, Hacker News, and more, scores them with a transparent relevance engine, and drafts helpful replies. The platform does not auto-post to Reddit or any other service. All posting is manual.

## Who uses it

- **Marketing teams** looking for organic engagement opportunities
- **Content creators** wanting to find relevant discussions
- **SEO professionals** monitoring brand mentions and opportunities
- **Developers** building marketing automation tools

## Core capabilities

**Multi-agent system** with 10 specialized agents:
- Brand Brain analyzes your website and builds keyword intelligence
- Reddit Agent finds relevant Reddit posts using free public APIs
- Hacker News Agent monitors HN for technical discussions
- SEO Agent crawls your site and finds optimization opportunities
- GEO Agent scores AI search visibility readiness
- Articles Agent generates SEO article briefs
- X/Twitter Agent creates content ideas and search queries
- LinkedIn Agent generates professional post ideas
- UGC Agent creates short video briefs
- Technical SEO Agent performs code-level website audits

**Transparent relevance scoring** with weighted formula:
- Keywords (25%) + semantic similarity (30%) + intent (20%) + pain points (10%) + source fit (10%) + freshness (5%)
- Hard reject for spam, jobs, and unrelated content
- Every kept post shows why it's relevant

**Flexible LLM integration**:
- Gemini (default) for high-quality AI
- OpenAI, Claude, Perplexity as alternatives
- Ollama for local LLM usage
- Template fallback for zero-cost operation

## Tech stack

- **Backend**: FastAPI + Python 3.11 + Supabase Postgres
- **Frontend**: Next.js 16 + React 19 + Tailwind CSS v4 + shadcn/ui
- **Auth**: Supabase Auth with JWT
- **Embeddings**: scikit-learn TF-IDF (default) + optional sentence-transformers
- **LLM**: Modular provider system (Gemini, OpenAI, Claude, Perplexity, Ollama, Template)

## Quick links

- [Architecture](architecture.md) - System design and component relationships
- [Getting started](getting-started.md) - Prerequisites, installation, and setup
- [Glossary](glossary.md) - Project-specific terms and definitions
- [How to contribute](../how-to-contribute/index.md) - Development workflow and conventions

---

*360 Flatmates Platform Documentation*
