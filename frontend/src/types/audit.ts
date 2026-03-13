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
  edad?: number;
  sexo?: string;
  diagnosticoPrincipal: string;
  codigoCIE10: string;
  diagnosticosSecundarios?: any[];
  fechaIngreso?: string;
  diasHospitalizacion: number;
  diasEsperados: string;
  medicamentos?: any[];
  antecedentes?: any;
  estudiosSolicitados?: any[];
  procedimientos?: any[];
  evoluciones?: any[];
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
