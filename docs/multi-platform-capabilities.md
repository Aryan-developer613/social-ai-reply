# Multi-Platform Search, Security, and File Analysis

This document covers the optional capabilities added after multi-model LLM
routing. All features are modular and can be disabled without changing the
existing Claude/Gemini workflow.

## Feature Flags

```env
ENABLE_ENHANCED_SEARCH=true
SEARCH_CACHE_TTL_SECONDS=900

ENABLE_RESPONSE_ENCRYPTION=false
ENCRYPTION_KEY=

FILE_UPLOAD_DIR=.uploads
MAX_UPLOAD_BYTES=10000000
```

## Search APIs

All endpoints require the existing Bearer auth and workspace membership.

```http
POST /v1/search/reddit
POST /v1/search/x
POST /v1/search/web
GET  /v1/search/cache/{cache_key}
```

Request body:

```json
{
  "query": "delivery delays ecommerce",
  "project_id": 1,
  "limit": 10,
  "use_cache": true
}
```

Reddit also accepts:

```json
{
  "subreddits": ["india", "OnlineShopping"]
}
```

Web search responses include `citations` so generated replies can be
fact-checked before publishing.

## Search Cache

Search results are cached in `search_cache` by workspace, provider, query, and
search parameters. The TTL is controlled by `SEARCH_CACHE_TTL_SECONDS`.

Apply:

```sql
app/db/migrations/20260706_01_search_cache_uploaded_files.sql
```

## AES-256-GCM Encryption

`app.utils.aes_gcm` provides AES-256-GCM encryption with random 96-bit nonces
and optional associated data.

When `ENABLE_RESPONSE_ENCRYPTION=true`, reply draft content and post draft
title/body are encrypted before insertion/update and decrypted by table helpers
before returning to routes. Existing plaintext rows continue to read normally.

## File APIs

Raw body upload is used to avoid forcing multipart dependencies into the
backend.

```http
POST /v1/files/upload?file_name=brand-guide.pdf&project_id=1
GET  /v1/files?project_id=1
POST /v1/files/{file_id}/analyze
GET  /v1/files/{file_id}/report
```

Supported analysis:

- CSV/TSV: standard-library parser with row, column, numeric, and preview stats.
- TXT/MD: word counts, top terms, and preview.
- PDF: optional `pypdf` dependency.
- XLSX/XLSM: optional `openpyxl` dependency.

Uploaded records are stored in `uploaded_files`. Local file bytes are stored
under `FILE_UPLOAD_DIR`, which defaults to `.uploads/`.
