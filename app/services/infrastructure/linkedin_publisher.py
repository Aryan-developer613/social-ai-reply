"""LinkedIn API v2 publishing client.

``LinkedInPublisher`` posts a single text share or article to a LinkedIn
User or Organization via the LinkedIn Marketing/Share API
(``POST /rest/posts``).  ``get_linkedin_token`` retrieves the workspace's
stored token from ``integration_secrets`` (provider ``"linkedin"``) and
decrypts it.

.. note::

   The LinkedIn API v2 requires:
   * A LinkedIn Page (Company Page) or a LinkedIn Member account.
   * A 3-legged OAuth 2.0 access token with the ``w_member_social``
     (or ``w_organization_social``) scope.
   * The ``author`` field must be ``urn:li:person:{member-id}`` or
     ``urn:li:organization:{org-id}``.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import httpx

from app.core.config import get_settings
from app.services.infrastructure.platform_token_utils import (
    get_platform_secret_value,
    get_platform_token,
)

if TYPE_CHECKING:
    from supabase import Client

logger = logging.getLogger(__name__)

LINKEDIN_API_BASE_URL = "https://api.linkedin.com"
# TODO: Periodically review this version against LinkedIn's current API docs.
#       See: https://learn.microsoft.com/en-us/linkedin/marketing/versioning
LINKEDIN_API_VERSION = "202502"
_REQUEST_TIMEOUT_SECONDS = 30.0


def get_linkedin_token(db: Client, workspace_id: int) -> str | None:
    """Return the decrypted LinkedIn access token for a workspace, or None.

    Looks for an integration secret with provider ``"linkedin"``.
    """
    return get_platform_token(db, workspace_id, "linkedin")


def get_linkedin_author_urn(db: Client, workspace_id: int) -> str | None:
    """Return the LinkedIn author URN for a workspace, or None.

    Stored as an integration secret with provider ``"linkedin"`` and
    label ``"author_urn"`` (e.g. ``urn:li:organization:123456`` or
    ``urn:li:person:abcdef``).
    """
    return get_platform_secret_value(db, workspace_id, "linkedin", "author_urn")


class LinkedInPublisher:
    """LinkedIn API v2 client for publishing posts.

    Uses ``POST /rest/posts`` to create a text or article share.
    Currently only text shares are implemented (no article link or
    media upload).
    """

    def __init__(
        self,
        token: str,
        author_urn: str,
        base_url: str = LINKEDIN_API_BASE_URL,
        api_version: str = LINKEDIN_API_VERSION,
    ) -> None:
        """Args:
        token: LinkedIn OAuth 2.0 access token.
        author_urn: URN of the author
                   (e.g. ``urn:li:organization:123456``).
        base_url: LinkedIn API base URL (overridable for tests).
        api_version: LinkedIn API version header value.
        """
        self._token = token
        self._author_urn = author_urn
        self._base_url = base_url
        self._api_version = api_version

    # ── Public API ──────────────────────────────────────────────────────

    def publish_post(self, content: str) -> dict[str, Any]:
        """Publish a single LinkedIn post (text share).

        Args:
            content: The post body text (plain text or limited HTML).

        Returns:
            Dict with keys ``{"id": post_id}`` on success.

        Raises:
            RuntimeError: On API errors or network failures.
        """
        if get_settings().mock_publishers:
            logger.info("[MOCK] Would publish to LinkedIn: %s", content)
            return {"id": "mock_li_post"}

        url = f"{self._base_url}/rest/posts"

        payload: dict[str, Any] = {
            "author": self._author_urn,
            "commentary": content,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }

        with httpx.Client(timeout=_REQUEST_TIMEOUT_SECONDS) as client:
            try:
                response = client.post(
                    url,
                    json=payload,
                    headers=self._headers(),
                )
            except httpx.HTTPError as exc:
                raise RuntimeError(
                    f"Failed to reach LinkedIn API: {exc}"
                ) from exc

        if response.status_code >= 400:
            detail = _extract_linkedin_error(response)
            raise RuntimeError(
                f"LinkedIn API error (HTTP {response.status_code}): {detail}"
            )

        # LinkedIn returns the post ID in the ``x-restli-id`` header
        # for REST APIs, or in the response body for some endpoints.
        post_id = response.headers.get("x-restli-id") or ""
        if not post_id:
            try:
                body = response.json()
                post_id = str(body.get("id", ""))
            except ValueError:
                pass

        if not post_id:
            raise RuntimeError(
                "LinkedIn API did not return a post id (x-restli-id header missing)."
            )

        return {"id": post_id}

    # ── Internal helpers ────────────────────────────────────────────────

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": self._api_version,
        }


def _extract_linkedin_error(response: httpx.Response) -> str:
    """Pull the most descriptive error message from a LinkedIn API response."""
    try:
        body = response.json()
    except ValueError:
        return response.text[:500] or "no error detail"
    if isinstance(body, dict):
        msg = (
            body.get("message")
            or (body.get("serviceErrorCode") and str(body["serviceErrorCode"]))
            or body.get("status")
            or str(body)
        )
        return str(msg)[:500]
    return str(body)[:500]
