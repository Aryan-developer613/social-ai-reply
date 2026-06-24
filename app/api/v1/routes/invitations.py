"""Invitation management endpoints."""
import logging
import secrets
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from app.api.v1.deps import ensure_workspace_membership, get_current_user, get_current_workspace
from app.db.supabase_client import get_supabase
from app.db.tables.users import get_user_by_email
from app.db.tables.workspaces import (
    create_invitation as create_invitation_table,
)
from app.db.tables.workspaces import (
    get_invitation_by_token,
    list_invitations_for_workspace,
    update_invitation,
)
from app.schemas.v1.invitations import InvitationRequest, InvitationResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["invitations"])


@router.get("/invitations", response_model=list[InvitationResponse])
def list_invitations(
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> list[InvitationResponse]:
    membership = ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    if membership.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Only admins can manage invitations.")
    rows = list_invitations_for_workspace(supabase, workspace["id"])
    # Filter for pending invitations
    rows = [r for r in rows if not r.get("accepted_at") and r.get("expires_at", datetime.now(UTC).isoformat()) > datetime.now(UTC).isoformat()]
    return [InvitationResponse.model_validate(row) for row in rows]


@router.post("/invitations", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED)
def create_invitation_endpoint(
    payload: InvitationRequest,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> InvitationResponse:
    membership = ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    if membership.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Only admins can invite teammates.")

    # Check if email is already a workspace member
    from app.db.tables.workspaces import get_membership_by_user_and_workspace
    target_user = get_user_by_email(supabase, payload.email.lower())
    if target_user:
        existing_member = get_membership_by_user_and_workspace(supabase, target_user["id"], workspace["id"])
        if existing_member:
            raise HTTPException(status_code=409, detail="User is already a member of this workspace.")

    # Check for pending invitation
    from app.db.tables.workspaces import get_invitation_by_workspace_and_email
    pending = get_invitation_by_workspace_and_email(
        supabase,
        workspace["id"],
        payload.email.lower(),
    )
    if pending and not pending.get("accepted_at") and pending.get("expires_at", datetime.now(UTC).isoformat()) > datetime.now(UTC).isoformat():
        raise HTTPException(status_code=409, detail="A pending invitation already exists for this email.")

    token = secrets.token_urlsafe(32)
    invitation = create_invitation_table(
        supabase,
        {
            "workspace_id": workspace["id"],
            "email": payload.email.lower(),
            "role": payload.role,
            "invited_by_user_id": current_user["id"],
            "token": token,
        },
    )

    email_sent = True
    try:
        from app.services.product.email_service import EmailService
        inviter_name = current_user.get("full_name") or current_user.get("email", "A teammate")
        workspace_name = workspace.get("name", "a workspace")
        EmailService.send_invitation(
            to_email=payload.email.lower(),
            workspace_name=workspace_name,
            inviter_name=inviter_name,
            token=token,
        )
    except Exception as email_err:
        email_sent = False
        logger.warning("Failed to send invitation email to %s: %s", payload.email, email_err)

    response = InvitationResponse.model_validate(invitation)
    # Include email delivery status so the inviter knows when to resend (Issue #44).
    response = response.model_copy(update={"email_sent": email_sent})
    return response


@router.post("/invitations/accept/{token}", response_model=InvitationResponse)
def accept_invitation(
    token: str,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
) -> InvitationResponse:
    invitation = get_invitation_by_token(supabase, token)
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found.")
    if invitation.get("accepted_at"):
        raise HTTPException(status_code=400, detail="Invitation already accepted.")
    if invitation.get("expires_at", datetime.now(UTC).isoformat()) < datetime.now(UTC).isoformat():
        raise HTTPException(status_code=410, detail="Invitation has expired.")
    if invitation["email"] != current_user["email"]:
        raise HTTPException(status_code=403, detail="Invitation email does not match the current user.")

    from app.db.tables.workspaces import create_membership, get_membership_by_user_and_workspace
    existing = get_membership_by_user_and_workspace(supabase, current_user["id"], invitation["workspace_id"])
    if not existing:
        create_membership(
            supabase,
            {
                "workspace_id": invitation["workspace_id"],
                "user_id": current_user["id"],
                "role": invitation["role"],
            },
        )

    updated = update_invitation(
        supabase,
        invitation["id"],
        {"accepted_at": datetime.now(UTC).isoformat()},
    )
    return InvitationResponse.model_validate(updated)
