/**
 * Cliente HTTP centralizado para el backend FastAPI.
 * Lee el token JWT de localStorage y lo adjunta a cada petición.
 */

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1';

const TOKEN_KEY = 'audiomedia_token';

export function saveToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(init.headers as Record<string, string>),
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${BASE_URL}${path}`, { ...init, headers });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail ?? 'Error desconocido');
  }

  // 204 No Content
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

// ─── Auth ───────────────────────────────────────────────────────────────────

export interface ApiUser {
  id: string;
  email: string;
  full_name: string;
  role: 'admin' | 'auditor' | 'coordinador' | 'equipo_medico';
  is_active: boolean;
  created_at: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: ApiUser;
}

export const authApi = {
  login: (email: string, password: string) =>
    request<LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  register: (email: string, password: string, full_name: string) =>
    request<ApiUser>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, full_name }),
    }),

  me: () => request<ApiUser>('/users/me'),
};

// ─── Upload ─────────────────────────────────────────────────────────────────

export type DocumentStatus =
  | 'cargando' | 'anonimizando' | 'extrayendo' | 'analizando' | 'listo' | 'error';

export interface UploadResponse {
  session_id: string;
  status: DocumentStatus;
  message: string;
}

export const uploadApi = {
  uploadPdfs: (files: File[]): Promise<UploadResponse[]> => {
    const token = getToken();
    const form = new FormData();
    files.forEach(f => form.append('files', f));
    return fetch(`${BASE_URL}/upload/`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    }).then(async res => {
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new ApiError(res.status, body.detail ?? 'Error al cargar archivos');
      }
      return res.json();
    });
  },

  getStatus: (sessionId: string) =>
    request<UploadResponse>(`/upload/status/${sessionId}`),
};

// ─── Pacientes ───────────────────────────────────────────────────────────────

export interface PatientSummary {
  id: string;
  label: string;
  cama: string | null;
  diagnostico_principal: string | null;
  codigo_cie10: string | null;
  dias_hospitalizacion: number | null;
  dias_esperados: string | null;
  riesgo: 'bajo' | 'medio' | 'alto';
}

export interface AuditFinding {
  id: string;
  modulo: 'estancia' | 'cie10' | 'estudios' | 'glosas';
  descripcion: string;
  riesgo: 'bajo' | 'medio' | 'alto';
  pagina: number | null;
  resuelto: boolean;
  recomendacion: string | null;
}

export const patientsApi = {
  list: () => request<PatientSummary[]>('/patients/'),

  get: (id: string) => request<PatientSummary>(`/patients/${id}`),

  findings: (id: string) => request<AuditFinding[]>(`/patients/${id}/findings`),

  resolveFinding: (patientId: string, findingId: string, resuelto: boolean) =>
    request<AuditFinding>(`/patients/${patientId}/findings/${findingId}`, {
      method: 'PATCH',
      body: JSON.stringify({ resuelto }),
    }),
};

// ─── Chat ────────────────────────────────────────────────────────────────────

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  referencias: { pagina: number; fragmento: string }[];
}

export interface ChatResponse {
  answer: string;
  referencias: { pagina: number; fragmento: string }[];
}

export const chatApi = {
  ask: (patient_id: string, question: string) =>
    request<ChatResponse>('/chat/', {
      method: 'POST',
      body: JSON.stringify({ patient_id, question }),
    }),

  history: (patientId: string) =>
    request<ChatMessage[]>(`/chat/history/${patientId}`),
};

// ─── Dashboard ───────────────────────────────────────────────────────────────

export interface DashboardMetrics {
  historias_auditadas: number;
  glosas_evitadas: number;
  ahorro_estimado: number;
  estancias_prolongadas: number;
  riesgo_alto: number;
  pendientes_resueltos: number;
  tiempo_promedio_auditoria_min: number;
}

export const dashboardApi = {
  metrics: () => request<DashboardMetrics>('/dashboard/metrics'),
};
