export type RiskLevel = 'ALTO' | 'MEDIO' | 'BAJO';

export type FileStatus = 'idle' | 'cargando' | 'anonimizando' | 'extrayendo' | 'analizando' | 'listo' | 'error';

export interface UploadedFile {
  id: string;
  name: string;
  size: number;
  status: FileStatus;
  progress: number;
  label?: string; // Historia A, B, C...
  startPage?: number;
}

export interface PatientCase {
  id: string;
  label: string;
  cama: string;
  diagnosticoPrincipal: string;
  codigoCIE10: string;
  diasHospitalizacion: number;
  diasEsperados: string;
  riesgo: RiskLevel;
  estudiosPendientes: string[];
  hallazgos: AuditFinding[];
  recomendaciones: string[];
}

export interface AuditFinding {
  id: string;
  modulo: 'estancia' | 'cie10' | 'estudios' | 'glosas';
  descripcion: string;
  riesgo: RiskLevel;
  pagina?: number;
  resuelto: boolean;
}
