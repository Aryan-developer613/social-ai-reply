"""Timeout and retry configuration constants.

These constants define timeouts, retry delays, and other timing-related
values used throughout the application.
"""

# Request timeouts (in seconds)
DEFAULT_REQUEST_TIMEOUT = 30
API_REQUEST_TIMEOUT = 60
LLM_REQUEST_TIMEOUT = 120
REDDIT_API_TIMEOUT = 30
WEBHOOK_TIMEOUT = 10
EMAIL_SEND_TIMEOUT = 30

# Database timeouts
DB_QUERY_TIMEOUT = 30
DB_CONNECTION_TIMEOUT = 10

# Rate limiting windows (in seconds)
RATE_LIMIT_WINDOW_SCAN = 60
RATE_LIMIT_WINDOW_GENERATE = 60
RATE_LIMIT_WINDOW_AUTH = 300
RATE_LIMIT_WINDOW_DEFAULT = 60

# Token expiration (in seconds)
ACCESS_TOKEN_EXPIRATION = 3600  # 1 hour
REFRESH_TOKEN_EXPIRATION = 2_592_000  # 30 days
INVITATION_TOKEN_EXPIRATION = 604_800  # 7 days

# Scan intervals
SCAN_INTERVAL_MINUTES = 30
MIN_SCAN_INTERVAL_MINUTES = 15
AUTO_PIPELINE_INTERVAL_MINUTES = 60

# Cache TTL (in seconds)
CACHE_TTL_SHORT = 300  # 5 minutes
CACHE_TTL_MEDIUM = 3600  # 1 hour
CACHE_TTL_LONG = 86400  # 24 hours

# JWKS cache (in seconds)
JWKS_CACHE_TTL = 900  # 15 minutes — bounds staleness after Supabase key rotation
JWKS_REFRESH_COOLDOWN = 30  # min gap between refreshes triggered by unknown kids

# Health check intervals
HEALTH_CHECK_INTERVAL = 30
READINESS_CHECK_INTERVAL = 10

# Background task timeouts
BACKGROUND_TASK_TIMEOUT = 300  # 5 minutes
AUTO_PIPELINE_TIMEOUT = 600  # 10 minutes

# LLM-specific timeouts
GEMINI_REQUEST_TIMEOUT = 90

# Instagram scraping (legacy)
SCRAPE_REQUESTS_PER_MINUTE = 30
SCRAPE_DAILY_CAP_PER_ACCOUNT = 2500
SCRAPE_DELAY_BETWEEN_REQUESTS_MS = 2000

# Connection pool settings
DB_POOL_SIZE = 10
DB_MAX_OVERFLOW = 20
DB_POOL_TIMEOUT = 30
DB_POOL_RECYCLE = 1800  # 30 minutes
