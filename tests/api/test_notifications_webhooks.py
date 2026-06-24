"""API regressions for notifications and webhooks authorization/security."""
from fastapi.testclient import TestClient

from app.db.tables.system import create_notification
from app.db.tables.users import create_user
from app.db.tables.webhooks import create_webhook_endpoint
from app.db.tables.workspaces import create_membership


def _register_owner(client: TestClient) -> dict:
    response = client.post(
        "/v1/auth/register",
        json={
            "email": "owner@example.com",
            "password": "strongpass123",
            "full_name": "Owner User",
            "workspace_name": "Owner Workspace",
        },
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    client.headers.update({"Authorization": f"Bearer {payload['access_token']}"})
    return payload


def _add_member(mock_supabase, workspace_id: int, email: str = "member@example.com") -> dict:
    member = create_user(
        mock_supabase,
        {
            "email": email,
            "supabase_user_id": f"test-member-{email}",
            "full_name": "Member User",
        }
    )
    create_membership(
        mock_supabase,
        {
            "workspace_id": workspace_id,
            "user_id": member["id"],
            "role": "member",
        }
    )
    return member


class TestNotificationAuthorization:
    def test_mark_read_cannot_touch_another_users_personal_notification(self, client, mock_supabase):
        payload = _register_owner(client)
        workspace_id = payload["workspace"]["id"]
        member = _add_member(mock_supabase, workspace_id)

        notification = create_notification(
            mock_supabase,
            {
                "workspace_id": workspace_id,
                "user_id": member["id"],
                "type": "mention",
                "title": "Member-only notification",
                "body": "Private notification body",
                "is_read": False,
            }
        )

        response = client.put(f"/v1/notifications/{notification['id']}/read")

        assert response.status_code == 404
        # Verify notification is still unread
        from app.db.tables.system import get_notification_by_id
        notif = get_notification_by_id(mock_supabase, notification["id"])
        assert notif["is_read"] is False

    def test_delete_cannot_touch_another_users_personal_notification(self, client, mock_supabase):
        payload = _register_owner(client)
        workspace_id = payload["workspace"]["id"]
        member = _add_member(mock_supabase, workspace_id, email="member-delete@example.com")

        notification = create_notification(
            mock_supabase,
            {
                "workspace_id": workspace_id,
                "user_id": member["id"],
                "type": "mention",
                "title": "Delete-protected notification",
                "body": "Private notification body",
            }
        )

        response = client.delete(f"/v1/notifications/{notification['id']}")

        assert response.status_code == 404
        # Verify notification still exists
        from app.db.tables.system import get_notification_by_id
        still_exists = get_notification_by_id(mock_supabase, notification["id"])
        assert still_exists is not None

    def test_mark_read_can_touch_workspace_wide_notification(self, client, mock_supabase):
        """Workspace members can mark workspace-wide notifications as read.

        Changed contract (Issue #25): any workspace member can modify
        workspace-wide notifications since they apply to the whole workspace.
        """
        payload = _register_owner(client)
        workspace_id = payload["workspace"]["id"]

        notification = create_notification(
            mock_supabase,
            {
                "workspace_id": workspace_id,
                "user_id": None,
                "type": "mention",
                "title": "Workspace-wide notification",
                "body": "Visible to every member",
                "is_read": False,
            }
        )

        response = client.put(f"/v1/notifications/{notification['id']}/read")

        assert response.status_code == 200
        from app.db.tables.system import get_notification_by_id
        notif = get_notification_by_id(mock_supabase, notification["id"])
        assert notif["is_read"] is True

    def test_delete_can_touch_workspace_wide_notification(self, client, mock_supabase):
        """Workspace members can delete workspace-wide notifications.

        Changed contract (Issue #25): any workspace member can modify
        workspace-wide notifications since they apply to the whole workspace.
        """
        payload = _register_owner(client)
        workspace_id = payload["workspace"]["id"]

        notification = create_notification(
            mock_supabase,
            {
                "workspace_id": workspace_id,
                "user_id": None,
                "type": "mention",
                "title": "Shared notification",
                "body": "Visible to every member",
            }
        )

        response = client.delete(f"/v1/notifications/{notification['id']}")

        assert response.status_code == 200
        from app.db.tables.system import get_notification_by_id
        assert get_notification_by_id(mock_supabase, notification["id"]) is None

    def test_mark_all_read_updates_workspace_wide_and_personal_notifications(self, client, mock_supabase):
        """mark-all-read touches both personal and workspace-wide notifications.

        Changed contract (Issue #25): workspace-wide notifications are
        also considered when marking all as read since they appear in
        every member's inbox.
        """
        payload = _register_owner(client)
        workspace_id = payload["workspace"]["id"]

        personal_notification = create_notification(
            mock_supabase,
            {
                "workspace_id": workspace_id,
                "user_id": payload["user"]["id"],
                "type": "mention",
                "title": "Personal notification",
                "body": "Should be marked read",
                "is_read": False,
            }
        )
        shared_notification = create_notification(
            mock_supabase,
            {
                "workspace_id": workspace_id,
                "user_id": None,
                "type": "mention",
                "title": "Workspace-wide notification",
                "body": "Should be marked read",
                "is_read": False,
            }
        )

        response = client.put("/v1/notifications/read-all")

        assert response.status_code == 200
        from app.db.tables.system import get_notification_by_id
        personal = get_notification_by_id(mock_supabase, personal_notification["id"])
        shared = get_notification_by_id(mock_supabase, shared_notification["id"])
        assert personal["is_read"] is True
        assert shared["is_read"] is True


class TestWebhookSecurity:
    def test_test_webhook_revalidates_stored_target_url(self, client, mock_supabase):
        payload = _register_owner(client)
        workspace_id = payload["workspace"]["id"]

        webhook = create_webhook_endpoint(
            mock_supabase,
            {
                "workspace_id": workspace_id,
                "target_url": "http://localhost:9000/hook",
                "signing_secret": "test-secret",
                "event_types": ["webhook.test"],
                "is_active": True,
            }
        )

        response = client.post(f"/v1/webhooks/{webhook['id']}/test", json={"event_type": "webhook.test"})

        assert response.status_code == 422
        assert response.json()["detail"] == "Internal URLs are not allowed."
