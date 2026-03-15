/**
 * Cliente HTTP centralizado para el backend FastAPI.
 * Lee el token JWT de localStorage y lo adjunta a cada petición.
 *
 * Características:
 * - Retry automático con backoff exponencial (solo errores de red / 5xx)
 * - Límite de concurrencia: máximo MAX_CONCURRENT peticiones simultáneas
 */

const BASE_URL = import.meta.env.VITE_API_URL ?? '/api/v1';

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

// ─── Concurrency limiter ─────────────────────────────────────────────────────

const MAX_CONCURRENT = 6;
let _active = 0;
const _queue: Array<() => void> = [];

function acquireSlot(): Promise<void> {
  return new Promise(resolve => {
    if (_active < MAX_CONCURRENT) {
      _active++;
      resolve();
    } else {
      _queue.push(() => { _active++; resolve(); });
    }
  });
}

function releaseSlot() {
  _active--;
  if (_queue.length > 0) {
    const next = _queue.shift()!;
    next();
  }
}

// ─── Fetch with retry ────────────────────────────────────────────────────────

const RETRY_COUNT = 3;
const RETRY_BASE_MS = 500;

function isRetryable(error: unknown, status?: number): boolean {
  if (status !== undefined) return status >= 500;
  // Network failures (TypeError: Failed to fetch) are retryable
  return error instanceof TypeError;
}

async function fetchWithRetry(url: string, init: RequestInit): Promise<Response> {
  let lastError: unknown;
  for (let attempt = 0; attempt <= RETRY_COUNT; attempt++) {
    if (attempt > 0) {
      const delay = RETRY_BASE_MS * 2 ** (attempt - 1) + Math.random() * 100;
      await new Promise(r => setTimeout(r, delay));
    }
    try {
      const res = await fetch(url, init);
      if (res.ok || !isRetryable(null, res.status)) return res;
      lastError = new ApiError(res.status, `HTTP ${res.status}`);
    } catch (err) {
      lastError = err;
      if (!isRetryable(err)) throw err;
    }
  }
  throw lastError;
}

// ─── Core request ────────────────────────────────────────────────────────────

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(init.headers as Record<string, string>),
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  await acquireSlot();
  try {
    const res = await fetchWithRetry(`${BASE_URL}${path}`, { ...init, headers });

    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new ApiError(res.status, body.detail ?? 'Error desconocido');
    }

    // 204 No Content
    if (res.status === 204) return undefined as T;
    return res.json() as Promise<T>;
  } finally {
    releaseSlot();
  }
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
  | 'cargando' | 'subido' | 'extrayendo' | 'extraido'
  | 'anonimizando' | 'analizando' | 'listo' | 'error';

export interface UploadResponse {
  session_id: string;
  status: DocumentStatus;
  message: string;
  progress: number;
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

// ─── Processing (etapas 2 y 3) ────────────────────────────────────────────────────────

export interface AiProgress {
  status: string;
  ai_chunks_done: number;
  ai_chunks_total: number;
}

export interface BatchResult {
  session_id: string;
  batch_done: number;
  total_batches: number;
  is_last: boolean;
  status: DocumentStatus;
  message: string;
}

export const processingApi = {
  extract: (sessionId: string) =>
    request<UploadResponse>(`/processing/${sessionId}/extract`, { method: 'POST' }),

  process: (sessionId: string) =>
    request<UploadResponse>(`/processing/${sessionId}/process`, { method: 'POST' }),

  processBatch: (sessionId: string) =>
    request<BatchResult>(`/processing/${sessionId}/process_batch`, { method: 'POST' }),

  partialFinalize: (sessionId: string) =>
    request<UploadResponse>(`/processing/${sessionId}/partial_finalize`, { method: 'POST' }),

  getProgress: (sessionId: string) =>
    request<AiProgress>(`/processing/${sessionId}/progress`),
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
  heredado: boolean;
  recomendacion: string | null;
  categoria: string | null;
  normativa_aplicable: string | null;
  valor_glosa_estimado: number | null;
  estado: string;
  created_at: string;
}

export interface AuditSummary {
  riesgo_global: 'alto' | 'medio' | 'bajo' | 'pending';
  total_hallazgos: number;
  exposicion_glosas: number;
  hallazgos_por_riesgo: Record<string, number>;
  hallazgos_por_modulo: Record<string, number>;
  hallazgos: AuditFinding[];
  recomendacion_general: string;
  paciente: {
    id: string;
    label: string;
    // sample of fields returned by backend (PatientCaseRead)
    edad?: number;
    sexo?: string;
    diagnostico_principal: string | null;
    codigo_cie10: string | null;
    diagnosticos_secundarios?: any[];
    fecha_ingreso?: string; // ISO date string
    fecha_egreso?: string;
    dias_hospitalizacion?: number;
    dias_esperados?: string | null;
    medicamentos?: any[];
    antecedentes?: any;
    estudios_solicitados?: any[];
    procedimientos?: any[];
    evoluciones?: any[];
  };
}

export interface PatientControlBoard {
  id: string;
  cama: string | null;
  historia: string;
  diagnostico: string;
  dias_hospitalizacion: number;
  dias_esperados: string;
  estudios_pendientes: string[];
  riesgo_glosa: 'alto' | 'medio' | 'bajo' | 'pending';
  total_hallazgos: number;
  exposicion_glosas: number;
  audit_status: 'pending' | 'processing' | 'completed';
  fecha_ultima_auditoria: string | null;
}

export interface AuditSessionStatus {
  id: string;
  patient_id: string | null;
  ultima_pagina_auditada: number;
  total_paginas_conocidas: number;
  porcentaje_completado: number;
  fecha_ultima_auditoria: string | null;
  status: string;
  tiene_progreso_previo: boolean;
}

export interface ResetResponse {
  relaunched: boolean;
  message: string;
}

export const patientsApi = {
  list: () => request<PatientSummary[]>('/patients/'),

  get: (id: string) => request<PatientSummary>(`/patients/${id}`),

  findings: (id: string) => request<AuditFinding[]>(`/patients/${id}/findings`),

  audit: (id: string) => request<AuditSummary>(`/patients/${id}/audit`),

  getSession: (id: string) =>
    request<AuditSessionStatus>(`/patients/${id}/session`),

  resetSession: (id: string) =>
    request<ResetResponse>(`/patients/${id}/session/reset`, { method: 'POST' }),

  controlBoard: (filters?: { risk_level?: string; audit_status?: string }) => {
    const params = new URLSearchParams();
    if (filters?.risk_level) params.append('risk_level', filters.risk_level);
    if (filters?.audit_status) params.append('audit_status', filters.audit_status);
    const query = params.toString() ? `?${params.toString()}` : '';
    return request<PatientControlBoard[]>(`/patients/control-board${query}`);
  },

  resolveFinding: (patientId: string, findingId: string, resuelto: boolean) =>
    request<AuditFinding>(`/patients/${patientId}/findings/${findingId}`, {
      method: 'PATCH',
      body: JSON.stringify({ resuelto }),
    }),

  exportPdf: (id: string) => {
    const token = getToken();
    return fetch(`${BASE_URL}/patients/${id}/export/pdf`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    }).then(async res => {
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new ApiError(res.status, body.detail ?? 'Error al exportar PDF');
      }
      return res.blob();
    });
  },

  exportExcel: (id: string) => {
    const token = getToken();
    return fetch(`${BASE_URL}/patients/${id}/export/excel`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    }).then(async res => {
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new ApiError(res.status, body.detail ?? 'Error al exportar Excel');
      }
      return res.blob();
    });
  },

  exportHtml: (id: string) => {
    const token = getToken();
    return fetch(`${BASE_URL}/patients/${id}/export/html`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    }).then(async res => {
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new ApiError(res.status, body.detail ?? 'Error al exportar HTML');
      }
      return res.text();
    });
  },

  downloadOriginalPdf: (id: string) => {
    const token = getToken();
    return fetch(`${BASE_URL}/patients/${id}/download/original`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    }).then(async res => {
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new ApiError(res.status, body.detail ?? 'Error al descargar PDF original');
      }
      return res.blob();
    });
  },
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
  patient_ids?: string[];
}

export interface RagReference {
  chunk_index: number;
  page_number: number;
  text_snippet: string;
  relevance_score: number;
}

export interface RagChatResponse {
  answer: string;
  references: RagReference[];
  model_used: string;
  chunks_total: number;
  chunks_used: number;
}

export const chatApi = {
  ask: (patient_id: string, question: string) =>
    request<ChatResponse>('/chat/', {
      method: 'POST',
      body: JSON.stringify({ patient_id, question }),
    }),

  history: (patientId: string) =>
    request<ChatMessage[]>(`/chat/history/${patientId}`),

  askMulti: (question: string, patient_ids: string[]) =>
    request<ChatResponse>('/chat/multi-history', {
      method: 'POST',
      body: JSON.stringify({ question, patient_ids }),
    }),

  askRag: (session_id: string, question: string, history: { role: string; content: string }[] = []) =>
    request<RagChatResponse>('/chat/rag', {
      method: 'POST',
      body: JSON.stringify({ session_id, question, history }),
    }),
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
