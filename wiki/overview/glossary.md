# Glossary

Project-specific terms and definitions for Social AI Reply.

## Core concepts

**Opportunity**
A relevant social media post (Reddit, Hacker News, etc.) that has been discovered and scored by the platform. Opportunities are the primary unit of work.

**Relevance Score**
A weighted score (0-100) indicating how relevant a post is to your brand. Calculated using keywords, semantic similarity, intent, pain points, source fit, and freshness.

**Scan**
The process of discovering new opportunities from social media platforms. Scans can be triggered manually or via scheduler.

**Agent**
A specialized AI component that performs a specific marketing task (e.g., Reddit discovery, SEO analysis, content generation).

**Brand Brain**
The system that analyzes your website, extracts product intelligence, and builds a keyword universe for your brand.

## Technical terms

**LLM Provider**
An AI language model service (Gemini, OpenAI, Claude, Perplexity, Ollama) used for content generation and analysis.

**Embedding Service**
Converts text into numerical vectors for semantic similarity comparison. Uses TF-IDF by default.

**Relevance Engine**
The scoring algorithm that evaluates opportunities based on multiple weighted factors.

**Scheduler**
Orchestrates agent runs on manual, daily, or cron schedules.

**Copilot**
The LLM-driven system that generates replies and posts for opportunities.

## Domain objects

**Workspace**
The top-level organizational unit. Users belong to workspaces, and projects belong to workspaces.

**Project**
A specific brand or campaign within a workspace. Contains its own set of opportunities, prompts, and settings.

**Brand Profile**
Analysis of a brand's website, including product intelligence, keywords, and voice characteristics.

**Prompt Template**
Custom instructions that guide LLM generation for replies or posts.

**Voice Profile**
Specific writing style and tone guidelines for generating content.

## Platform terms

**Reddit Agent**
Specialized agent for discovering relevant Reddit posts using public APIs.

**Hacker News Agent**
Agent that monitors Hacker News for technical and product discussions.

**SEO Agent**
Agent that crawls websites and identifies SEO issues and keyword gaps.

**GEO Agent**
Agent that scores AI search visibility readiness and suggests content gaps.

**Articles Agent**
Agent that generates SEO article briefs from identified gaps.

**X Agent**
Agent that generates X/Twitter content ideas and search queries (manual mode).

**LinkedIn Agent**
Agent that generates professional LinkedIn post ideas (manual mode).

**UGC Agent**
Agent that creates short video briefs from pain points.

**Technical SEO Agent**
Agent that performs code-level website audits with fix suggestions.

## Data flow terms

**Scan Run**
A single execution of the discovery process, which may produce multiple opportunities.

**Draft**
A generated reply or post for an opportunity, ready for manual review and posting.

**Feedback Loop**
The system that learns from approve/reject actions to improve future scoring.

**Score Feedback**
User feedback on opportunity relevance that calibrates future scoring.

## Infrastructure terms

**Supabase**
The backend-as-a-service platform providing authentication, database, and real-time features.

**FastAPI**
The Python web framework used for the backend API.

**Next.js**
The React framework used for the frontend application.

**Tailwind CSS**
The utility-first CSS framework used for styling.

**shadcn/ui**
The component library built on `@base-ui/react` used for UI primitives.

## Configuration terms

**Environment Variables**
Configuration values set in `.env` files or deployment environment.

**CORS Origins**
Allowed cross-origin request origins for the frontend.

**Rate Limiting**
Operational safeguards that limit request frequency (not commercial quotas).

**Feature Flags**
Configuration toggles that enable or disable specific features.

## Business terms

**CMO**
Chief Marketing Officer. The platform is sometimes referred to as an "AI CMO."

**Organic Engagement**
Authentic, non-paid interactions with relevant communities.

**Brand Authority**
Establishing credibility and expertise in relevant discussions.

**Content Workflows**
Automated processes for creating and managing marketing content.

---

*360 Flatmates Platform Documentation*
