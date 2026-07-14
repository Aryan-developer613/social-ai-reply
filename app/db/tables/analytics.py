"""Analytics table operations: analytics snapshots, audit events, auto pipelines, visibility snapshots."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from supabase import Client

ANALYTICS_SNAPSHOTS_TABLE = "analytics_snapshots"
AUDIT_EVENTS_TABLE = "audit_events"
AUTO_PIPELINES_TABLE = "auto_pipelines"
VISIBILITY_SNAPSHOTS_TABLE = "visibility_snapshots"


# Analytics snapshot operations
def get_analytics_snapshot_by_id(db: Client, snapshot_id: str) -> dict[str, Any] | None:
    """Get an analytics snapshot by ID."""
    result = db.table(ANALYTICS_SNAPSHOTS_TABLE).select("*").eq("id", snapshot_id).execute()
    return result.data[0] if result.data else None


def get_analytics_snapshot_by_project_and_date(
    db: Client,
    project_id: int,
    date: str,
) -> dict[str, Any] | None:
    """Get an analytics snapshot by project ID and date."""
    result = (
        db.table(ANALYTICS_SNAPSHOTS_TABLE)
        .select("*")
        .eq("project_id", project_id)
        .eq("snapshot_date", date)
        .execute()
    )
    return result.data[0] if result.data else None


def list_analytics_snapshots_for_project(
    db: Client,
    project_id: int,
    limit: int = 30,
) -> list[dict[str, Any]]:
    """List analytics snapshots for a project."""
    result = (
        db.table(ANALYTICS_SNAPSHOTS_TABLE)
        .select("*")
        .eq("project_id", project_id)
        .order("snapshot_date", desc=True)
        .limit(limit)
        .execute()
    )
    return list(result.data)


def create_analytics_snapshot(db: Client, snapshot_data: dict[str, Any]) -> dict[str, Any]:
    """Create a new analytics snapshot."""
    result = db.table(ANALYTICS_SNAPSHOTS_TABLE).insert(snapshot_data).execute()
    return result.data[0]


def update_analytics_snapshot(
    db: Client,
    snapshot_id: str,
    update_data: dict[str, Any],
) -> dict[str, Any] | None:
    """Update an analytics snapshot."""
    result = db.table(ANALYTICS_SNAPSHOTS_TABLE).update(update_data).eq("id", snapshot_id).execute()
    return result.data[0] if result.data else None


def delete_analytics_snapshot(db: Client, snapshot_id: str) -> None:
    """Delete an analytics snapshot."""
    db.table(ANALYTICS_SNAPSHOTS_TABLE).delete().eq("id", snapshot_id).execute()


# Audit event operations
def get_audit_event_by_id(db: Client, event_id: int) -> dict[str, Any] | None:
    """Get an audit event by ID."""
    result = db.table(AUDIT_EVENTS_TABLE).select("*").eq("id", event_id).execute()
    return result.data[0] if result.data else None


def list_audit_events_for_workspace(
    db: Client,
    workspace_id: int,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """List audit events for a workspace."""
    result = (
        db.table(AUDIT_EVENTS_TABLE)
        .select("*")
        .eq("workspace_id", workspace_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return list(result.data)


def create_audit_event(db: Client, event_data: dict[str, Any]) -> dict[str, Any]:
    """Create a new audit event."""
    result = db.table(AUDIT_EVENTS_TABLE).insert(event_data).execute()
    return result.data[0]


def delete_audit_event(db: Client, event_id: int) -> None:
    """Delete an audit event."""
    db.table(AUDIT_EVENTS_TABLE).delete().eq("id", event_id).execute()


# Auto pipeline operations
def get_auto_pipeline_by_id(db: Client, pipeline_id: str) -> dict[str, Any] | None:
    """Get an auto pipeline by ID."""
    result = db.table(AUTO_PIPELINES_TABLE).select("*").eq("id", pipeline_id).execute()
    return result.data[0] if result.data else None


def list_auto_pipelines_for_project(
    db: Client,
    project_id: int,
    limit: int = 20,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """List auto pipelines for a project."""
    result = (
        db.table(AUTO_PIPELINES_TABLE)
        .select("*")
        .eq("project_id", project_id)
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return list(result.data)


def create_auto_pipeline(db: Client, pipeline_data: dict[str, Any]) -> dict[str, Any]:
    """Create a new auto pipeline."""
    result = db.table(AUTO_PIPELINES_TABLE).insert(pipeline_data).execute()
    return result.data[0]


def update_auto_pipeline(
    db: Client,
    pipeline_id: str,
    update_data: dict[str, Any],
) -> dict[str, Any] | None:
    """Update an auto pipeline."""
    result = db.table(AUTO_PIPELINES_TABLE).update(update_data).eq("id", pipeline_id).execute()
    return result.data[0] if result.data else None


def delete_auto_pipeline(db: Client, pipeline_id: str) -> None:
    """Delete an auto pipeline."""
    db.table(AUTO_PIPELINES_TABLE).delete().eq("id", pipeline_id).execute()


# Visibility snapshot operations
def get_visibility_snapshot_by_id(db: Client, snapshot_id: int) -> dict[str, Any] | None:
    """Get a visibility snapshot by ID."""
    result = db.table(VISIBILITY_SNAPSHOTS_TABLE).select("*").eq("id", snapshot_id).execute()
    return result.data[0] if result.data else None


def list_visibility_snapshots_for_project(
    db: Client,
    project_id: int,
    limit: int = 30,
) -> list[dict[str, Any]]:
    """List visibility snapshots for a project."""
    result = (
        db.table(VISIBILITY_SNAPSHOTS_TABLE)
        .select("*")
        .eq("project_id", project_id)
        .order("snapshot_date", desc=True)
        .limit(limit)
        .execute()
    )
    return list(result.data)


def create_visibility_snapshot(db: Client, snapshot_data: dict[str, Any]) -> dict[str, Any]:
    """Create a new visibility snapshot."""
    result = db.table(VISIBILITY_SNAPSHOTS_TABLE).insert(snapshot_data).execute()
    return result.data[0]


def delete_visibility_snapshot(db: Client, snapshot_id: int) -> None:
    """Delete a visibility snapshot."""
    db.table(VISIBILITY_SNAPSHOTS_TABLE).delete().eq("id", snapshot_id).execute()
