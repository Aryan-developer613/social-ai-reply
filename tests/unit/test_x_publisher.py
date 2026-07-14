"""Unit tests for the X API v2 publisher."""

from unittest.mock import patch

import pytest

from app.services.infrastructure.x_publisher import XPublisher, get_x_token

# ── Fakes ─────────────────────────────────────────────────────────────


class FakeResponse:
    def __init__(self, status_code, json_data=None, headers=None, text=""):
        self.status_code = status_code
        self._json = json_data
        self.headers = headers or {}
        self.text = text

    def json(self):
        if self._json is None:
            raise ValueError("no json")
        return self._json


class FakeHttpxClient:
    """Stands in for httpx.Client; pops queued responses and records requests."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, *args, **kwargs):  # constructor stand-in
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def post(self, url, json=None, headers=None):
        self.calls.append({"url": url, "json": json, "headers": headers})
        return self.responses.pop(0)


def _ok(tweet_id, text):
    return FakeResponse(201, {"data": {"id": tweet_id, "text": text}})


def _run_publish(responses, tweets):
    fake = FakeHttpxClient(responses)
    with (
        patch("app.services.infrastructure.x_publisher.httpx.Client", fake),
        patch("app.services.infrastructure.x_publisher.time.sleep") as sleep,
    ):
        results = XPublisher("token-123").publish_thread(tweets)
    return fake, sleep, results


# ── publish_thread chaining ───────────────────────────────────────────


def test_publish_thread_chains_replies():
    fake, sleep, results = _run_publish(
        [_ok("100", "t1"), _ok("101", "t2"), _ok("102", "t3")],
        ["t1", "t2", "t3"],
    )

    assert results == [
        {"id": "100", "text": "t1"},
        {"id": "101", "text": "t2"},
        {"id": "102", "text": "t3"},
    ]
    assert len(fake.calls) == 3
    # First tweet is the root (no reply field)
    assert "reply" not in fake.calls[0]["json"]
    # Each subsequent tweet replies to the previous tweet's id
    assert fake.calls[1]["json"]["reply"] == {"in_reply_to_tweet_id": "100"}
    assert fake.calls[2]["json"]["reply"] == {"in_reply_to_tweet_id": "101"}
    # Bearer auth on every request
    assert all(c["headers"]["Authorization"] == "Bearer token-123" for c in fake.calls)
    # 1s sleep between tweets (2 gaps for 3 tweets)
    assert sleep.call_count == 2


def test_publish_thread_single_tweet_no_sleep():
    fake, sleep, results = _run_publish([_ok("1", "only")], ["only"])
    assert results == [{"id": "1", "text": "only"}]
    assert sleep.call_count == 0


def test_publish_thread_empty_raises():
    with pytest.raises(RuntimeError):
        XPublisher("tok").publish_thread([])


# ── 429 handling ──────────────────────────────────────────────────────


def test_429_honors_retry_after_once_then_succeeds():
    rate_limited = FakeResponse(429, {"title": "Too Many Requests"}, headers={"Retry-After": "7"})
    fake, sleep, results = _run_publish([rate_limited, _ok("55", "hello")], ["hello"])

    assert results == [{"id": "55", "text": "hello"}]
    assert len(fake.calls) == 2
    # Slept for the Retry-After duration before retrying
    assert sleep.call_args_list[0].args[0] == 7.0


def test_429_twice_fails_with_clear_message():
    rate_limited = FakeResponse(429, {"title": "Too Many Requests"}, headers={"Retry-After": "1"})
    fake = FakeHttpxClient([rate_limited, FakeResponse(429, {}, headers={})])
    with (
        patch("app.services.infrastructure.x_publisher.httpx.Client", fake),
        patch("app.services.infrastructure.x_publisher.time.sleep"),
        pytest.raises(RuntimeError, match="rate limit"),
    ):
        XPublisher("tok").publish_thread(["hello"])
    assert len(fake.calls) == 2  # retried exactly once


# ── Other error propagation ───────────────────────────────────────────


def test_4xx_error_raises_with_api_detail():
    forbidden = FakeResponse(403, {"detail": "You are not permitted to perform this action."})
    fake = FakeHttpxClient([forbidden])
    with (
        patch("app.services.infrastructure.x_publisher.httpx.Client", fake),
        patch("app.services.infrastructure.x_publisher.time.sleep"),
        pytest.raises(RuntimeError, match="not permitted"),
    ):
        XPublisher("tok").publish_thread(["hi"])


def test_error_detail_from_errors_array():
    bad = FakeResponse(400, {"errors": [{"message": "Tweet text is too long."}]})
    fake = FakeHttpxClient([bad])
    with (
        patch("app.services.infrastructure.x_publisher.httpx.Client", fake),
        patch("app.services.infrastructure.x_publisher.time.sleep"),
        pytest.raises(RuntimeError, match="too long"),
    ):
        XPublisher("tok").publish_thread(["hi"])


def test_failure_mid_thread_stops_publishing():
    fake = FakeHttpxClient([_ok("1", "a"), FakeResponse(400, {"detail": "dup"})])
    with (
        patch("app.services.infrastructure.x_publisher.httpx.Client", fake),
        patch("app.services.infrastructure.x_publisher.time.sleep"),
        pytest.raises(RuntimeError),
    ):
        XPublisher("tok").publish_thread(["a", "b", "c"])
    assert len(fake.calls) == 2  # third tweet never attempted


# ── get_x_token ───────────────────────────────────────────────────────


def _secrets_patch(rows):
    return patch(
        "app.services.infrastructure.platform_token_utils.list_integration_secrets_for_workspace",
        return_value=rows,
    )


def test_get_x_token_prefers_provider_x():
    rows = [
        {"provider": "twitter", "encrypted_value": "enc-twitter"},
        {"provider": "x", "encrypted_value": "enc-x"},
    ]
    with (
        _secrets_patch(rows),
        patch("app.services.infrastructure.platform_token_utils.decrypt_text", side_effect=lambda v: f"dec:{v}"),
    ):
        assert get_x_token(object(), 1) == "dec:enc-x"


def test_get_x_token_falls_back_to_twitter():
    rows = [{"provider": "twitter", "encrypted_value": "enc-tw"}]
    with (
        _secrets_patch(rows),
        patch("app.services.infrastructure.platform_token_utils.decrypt_text", side_effect=lambda v: f"dec:{v}"),
    ):
        assert get_x_token(object(), 1) == "dec:enc-tw"


def test_get_x_token_none_when_not_configured():
    with _secrets_patch([{"provider": "reddit", "encrypted_value": "enc"}]):
        assert get_x_token(object(), 1) is None


def test_get_x_token_decrypt_failure_raises_runtime_error():
    rows = [{"provider": "x", "encrypted_value": "broken"}]
    with (
        _secrets_patch(rows),
        patch("app.services.infrastructure.platform_token_utils.decrypt_text", side_effect=ValueError("bad key")),
        pytest.raises(RuntimeError, match="decrypt"),
    ):
        get_x_token(object(), 1)
