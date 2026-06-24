import { apiRequest } from "../api";

export interface Invitation {
  id: string;
  workspace_id: number;
  email: string;
  role: string;
  token: string;
  expires_at: string;
  accepted_at: string | null;
  created_at: string;
  email_sent?: boolean;
}

export async function getInvitations(token: string) {
  return apiRequest<Invitation[]>(
    `/v1/invitations`, { headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function createInvitation(token: string, data: { email: string; role: string }) {
  return apiRequest<Invitation>(
    `/v1/invitations`,
    { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(data) }
  );
}

export async function deleteInvitation(token: string, invitationId: string) {
  return apiRequest<void>(
    `/v1/invitations/${invitationId}`, { method: "DELETE", headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function resendInvitation(token: string, invitationId: string) {
  return apiRequest<{ status: string }>(
    `/v1/invitations/${invitationId}/resend`,
    { method: "POST", headers: { Authorization: `Bearer ${token}` } }
  );
}
