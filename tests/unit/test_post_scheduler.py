"""Unit tests for the post_drafts auto-publish scheduler."""

from unittest.mock import patch

from app.services.product.post_scheduler import publish_due_drafts


def _draft(draft_id, platform, **overrides):
    base = {
        "id": draft_id,
        "project_id": 1,
        "platform": platform,
        "body": "hello world",
        "thread_json": [],
    }
    base.update(overrides)
    return base


def test_publish_due_drafts_counts_success_and_failure():
    due = [_draft(1, "x"), _draft(2, "linkedin"), _draft(3, "x")]
    updates = []

    with (
        patch("app.services.product.post_scheduler.list_due_scheduled_post_drafts", return_value=due),
        patch("app.services.product.post_scheduler.update_post_draft", side_effect=lambda db, did, data: updates.append((did, data))),
        patch("app.services.product.post_scheduler.get_project_by_id", return_value={"workspace_id": 1}),
        patch("app.services.product.post_scheduler.get_x_token", return_value="tok"),
        patch("app.services.product.post_scheduler.get_linkedin_token", return_value=None),
        patch("app.services.product.post_scheduler.get_linkedin_author_urn", return_value=None),
        patch("app.services.product.post_scheduler.XPublisher") as mock_x_publisher,
    ):
        mock_x_publisher.return_value.publish_thread.return_value = [{"id": "123", "text": "hello world"}]
        outcome = publish_due_drafts(object())

    assert outcome == {"attempted": 3, "published": 2, "failed": 1}
    statuses = {did: data["status"] for did, data in updates}
    assert statuses == {1: "published", 3: "published", 2: "needs_edit"}


def test_publish_due_drafts_no_due_items():
    with patch("app.services.product.post_scheduler.list_due_scheduled_post_drafts", return_value=[]):
        assert publish_due_drafts(object()) == {"attempted": 0, "published": 0, "failed": 0}


def test_publish_due_drafts_missing_project_marks_needs_edit():
    due = [_draft(1, "x")]
    updates = []
    with (
        patch("app.services.product.post_scheduler.list_due_scheduled_post_drafts", return_value=due),
        patch("app.services.product.post_scheduler.update_post_draft", side_effect=lambda db, did, data: updates.append((did, data))),
        patch("app.services.product.post_scheduler.get_project_by_id", return_value=None),
    ):
        outcome = publish_due_drafts(object())

    assert outcome == {"attempted": 1, "published": 0, "failed": 1}
    assert updates[0][1]["status"] == "needs_edit"


if __name__ == "__main__":
    test_publish_due_drafts_counts_success_and_failure()
    test_publish_due_drafts_no_due_items()
    test_publish_due_drafts_missing_project_marks_needs_edit()
    print("post_scheduler self-checks passed")
