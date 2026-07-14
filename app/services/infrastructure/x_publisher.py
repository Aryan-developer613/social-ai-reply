"""X (Twitter) API v2 publishing client.

``XPublisher`` posts tweet threads sequentially via ``POST /2/tweets`` with an
OAuth2 user-context access token, chaining each tweet as a reply to the
previous one. ``get_x_token`` retrieves the workspace's stored token from
``integration_secrets`` (provider ``"x"``, falling back to ``"twitter"``)
and decrypts it.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

import httpx

from app.core.config import get_settings
from app.services.infrastructure.platform_token_utils import get_platform_token

if TYPE_CHECKING:
    from supabase import Client

logger = logging.getLogger(__name__)

X_TWEETS_URL = "https://api.x.com/2/tweets"
_TWEET_SLEEP_SECONDS = 1.0
_REQUEST_TIMEOUT_SECONDS = 30.0


def get_x_token(db: Client, workspace_id: int) -> str | None:
    """Return the decrypted X access token for a workspace, or None if not configured.

    Looks for an integration secret with provider ``"x"`` first, then falls back
    to ``"twitter"``.
    """
    return get_platform_token(db, workspace_id, "x", fallback_provider="twitter")


class XPublisher:
    """httpx-based X API v2 client for publishing tweet threads."""

    def __init__(
        self,
        token: str,
        base_url: str = X_TWEETS_URL,
        sleep_seconds: float = _TWEET_SLEEP_SECONDS,
    ) -> None:
        """Args:
        token: OAuth2 user-context access token (bearer string).
        base_url: Tweets endpoint URL (overridable for tests).
        sleep_seconds: Delay between consecutive tweets in a thread.
        """
        self._token = token
        self._base_url = base_url
        self._sleep_seconds = sleep_seconds

    def publish_thread(self, tweets: list[str]) -> list[dict[str, Any]]:
        """Publish a thread sequentially, chaining replies.

        Args:
            tweets: Ordered tweet texts (first is the root tweet).

        Returns:
            List of ``{"id": tweet_id, "text": tweet_text}`` in publish order.

        Raises:
            RuntimeError: On API errors (rate limit, auth, validation) or
                network failures, with a clear message.
        """
        if not tweets:
            raise RuntimeError("Cannot publish an empty thread.")

        if get_settings().mock_publishers:
            for text in tweets:
                logger.info("[MOCK] Would publish to X: %s", text)
            return [{"id": f"mock_{i}", "text": t} for i, t in enumerate(tweets)]

        results: list[dict[str, Any]] = []
        previous_id: str | None = None
        with httpx.Client(timeout=_REQUEST_TIMEOUT_SECONDS) as client:
            for index, text in enumerate(tweets):
                payload: dict[str, Any] = {"text": text}
                if previous_id:
                    payload["reply"] = {"in_reply_to_tweet_id": previous_id}
                data = self._post_tweet(client, payload)
                previous_id = str(data.get("id", ""))
                results.append({"id": previous_id, "text": data.get("text", text)})
                if index < len(tweets) - 1:
                    time.sleep(self._sleep_seconds)
        return results

    # ── Internal helpers ───────────────────────────────────────────────

    def _post_tweet(self, client: httpx.Client, payload: dict[str, Any]) -> dict[str, Any]:
        """POST one tweet, honoring a single 429 Retry-After before failing."""
        response = self._send(client, payload)
        if response.status_code == 429:
            retry_after = _parse_retry_after(response)
            logger.warning("X API rate limited; retrying once after %ss", retry_after)
            time.sleep(retry_after)
            response = self._send(client, payload)
            if response.status_code == 429:
                raise RuntimeError(
                    "X API rate limit exceeded (HTTP 429) even after honoring "
                    "Retry-After. The thread was not fully published; try again later."
                )
        if response.status_code >= 400:
            raise RuntimeError(
                f"X API error (HTTP {response.status_code}): {_extract_error_detail(response)}"
            )
        body = response.json()
        data = body.get("data") if isinstance(body, dict) else None
        if not isinstance(data, dict) or not data.get("id"):
            raise RuntimeError("X API returned an unexpected response with no tweet id.")
        return data

    def _send(self, client: httpx.Client, payload: dict[str, Any]) -> httpx.Response:
        try:
            return client.post(
                self._base_url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Content-Type": "application/json",
                },
            )
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Failed to reach the X API: {exc}") from exc


def _parse_retry_after(response: httpx.Response) -> float:
    """Parse the Retry-After header, defaulting to 1 second."""
    raw = response.headers.get("Retry-After", "")
    try:
        return max(0.0, float(raw))
    except (TypeError, ValueError):
        return 1.0


def _extract_error_detail(response: httpx.Response) -> str:
    """Pull the most useful error message out of an X API error response."""
    try:
        body = response.json()
    except ValueError:
        return response.text[:500] or "no error detail provided"
    if isinstance(body, dict):
        if isinstance(body.get("errors"), list) and body["errors"]:
            first = body["errors"][0]
            if isinstance(first, dict):
                return str(first.get("message") or first.get("detail") or first)
        for key in ("detail", "title", "error_description", "error"):
            if body.get(key):
                return str(body[key])
    return str(body)[:500]
