import asyncio
import hashlib
import json
from collections.abc import AsyncGenerator
from typing import Any

from app.services.product.brand_brain import BrandBrain
from app.services.product.docs import generate_markdown_report


def _event(data: dict[str, Any]) -> str:
    """Format a dict as an SSE event line."""
    return f"data: {json.dumps(data)}\n\n"


def _log(msg: str, level: str = "info") -> str:
    return _event({"type": "log", "msg": msg, "level": level})


def _data(key: str, value: Any) -> str:
    return _event({"type": "data", "key": key, "value": value})


def _section(label: str) -> str:
    return _event({"type": "section", "label": label})


async def run_full_pipeline_stream(url: str, workspace: dict, supabase: Any) -> AsyncGenerator[str, None]:
    """
    Zero-Input Master Pipeline.
    Runs enrichment, scraping, relevance scoring, and document generation.
    """
    yield _log(f"Starting master pipeline for {url}…")
    yield _log("Step 1: Auto-Enrichment via URL")

    # Load or create company profile based on the URL
    try:
        from app.db.tables.company import get_company_by_url
        company_profile = get_company_by_url(supabase, workspace["id"], url)
    except Exception as exc:
        yield _log(f"Error fetching company profile: {exc}", "warn")
        company_profile = None

    if not company_profile:
        yield _log("Creating new company profile from URL…")
        from urllib.parse import urlparse
        parsed = urlparse(url if url.startswith("http") else f"https://{url}")
        domain = parsed.netloc.replace("www.", "")
        name_guess = domain.split(".")[0].title()

        result = supabase.table("company_profiles").insert({
            "workspace_id": workspace["id"],
            "name": name_guess,
            "website_url": url,
            "is_active": True,
            "language": "en",
            "features": "",
            "benefits": "",
            "pain_points": "",
            "competitors": "",
        }).execute()
        company_profile = result.data[0] if result.data else None

    if not company_profile:
        yield _event({"type": "error", "msg": "Failed to create company profile."})
        return

    company_id = company_profile.get("id")
    company_name = company_profile.get("name")

    # 0. Load or create Project
    # IMPORTANT: lookup is keyed on company_id (stable FK), not slug.
    # A prior bug looked up by a clean slug ("flipkart") but created with a
    # UUID-suffixed slug ("flipkart-a3f9c2"), so the lookup never matched and
    # every pipeline run silently created a brand-new project. company_id is
    # immune to that class of bug since it's never regenerated per-run.
    try:
        from app.db.tables.projects import (
            create_brand_profile,
            create_project,
            get_brand_profile_by_project,
            get_project_by_company_id,
            get_project_by_slug,
        )
        project_name = company_name
        base_slug = (project_name or "my-project").lower().replace(" ", "-")

        project = get_project_by_company_id(supabase, workspace["id"], company_id) if company_id else None

        # Legacy fallback: a project created before company_id linking existed
        if not project:
            project = get_project_by_slug(supabase, workspace["id"], base_slug)

        if not project:
            yield _log(f"Creating project '{project_name}'…")
            # Only disambiguate the slug if there's an actual collision —
            # don't append a UUID unconditionally, since that's what broke
            # lookups before.
            slug = base_slug
            if get_project_by_slug(supabase, workspace["id"], slug):
                import uuid
                slug = f"{base_slug}-{str(uuid.uuid4())[:6]}"
            project = create_project(supabase, {
                "workspace_id": workspace["id"],
                "company_id": company_id,
                "name": project_name,
                "slug": slug,
                "status": "active"
            })
            # Create the brand profile so the dashboard sees it as configured
            create_brand_profile(supabase, {
                "project_id": project["id"],
                "brand_name": project_name,
                "summary": "",
                "target_audience": "",
                "business_domain": ""
            })
        else:
            yield _log(f"Reusing existing project '{project.get('name', project_name)}' (ID {project['id']})")
            # Self-heal: If project exists but brand profile is missing (e.g. from a past failed run)
            bp = get_brand_profile_by_project(supabase, project["id"])
            if not bp:
                create_brand_profile(supabase, {
                    "project_id": project["id"],
                    "brand_name": project_name,
                    "summary": "",
                    "target_audience": "",
                    "business_domain": ""
                })
    except Exception as exc:
        yield _log(f"Error handling project: {exc}", "warn")
        project = None

    project_id = project.get("id") if project else None

    yield _data("company_id", company_id)
    if project_id:
        yield _data("project_id", project_id)

    # 1. Enrich (BrandBrain)
    yield _section("Crawling Website")
    brain = BrandBrain()
    loop = asyncio.get_running_loop()
    try:
        enriched = await loop.run_in_executor(
            None,
            lambda: brain.analyze_website(url, dict(company_profile), supabase),
        )
        yield _log("Website parsed and intelligence extracted ✓", "success")
    except Exception as exc:
        yield _log(f"Website crawl failed: {exc}", "warn")
        enriched = company_profile

    company_name = enriched.get("name") or company_profile.get("name") or ""
    yield _data("company_name", company_name)
    yield _log(f"Identified Brand: {company_name}")

    # Update company and brand profile with enriched data
    if company_id:
        try:
            from app.db.tables.company import update_company
            update_company(supabase, company_id, {
                "name": company_name,
                "description": enriched.get("description", ""),
                "features": enriched.get("features", ""),
                "benefits": enriched.get("benefits", ""),
                "pain_points": enriched.get("pain_points", ""),
                "target_audience": enriched.get("target_audience", ""),
            })
            if project_id:
                from app.db.tables.projects import get_brand_profile_by_project, update_brand_profile
                bp = get_brand_profile_by_project(supabase, project_id)
                if bp:
                    update_brand_profile(supabase, bp["id"], {
                        "brand_name": company_name,
                        "summary": enriched.get("description", ""),
                        "target_audience": enriched.get("target_audience", "")
                    })
        except Exception as exc:
            yield _log(f"Failed to update company profile: {exc}", "warn")

    # Competitors
    raw_competitors = enriched.get("competitors") or enriched.get("extracted_competitors") or ""
    competitor_list = []
    if isinstance(raw_competitors, str):
        competitor_list = [c.strip() for c in raw_competitors.split(",") if c.strip()]
    elif isinstance(raw_competitors, list):
        competitor_list = raw_competitors

    if competitor_list:
        for comp in competitor_list[:3]:
            yield _log(f"Found competitor: {comp}", "success")

    # Keywords & Personas
    yield _section("Generating Personas & Keywords")
    analysis_project = project if project_id else None

    kws_list = []
    personas_list = []
    saved_personas = []
    kws_db = []

    if analysis_project:
        from app.db.tables.discovery import list_personas_for_project
        from app.services.product.discovery import get_project_search_keywords
        saved_personas = list_personas_for_project(supabase, analysis_project["id"]) or []
        kws_db = get_project_search_keywords(supabase, analysis_project, limit=10)

    if enriched:
        yield _log("Generating target personas…")
        from app.services.product.copilot import suggest_personas
        personas_list = await loop.run_in_executor(
            None,
            lambda: suggest_personas({
                "brand_name": enriched.get("name", ""),
                "product_summary": enriched.get("description", ""),
                "target_audience": enriched.get("target_audience", ""),
            }),
        )
        yield _log(f"Generated {len(personas_list)} personas.", "success")
        yield _data("personas_count", len(personas_list))

        if project_id and not saved_personas:
            try:
                from app.db.tables.discovery import create_persona
                for p in personas_list:
                    create_persona(supabase, {
                        "project_id": project_id,
                        "name": p.get("name", "Target User"),
                        "role": p.get("role", "User"),
                        "summary": p.get("summary", ""),
                        "pain_points": p.get("pain_points", []),
                        "goals": p.get("goals", []),
                        "is_active": True,
                        "source": "auto"
                    })
            except Exception as exc:
                yield _log(f"Failed to save personas: {exc}", "warn")

    if enriched:
        yield _log("Generating search keywords…")
        from app.services.product.copilot import generate_keywords
        generated = await loop.run_in_executor(
            None,
            lambda: generate_keywords({
                "brand_name": enriched.get("name", ""),
                "summary": enriched.get("extracted_summary", ""),
                "product_summary": enriched.get("description", ""),
            }, personas_list, count=30),  # Generate 30 keywords directly
        )

        new_kws = [
            {
                "keyword": kw.keyword if hasattr(kw, "keyword") else str(kw),
                "type": getattr(kw, "category", "core") if hasattr(kw, "category") else "core",
                "priority": getattr(kw, "priority_score", 50) if hasattr(kw, "priority_score") else 50
            }
            for kw in generated
        ]

        # Merge avoiding duplicates
        existing_kw_strs = {k.keyword.lower() if hasattr(k, "keyword") else str(k).lower() for k in kws_db}
        for kw in new_kws:
            if kw["keyword"].lower() not in existing_kw_strs:
                kws_list.append(kw)

        if not kws_list and not kws_db:
            kws_list = [{"keyword": company_name, "type": "core", "priority": 50}]

        yield _log(f"Generated {len(kws_list)} expanded keywords.", "success")
        yield _data("keywords_count", len(kws_list))

        if project_id:
            try:
                from app.db.tables.discovery import create_discovery_keyword
                for kw in kws_list:
                    create_discovery_keyword(supabase, {
                        "project_id": project_id,
                        "keyword": kw["keyword"],
                        "category": kw["type"],
                        "priority_score": kw["priority"],
                        "source": "auto",
                        "is_active": True
                    })
            except Exception as exc:
                yield _log(f"Failed to save keywords: {exc}", "warn")

        # Combine old and new for the rest of the pipeline
        kws_list = kws_list or kws_db
    else:
        kws_list = kws_db

    # 2. Parallel Scraping
    yield _section("Parallel Free Source Discovery")
    from app.scrapers.free_sources import find_competitors_ddg
    from app.services.product.platform_scanner import _async_platform_scan, _result_payload

    def _kw_str(k):
        if isinstance(k, dict):
            v = k.get("keyword", "")
            return v.keyword if hasattr(v, "keyword") else str(v)
        return k.keyword if hasattr(k, "keyword") else str(k)
    keywords_flat = [_kw_str(k) for k in kws_list if _kw_str(k)] if kws_list else [company_name]

    def _add_search_term(terms: list[str], value: Any) -> None:
        term = str(value or "").strip()
        if not term:
            return
        normalized = " ".join(term.split())
        existing = {item.lower() for item in terms}
        if 2 <= len(normalized) <= 80 and normalized.lower() not in existing:
            terms.append(normalized)

    def _pipeline_search_terms() -> list[str]:
        terms: list[str] = []
        description = " ".join(
            str(enriched.get(key) or "")
            for key in ("description", "extracted_summary", "category", "target_audience")
        ).lower()
        _add_search_term(terms, company_name)

        # DDG-backed platforms only use the first few terms, so place broad
        # problem phrases early instead of relying only on exact brand-name
        # searches that may have very little public discussion.
        if any(signal in description for signal in ("real estate", "property", "housing", "home", "rent")):
            city_terms = []
            if "gurgaon" in description or "gurugram" in description:
                city_terms = ["Gurgaon property", "Gurugram real estate", "rental scam Gurgaon"]
            for term in [
                *city_terms,
                "fake property listings",
                "verified property listings",
                "property virtual tour",
                "real estate platform",
            ]:
                _add_search_term(terms, term)

        if any(signal in description for signal in ("ecommerce", "shopping", "marketplace", "delivery")):
            for term in ("online shopping problem", "ecommerce customer pain points", "marketplace seller issues"):
                _add_search_term(terms, term)

        for kw in keywords_flat:
            _add_search_term(terms, kw)

        for persona in personas_list[:4]:
            pain_points = persona.get("pain_points", []) if isinstance(persona, dict) else []
            if isinstance(pain_points, str):
                pain_points = [pain_points]
            for pain_point in pain_points[:2]:
                _add_search_term(terms, pain_point)

        return terms or [company_name]

    search_terms = _pipeline_search_terms()
    yield _log(f"Scraping using {len(search_terms)} search terms across platforms…")

    import concurrent.futures
    all_posts = []

    # 2a. Determine Reddit subreddits
    yield _log("Determining relevant subreddits…")
    from app.services.infrastructure.llm.service import LLMService
    llm = LLMService()
    # Build a smarter domain-aware fallback in case LLM fails or returns garbage
    def _domain_fallback_subreddits(company_nm: str, description: str) -> list[str]:
        """Return contextually appropriate fallback subreddits based on company domain."""
        desc_lower = (description or "").lower()
        name_lower = (company_nm or "").lower()
        combined = f"{name_lower} {desc_lower}"

        # Map domain signals → subreddits
        domain_map = [
            (["ecommerce", "shopping", "india", "flipkart", "meesho", "myntra", "delivery", "grocery"],
             ["india", "IndiaShipping", "OnlineShopping", "IndianFinance", "InstacartShoppers"]),
            (["saas", "software", "b2b", "api", "developer", "devtool"],
             ["SaaS", "startups", "webdev", "programming"]),
            (["health", "fitness", "wellness", "medical"],
             ["health", "fitness", "nutrition", "loseit"]),
            (["finance", "fintech", "payment", "banking", "invest"],
             ["personalfinance", "investing", "FinancialPlanning", "IndiaInvestments"]),
            (["real estate", "property", "mortgage", "housing"],
             ["realestate", "RealEstateInvesting", "FirstTimeHomeBuyer"]),
            (["education", "edtech", "learning", "course", "tutor"],
             ["education", "learnprogramming", "OnlineLearning"]),
            (["food", "restaurant", "delivery", "recipe"],
             ["food", "recipes", "mealprep", "MealPrepSunday"]),
        ]
        for signals, subs in domain_map:
            if any(sig in combined for sig in signals):
                return subs[:3]
        # Generic fallback
        return ["startups", "smallbusiness", "Entrepreneur"]

    fallback_subs = _domain_fallback_subreddits(company_name, enriched.get("description", ""))

    subreddit_prompt = (
        f"You are a Reddit community expert. Suggest exactly 3 active subreddits where people would "
        f"discuss or ask about a product like '{company_name}' which does: '{enriched.get('description', '')}'. "
        f"Return ONLY a comma-separated list of subreddit names WITHOUT r/ prefix and WITHOUT any explanation. "
        f"Example format: india,OnlineShopping,IndiaFinance"
    )
    try:
        subreddits_response = await loop.run_in_executor(None, lambda: llm.generate(subreddit_prompt))
        # Clean up the response — strip markdown, backticks, bullets etc.
        clean = subreddits_response.strip().strip("`").replace("\n", ",").replace(";", ",")
        # Remove any "r/" prefix the LLM may have added
        subreddits = [s.strip().lstrip("r/").strip() for s in clean.split(",") if s.strip()]
        # Validate: each name must look like a real subreddit (no spaces, no long sentences)
        subreddits = [s for s in subreddits if s and " " not in s and len(s) < 40][:3]
        if len(subreddits) < 2:
            subreddits = fallback_subs
    except Exception:
        subreddits = fallback_subs
    yield _log(f"Selected subreddits: {', '.join(subreddits)}", "info")

    if project_id:
        try:
            from app.db.tables.discovery import create_monitored_subreddit, get_subreddit_by_project_and_name
            for s_name in subreddits:
                existing = get_subreddit_by_project_and_name(supabase, project_id, s_name)
                if not existing:
                    create_monitored_subreddit(supabase, {
                        "project_id": project_id,
                        "name": s_name,
                        "title": f"r/{s_name}",
                        "description": "",
                        "subscribers": 0,
                        "activity_score": 50,
                        "fit_score": 50,
                        "is_active": True
                    })
        except Exception as exc:
            yield _log(f"Failed to save subreddits: {exc}", "warn")

    # Run all platforms (including new free native scrapers) via PlatformRouter asynchronously
    router_platforms = ["twitter", "linkedin", "instagram", "hackernews", "github", "reddit", "indiehackers"]
    try:
        router_results = await _async_platform_scan(
            platforms=router_platforms,
            search_keywords=search_terms[:12],
            limit_per_platform=45,
            subreddits=subreddits,
            time_filter="month",
            workspace_id=workspace["id"],
            db=supabase
        )
        if router_results:
            yield _log(f"Found {len(router_results)} posts across platforms", "success")
            all_posts.extend(router_results)
        else:
            yield _log("Platform scan returned 0 posts — keywords or subreddits may need tuning", "warn")
    except Exception as scan_err:
        yield _log(f"Platform scan error (non-fatal): {scan_err}", "warn")
        router_results = []

    # Still use DuckDuckGo for competitor discovery
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        try:
            res = await loop.run_in_executor(executor, find_competitors_ddg, company_name)
            if res:
                yield _log(f"Found {len(res)} alternative competitors on DDG", "success")
                for c in res:
                    if c not in competitor_list:
                        competitor_list.append(c)
        except Exception as e:
            yield _log(f"Error scraping DuckDuckGo: {e}", "warn")

    if competitor_list and company_id:
        try:
            from app.db.tables.company import update_company
            # Join the competitors if it's a list of strings
            comp_str = ", ".join(str(c) for c in competitor_list)
            update_company(supabase, company_id, {"competitors": comp_str})
        except Exception as exc:
            yield _log(f"Failed to save competitors: {exc}", "warn")

    # 3. AI Scoring
    yield _section("AI Relevance Scoring")
    from app.services.product.relevance_v2 import RelevanceEngine
    from app.services.product.scanner import CandidatePost

    engine = RelevanceEngine(relevance_threshold=15, semantic_threshold=0.0)
    engine_brand = {
        "name": company_name,
        "brand_name": company_name,
        "description": enriched.get("extracted_summary") or enriched.get("description", ""),
        "product_summary": enriched.get("extracted_summary", ""),
        "target_audience": enriched.get("target_audience", ""),
        "category": enriched.get("category", ""),
        "pain_points": [],   # populated from personas if available
        "competitors": competitor_list,
    }
    # Merge persona pain points for better relevance scoring
    if personas_list:
        all_pain_points = []
        for p in personas_list[:3]:
            pts = p.get("pain_points", []) if isinstance(p, dict) else []
            if isinstance(pts, list):
                all_pain_points.extend(str(pt) for pt in pts if pt)
        engine_brand["pain_points"] = list(dict.fromkeys(all_pain_points))[:15]

    scored_opps = []
    seen_post_ids: set[str] = set()
    if not all_posts:
        yield _log("No posts found to score — try broader keywords or different subreddits", "warn")
        yield _log("Tip: Reddit blocks direct API calls from server IPs. Use the manual Subreddits page to add communities, then run a scan from the Discovery page.", "info")
    else:
        yield _log(f"Scoring {len(all_posts)} posts against brand profile…")
        for fp in all_posts[:240]:
            try:
                # Handle both FreePost (has .score, .source) and UnifiedPost (has .upvotes, only .platform)
                upvotes = getattr(fp, "score", getattr(fp, "upvotes", 0))
                platform = getattr(fp, "platform", "reddit") or "reddit"
                title = getattr(fp, "title", "") or ""
                body = getattr(fp, "body", "") or ""
                post_url = getattr(fp, "url", "") or ""
                external_id = getattr(fp, "external_id", None) or getattr(fp, "id", None)
                if not external_id:
                    fingerprint = f"{platform}:{post_url}:{title}:{body[:120]}"
                    external_id = hashlib.sha1(fingerprint.encode("utf-8")).hexdigest()[:16]
                reddit_post_id = f"{platform}_{external_id}"
                if reddit_post_id in seen_post_ids:
                    continue
                seen_post_ids.add(reddit_post_id)

                source_name = getattr(fp, "subreddit", None) or getattr(fp, "source", platform)

                candidate = CandidatePost(
                    title=title,
                    body=body,
                    platform=platform,
                    source_name=source_name,
                    upvotes=upvotes,
                    comments_count=getattr(fp, "comments_count", 0) or 0,
                    created_at=getattr(fp, "created_at", None),
                    author=getattr(fp, "author", "unknown") or "unknown",
                    post_url=post_url,
                )

                # Build keyword list for scoring — use all flat keywords as dicts
                engine_kws = [{"keyword": kw, "type": "core", "weight": 1.0} for kw in search_terms[:25]]
                if not engine_kws:
                    engine_kws = [{"keyword": company_name, "type": "core", "weight": 1.0}]
                result = await loop.run_in_executor(
                    None,
                    lambda c=candidate, kws=engine_kws: engine.score(c, engine_brand, kws)
                )

                keyword_rescue = result.relevance_score >= 10 and bool(result.matched_keywords)
                if result.should_keep or keyword_rescue:
                    if result.relevance_score >= 50:
                        yield _log(f"High-value opportunity on {platform} (Score: {result.relevance_score})", "success")
                    opp = {
                        "platform": platform,
                        "title": title,
                        "body": body,
                        "post_url": post_url,
                        "score": result.relevance_score,
                    }
                    scored_opps.append(opp)

                    if project_id:
                        try:
                            from app.db.tables.discovery import create_opportunity
                            create_opportunity(supabase, {
                                "project_id": project_id,
                                "platform": platform,
                                "reddit_post_id": reddit_post_id,
                                "title": title or body[:100],
                                "body": body,
                                "body_excerpt": body[:1200],
                                "permalink": post_url,
                                "author": getattr(fp, "author", "unknown") or "unknown",
                                "status": "new",
                                "subreddit_name": source_name,
                                "opportunity_type": "mention",
                                "source_type": "post",
                                **_result_payload(result),
                            })
                        except Exception as exc:
                            yield _log(f"Failed to save opportunity: {exc}", "warn")
            except Exception as e:
                yield _log(f"Error scoring post: {e}", "warn")

    # 3b. Competitor Intelligence — detect mentions in the posts we just scored.
    # This was previously only wired into the legacy pipeline.py orchestrator,
    # which meant the Competitor Intel page stayed empty for anyone using the
    # Auto-Analyze flow or a manual Launch Scan. Wiring it here (and in
    # scanner.py) makes all three entry points feed the same page consistently.
    if all_posts:
        yield _log(f"Kept {len(scored_opps)} actionable opportunities from this run.", "success" if scored_opps else "warn")
        yield _data("opportunities_count", len(scored_opps))

    if project_id:
        try:
            from app.db.tables.discovery import list_opportunities_for_project

            saved_opps = list_opportunities_for_project(supabase, project_id, status="new", limit=1000)
            if saved_opps:
                synced_opps = []
                synced_keys: set[str] = set()
                for row in saved_opps:
                    key = str(row.get("permalink") or row.get("url") or row.get("reddit_post_id") or row.get("id"))
                    if key in synced_keys:
                        continue
                    synced_keys.add(key)
                    synced_opps.append({
                        "platform": row.get("platform") or "reddit",
                        "title": row.get("title") or row.get("body_excerpt") or "Untitled Post",
                        "body": row.get("body_excerpt") or row.get("body") or "",
                        "post_url": row.get("permalink") or row.get("url") or "#",
                        "score": row.get("score") or 0,
                    })
                scored_opps = synced_opps
                yield _log(f"Synced {len(scored_opps)} saved opportunities for this project.", "success")
                yield _data("opportunities_count", len(scored_opps))
        except Exception as exc:
            yield _log(f"Failed to sync saved opportunities: {exc}", "warn")

    if project_id and competitor_list and scored_opps:
        yield _section("Competitor Intelligence")
        try:
            from app.services.product.competitor_intel import process_competitor_opportunities
            post_dicts_for_comp = [
                {
                    "title": o.get("title", ""),
                    "body": o.get("body", ""),
                    "selftext": o.get("body", ""),
                    "platform": o.get("platform", "reddit"),
                    "url": o.get("post_url", ""),
                }
                for o in scored_opps
            ]
            comp_mentions = await process_competitor_opportunities(
                supabase, project_id, post_dicts_for_comp, competitor_list
            )
            if comp_mentions:
                yield _log(f"Detected {len(comp_mentions)} competitor mentions across scanned posts", "success")
            else:
                yield _log("No competitor mentions found in this batch", "info")
        except Exception as exc:
            yield _log(f"Competitor intelligence scan failed (non-fatal): {exc}", "warn")

    # 4. Generate Document
    yield _section("Generating Final Report")
    yield _log("Compiling living document…")

    report_md = generate_markdown_report(
        company=enriched,
        keywords=kws_list,
        personas=personas_list,
        opportunities=scored_opps,
    )

    if project_id:
        try:
            from app.db.tables.analytics import create_auto_pipeline
            create_auto_pipeline(supabase, {
                "project_id": project_id,
                "website_url": url,
                "status": "executed",
                "progress": 100,
                "personas_count": len(personas_list),
                "keywords_count": len(kws_list),
                "subreddits_count": len(locals().get("subs_list", [])),
                "opportunities_count": len(scored_opps),
                "drafts_count": 0,
                "results": {
                    "brand_summary": enriched.get("extracted_summary", ""),
                    "report_md": report_md
                }
            })
            yield _log("Saved pipeline run history to database.", "success")
        except Exception as exc:
            yield _log(f"Failed to save pipeline run to history: {exc}", "warn")

    yield _data("report", report_md)
    yield _log("Report ready.", "success")

    yield _event({
        "type": "complete",
        "company": enriched,
        "keywords": kws_list,
        "competitors": competitor_list,
        "project_id": project_id,
        "opportunities_count": len(scored_opps),
        "report": report_md
    })

