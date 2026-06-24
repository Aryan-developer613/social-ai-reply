import { apiRequest } from "../api";
import type { Persona } from "../api";

export type { Persona };

export async function getPersonas(token: string, projectId: number) {
  return apiRequest<Persona[]>(
    `/v1/personas?project_id=${projectId}`, { headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function getPersona(token: string, personaId: number) {
  return apiRequest<Persona>(
    `/v1/personas/${personaId}`, { headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function createPersona(token: string, projectId: number, data: Partial<Persona>) {
  return apiRequest<Persona>(
    `/v1/personas?project_id=${projectId}`,
    { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(data) }
  );
}

export async function updatePersona(token: string, personaId: number, data: Partial<Persona>) {
  return apiRequest<Persona>(
    `/v1/personas/${personaId}`,
    { method: "PUT", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(data) }
  );
}

export async function deletePersona(token: string, personaId: number) {
  return apiRequest<void>(
    `/v1/personas/${personaId}`, { method: "DELETE", headers: { Authorization: `Bearer ${token}` } }
  );
}
