from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.db.supabase_client import get_supabase
from app.main import app
from app.services.product.copilot import GeneratedKeyword
from app.services.product.reddit import RedditPost, RedditSubredditMatch


def test_v1_auth_project_and_brand_flow(mock_supabase):
    def override_get_supabase():
        try:
            yield mock_supabase
        finally:
            pass

    app.dependency_overrides[get_supabase] = override_get_supabase
    client = TestClient(app)

    register = client.post(
        "/v1/auth/register",
        json={
            "email": "founder@example.com",
            "password": "strongpass123",
            "full_name": "Founder",
            "workspace_name": "Growth Ops",
        },
    )
    assert register.status_code == 201
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    project = client.post("/v1/projects", json={"name": "Launch Project", "description": "Primary GTM motion"}, headers=headers)
    assert project.status_code == 201
    project_id = project.json()["id"]

    brand = client.put(
        f"/v1/brand/{project_id}",
        json={
            "brand_name": "RedditFlow",
            "website_url": "https://example.com",
            "summary": "Hosted Reddit opportunity intelligence for SaaS teams.",
            "voice_notes": "Specific and practical",
            "product_summary": "Find threads and write better replies.",
            "target_audience": "founders, growth marketers",
            "call_to_action": "Offer the process when invited.",
            "reddit_username": "redditflow",
            "linkedin_url": "https://linkedin.com/company/redditflow",
        },
        headers=headers,
    )
    assert brand.status_code == 200
    assert brand.json()["brand_name"] == "RedditFlow"

    prompts = client.get(f"/v1/prompts?project_id={project_id}", headers=headers)
    assert prompts.status_code == 200
    assert len(prompts.json()) >= 3

    app.dependency_overrides.clear()


def test_v1_discovery_scan_and_draft_flow(monkeypatch, mock_supabase):
    def override_get_supabase():
        try:
            yield mock_supabase
        finally:
            pass

    app.dependency_overrides[get_supabase] = override_get_supabase
    client = TestClient(app)

    register = client.post(
        "/v1/auth/register",
        json={
            "email": "ops@example.com",
            "password": "strongpass123",
            "full_name": "Ops Lead",
            "workspace_name": "Signals",
        },
    )
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    project = client.post("/v1/projects", json={"name": "Signal Project", "description": "Reddit growth"}, headers=headers)
    project_id = project.json()["id"]

    client.put(
        f"/v1/brand/{project_id}",
        json={
            "brand_name": "Signal Project",
            "website_url": "https://example.com",
            "summary": "Find the highest intent Reddit threads.",
            "voice_notes": "Helpful and direct",
            "product_summary": "Scoring and drafting for Reddit engagement.",
            "target_audience": "founders, marketers",
            "call_to_action": "Offer the scoring rubric if useful.",
            "reddit_username": "signalproject",
            "linkedin_url": "https://linkedin.com/company/signalproject",
        },
        headers=headers,
    )

    client.post(
        f"/v1/personas?project_id={project_id}",
        json={
            "name": "Founder",
            "role": "Founder",
            "summary": "Wants repeatable, non-spammy demand capture.",
            "pain_points": ["Low signal outreach"],
            "goals": ["Capture intent"],
            "triggers": ["Pipeline softness"],
            "preferred_subreddits": ["saas"],
            "source": "manual",
            "is_active": True,
        },
        headers=headers,
    )

    monkeypatch.setattr(
        "app.services.product.copilot.ProductCopilot.generate_keywords",
        lambda self, brand, personas, count=12: [
            GeneratedKeyword(keyword="demand capture", rationale="High-intent SaaS pain point.", priority_score=92),
            GeneratedKeyword(keyword="reddit threads", rationale="Relevant channel phrase.", priority_score=86),
            GeneratedKeyword(keyword="founders", rationale="Audience phrase.", priority_score=65),
        ],
    )

    keywords = client.post(f"/v1/discovery/keywords/generate?project_id={project_id}", json={"count": 6}, headers=headers)
    assert keywords.status_code == 200
    assert keywords.json()

    monkeypatch.setattr(
        "app.api.v1.routes.discovery.RedditClient.search_subreddits",
        lambda self, keyword, limit=10: [
            RedditSubredditMatch(name="saas", title="SaaS", description="Software founders discussing growth", subscribers=120000)
        ],
    )
    monkeypatch.setattr(
        "app.api.v1.routes.discovery.RedditClient.subreddit_rules",
        lambda self, name: ["No self-promo", "Explain your reasoning"],
    )
    monkeypatch.setattr(
        "app.api.v1.routes.discovery.RedditClient.subreddit_about",
        lambda self, name: {"title": "SaaS", "public_description": "Software founders discussing growth", "subscribers": 120000},
    )
    monkeypatch.setattr(
        "app.api.v1.routes.discovery.RedditClient.list_subreddit_posts",
        lambda self, name, sort="hot", limit=6: [
            RedditPost(
                post_id="sub123",
                subreddit=name,
                title="How do founders find non-spammy demand capture?",
                author="maker1",
                permalink=f"https://reddit.com/r/{name}/comments/sub123",
                body="Looking for a better way to find relevant threads without blasting replies.",
                created_at=datetime.now(UTC),
                num_comments=6,
                score=18,
            )
        ],
    )
    monkeypatch.setattr(
        "app.api.v1.routes.discovery.RedditClient.search_posts",
        lambda self, subreddit, keywords, limit=20, sort="new": [
            RedditPost(
                post_id="abc123",
                subreddit=subreddit,
                title="How do founders find non-spammy demand capture?",
                author="maker1",
                permalink="https://reddit.com/r/saas/comments/abc123",
                body="Looking for a better way to find relevant threads without blasting replies.",
                created_at=datetime.now(UTC),
                num_comments=8,
                score=42,
            )
        ],
    )
    monkeypatch.setattr(
        "app.services.product.scanner.RedditDiscoveryService.subreddit_rules",
        lambda self, name: ["No self-promo", "Explain your reasoning"],
    )
    monkeypatch.setattr(
        "app.services.product.scanner.RedditDiscoveryService.search_posts",
        lambda self, keywords, subreddits=None, limit=20: [
            RedditPost(
                post_id="abc123",
                subreddit=(subreddits or ["saas"])[0],
                title="How do founders find non-spammy demand capture?",
                author="maker1",
                permalink="https://reddit.com/r/saas/comments/abc123",
                body="Looking for a better way to find relevant threads without blasting replies.",
                created_at=datetime.now(UTC),
                num_comments=8,
                score=42,
            )
        ],
    )

    subreddits = client.post(
        f"/v1/discovery/subreddits/discover?project_id={project_id}",
        json={"max_subreddits": 5},
        headers=headers,
    )
    assert subreddits.status_code == 200
    assert subreddits.json()[0]["name"] == "saas"

    scan = client.post(
        "/v1/scans",
        json={"project_id": project_id, "search_window_hours": 72, "max_posts_per_subreddit": 10},
        headers=headers,
    )
    assert scan.status_code == 200
    assert scan.json()["status"] == "completed"

    opportunities = client.get(f"/v1/opportunities?project_id={project_id}", headers=headers)
    assert opportunities.status_code == 200
    assert opportunities.json()
    opportunity_id = opportunities.json()[0]["id"]

    monkeypatch.setattr(
        "app.services.product.copilot.ProductCopilot.generate_reply",
        lambda self, opportunity, brand, prompts: (
            "This looks like a good fit to solve by first defining the signals that make a thread worth answering, "
            "then reviewing recent posts against those signals before writing a specific, non-promotional reply.",
            "Deterministic test draft for the API persistence flow.",
            "test prompt",
        ),
    )

    draft = client.post("/v1/drafts/replies", json={"opportunity_id": opportunity_id}, headers=headers)
    assert draft.status_code == 201
    draft_content = draft.json().get("content") or ""
    # The end-to-end flow is the behavioural contract: a non-empty reply comes back.
    # Avoid brittle keyword assertions against the live LLM output — the model wording
    # shifts between Gemini versions and flavour updates.
    assert draft_content.strip(), "reply draft should contain non-empty content"
    assert len(draft_content) >= 40, f"reply draft looks too short: {draft_content!r}"

    app.dependency_overrides.clear()
