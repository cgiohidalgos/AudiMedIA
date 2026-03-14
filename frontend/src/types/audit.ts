export type RiskLevel = 'ALTO' | 'MEDIO' | 'BAJO';

export type FileStatus =
  | 'idle'         // en cola, aún no subido
  | 'cargando'     // subiendo al servidor
  | 'subido'       // Etapa 1 completa: PDF guardado
  | 'extrayendo'   // Etapa 2 en curso: extrayendo texto
  | 'extraido'     // Etapa 2 completa: chunks guardados
  | 'anonimizando'
  | 'analizando'   // Etapa 3 en curso: IA procesando
  | 'listo'        // Todo completado
  | 'error';

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
