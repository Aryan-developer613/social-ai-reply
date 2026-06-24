"""Webhook CRUD and testing endpoints."""
import hashlib
import hmac
import ipaddress
import json
import logging
import socket
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from app.api.v1.deps import ensure_workspace_membership, get_current_user, get_current_workspace
from app.db.supabase_client import get_supabase
from app.db.tables.system import create_activity_log
from app.db.tables.webhooks import (
    create_webhook_endpoint,
    delete_webhook_endpoint,
    get_webhook_endpoint_by_id,
    list_webhook_endpoints_for_workspace,
    update_webhook_endpoint,
)
from app.schemas.v1.webhooks import (
    WebhookRequest,
    WebhookResponse,
    WebhookTestRequest,
    WebhookUpdateRequest,
)
from app.utils.security import validate_webhook_url

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["webhooks"])


@router.get("/webhooks", response_model=list[WebhookResponse])
def list_webhooks(
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> list[WebhookResponse]:
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    rows = list_webhook_endpoints_for_workspace(supabase, workspace["id"])
    return [WebhookResponse.model_validate(row) for row in rows]


@router.post("/webhooks", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
def create_webhook(
    payload: WebhookRequest,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> WebhookResponse:
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    try:
        validate_webhook_url(str(payload.target_url))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    row = create_webhook_endpoint(
        supabase,
        {
            "workspace_id": workspace["id"],
            "target_url": str(payload.target_url),
            "event_types": payload.event_types,
            "is_active": payload.is_active if payload.is_active is not None else True,
        },
    )
    create_activity_log(
        supabase,
        {
            "workspace_id": workspace["id"],
            "project_id": None,
            "actor_user_id": current_user["id"],
            "event_type": "webhook.created",
            "entity_type": "WebhookEndpoint",
            "entity_id": str(row["id"]),
        },
    )
    return WebhookResponse.model_validate(row)


@router.patch("/webhooks/{webhook_id}", response_model=WebhookResponse)
def update_webhook(
    webhook_id: int,
    payload: WebhookUpdateRequest,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> WebhookResponse:
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    row = get_webhook_endpoint_by_id(supabase, webhook_id)
    if not row:
        raise HTTPException(status_code=404, detail="Webhook not found.")
    if row["workspace_id"] != workspace["id"]:
        raise HTTPException(status_code=404, detail="Webhook not found.")
    # Build update dict with only mutable fields.
    # Map frontend field name target_url → DB column url (Issue #45).
    update_data = {}
    for key, value in payload.model_dump(exclude_unset=True).items():
        if key == "target_url":
            update_data["url"] = value
        elif key in ("url", "name", "description", "is_active", "secret"):
            update_data[key] = value
    updated = update_webhook_endpoint(supabase, webhook_id, update_data)
    return WebhookResponse.model_validate(updated)


@router.delete("/webhooks/{webhook_id}")
def delete_webhook(
    webhook_id: int,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> dict[str, bool]:
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    row = get_webhook_endpoint_by_id(supabase, webhook_id)
    if not row:
        raise HTTPException(status_code=404, detail="Webhook not found.")
    if row["workspace_id"] != workspace["id"]:
        raise HTTPException(status_code=404, detail="Webhook not found.")
    delete_webhook_endpoint(supabase, webhook_id)
    return {"ok": True}


@router.get("/webhooks/{webhook_id}/sample-payload")
def webhook_sample_payload(
    webhook_id: int,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
):
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    row = get_webhook_endpoint_by_id(supabase, webhook_id)
    if not row:
        raise HTTPException(status_code=404, detail="Webhook not found.")
    if row["workspace_id"] != workspace["id"]:
        raise HTTPException(status_code=404, detail="Webhook not found.")
    return {
        "event": "opportunity.found",
        "timestamp": "2024-01-15T10:30:00Z",
        "data": {
            "opportunity_id": 1,
            "title": "Sample Reddit Post",
            "subreddit": "example",
            "score": 85,
            "url": "https://reddit.com/r/example/comments/abc123",
        },
    }


@router.post("/webhooks/{webhook_id}/test")
async def test_webhook(
    webhook_id: int,
    payload: WebhookTestRequest,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
):
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    row = get_webhook_endpoint_by_id(supabase, webhook_id)
    if not row:
        raise HTTPException(status_code=404, detail="Webhook not found.")
    if row["workspace_id"] != workspace["id"]:
        raise HTTPException(status_code=404, detail="Webhook not found.")

    test_payload = {
        "event": "webhook.test",
        "timestamp": "2024-01-15T10:30:00Z",
        "data": {"test": True, "message": "Test webhook delivery"},
    }
    body = json.dumps(test_payload)
    signature = hmac.new(row["signing_secret"].encode(), body.encode(), hashlib.sha256).hexdigest() if row.get("signing_secret") else ""

    try:
        validate_webhook_url(row["target_url"])
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # DNS rebinding protection: resolve hostname and reject private/reserved IPs
    hostname = urlparse(row["target_url"]).hostname
    if hostname:
        try:
            addrs = socket.getaddrinfo(hostname, None)
            for (_, _, _, _, sockaddr) in addrs:
                ip = ipaddress.ip_address(sockaddr[0])
                if not ip.is_global:
                    raise HTTPException(status_code=422, detail="Webhook URL resolves to a private/reserved IP address")
        except HTTPException:
            raise
        except Exception as dns_err:
            raise HTTPException(status_code=422, detail=f"Failed to resolve webhook URL hostname: {dns_err}") from dns_err

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {
                "Content-Type": "application/json",
                "X-Webhook-Signature": signature,
                "X-Webhook-Event": "webhook.test",
            }
            resp = await client.post(row["target_url"], content=body, headers=headers)
        if resp.status_code >= 400:
            return {
                "delivered": False,
                "status_code": resp.status_code,
                "response_body": resp.text[:500],
                "error": f"Endpoint returned HTTP {resp.status_code}",
            }
        return {
            "delivered": True,
            "status_code": resp.status_code,
            "response_body": resp.text[:500],
        }
    except HTTPException:
        raise
    except Exception as e:
        return {"delivered": False, "error": str(e)}
