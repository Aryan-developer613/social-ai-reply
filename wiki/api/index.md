# API

REST API endpoints and patterns for Social AI Reply.

## Overview

The backend exposes a RESTful API under the `/v1` prefix. Most endpoints require authentication via JWT Bearer tokens and are scoped to workspaces. Auth endpoints (register, login, reset-password) are public and do not require a token.

## Base URL

```
http://localhost:8000/v1
```

## Authentication

### JWT Bearer tokens
```bash
Authorization: Bearer <token>
```

### Getting tokens
- Registration: `POST /v1/auth/register`
- Login: `POST /v1/auth/login`

## API structure

### Route organization
Routes are organized by domain in `app/api/v1/routes/`:
- `auth.py` - Authentication
- `projects.py` - Project management
- `discovery.py` - Opportunity discovery
- `drafts.py` - Draft generation
- `agents.py` - Agent management
- `visibility.py` - AI visibility
- `analytics.py` - Analytics and reporting

### Common patterns

**List endpoint:**
```bash
GET /v1/{resource}
```

**Get single:**
```bash
GET /v1/{resource}/{id}
```

**Create:**
```bash
POST /v1/{resource}
Content-Type: application/json

{...}
```

**Update:**
```bash
PUT /v1/{resource}/{id}
Content-Type: application/json

{...}
```

**Delete:**
```bash
DELETE /v1/{resource}/{id}
```

## Key endpoints

### Authentication
- `POST /v1/auth/register` - Create account
- `POST /v1/auth/login` - Get token
- `POST /v1/auth/reset-password` - Reset password

### Projects
- `GET /v1/projects` - List projects
- `POST /v1/projects` - Create project
- `GET /v1/projects/{id}` - Get project
- `PUT /v1/projects/{id}` - Update project

### Opportunities
- `GET /v1/opportunities` - List opportunities
- `GET /v1/opportunities/{id}` - Get opportunity
- `PUT /v1/opportunities/{id}` - Update status
- `POST /v1/opportunities/{id}/save` - Save
- `POST /v1/opportunities/{id}/ignore` - Ignore

### Agents
- `POST /v1/agents/run` - Run agent
- `GET /v1/agents/runs` - List runs
- `GET /v1/agents/runs/{id}` - Get run

### Drafts
- `POST /v1/drafts/generate` - Generate draft
- `GET /v1/drafts` - List drafts
- `PUT /v1/drafts/{id}` - Update draft

## Request/Response format

### Request body
```json
{
  "field1": "value1",
  "field2": "value2"
}
```

### Response format
```json
{
  "id": 1,
  "field1": "value1",
  "created_at": "2026-06-18T10:00:00Z"
}
```

### Error format
```json
{
  "detail": "Error message",
  "error_code": "NOT_FOUND"
}
```

## Pagination

### Query parameters
- `limit` - Items per page (default: 20)
- `offset` - Starting position (default: 0)

### Response headers
- `X-Total-Count` - Total items
- `X-Page-Count` - Total pages

## Rate limiting

### Limits
- Scan endpoints: 5 requests/60s
- Generate endpoints: 10 requests/60s
- Auth endpoints: 10 requests/300s
- Default: 60 requests/60s

### Headers
- `X-RateLimit-Limit` - Request limit
- `X-RateLimit-Remaining` - Remaining requests
- `X-RateLimit-Reset` - Reset timestamp

## CORS

### Allowed origins
Configured via `CORS_ORIGINS_RAW` environment variable.

### Methods
GET, POST, PUT, DELETE, PATCH, OPTIONS

### Headers
Authorization, Content-Type, X-Request-ID

## Documentation

### OpenAPI
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- JSON: `http://localhost:8000/openapi.json`

## Error codes

### Common codes
- `NOT_FOUND` - Resource not found
- `FORBIDDEN` - Insufficient permissions
- `CONFLICT` - Resource already exists
- `VALIDATION_ERROR` - Invalid input
- `RATE_LIMITED` - Too many requests

## Testing

### Using curl
```bash
# Get token
TOKEN=$(curl -s -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password"}' \
  | jq -r '.token')

# Use token
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/v1/projects
```

### Using Postman
1. Set base URL: `http://localhost:8000/v1`
2. Add Authorization header
3. Set Content-Type: application/json

---

*360 Flatmates Platform Documentation*
