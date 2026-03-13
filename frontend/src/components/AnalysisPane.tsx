import { useState } from 'react';
import { PatientCase, AuditFinding } from '@/types/audit';
import RiskBadge from '@/components/RiskBadge';
import { ChevronDown, ChevronRight, FileText, CheckCircle2, AlertTriangle, Download } from 'lucide-react';
import { patientsApi } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';

interface AnalysisPaneProps {
  patient: PatientCase;
  onOpenChat: () => void;
  onTraceToSource: (page: number) => void;
}

const moduloLabels: Record<string, string> = {
  estancia: 'Días de Estancia',
  cie10: 'Pertinencia Diagnóstico CIE-10',
  estudios: 'Estudios y Procedimientos',
  glosas: 'Detección de Glosas',
};

const formatValue = (value: any): React.ReactNode => {
  if (value == null) return '-';
  if (Array.isArray(value)) {
    if (value.length === 0) return '-';
    // primitive array: join with commas
    const primitives = value.every(v => v == null || typeof v !== 'object');
    if (primitives) return value.join(', ');
    // array of objects: render each as a styled card with key/value pairs
    return (
      <ul className="space-y-2">
        {value.map((v, i) => (
          <li key={i} className="bg-secondary/20 p-2 rounded-md">
            {typeof v === 'object' ? (
              <div className="space-y-1">
                {Object.entries(v).map(([k, val]) => (
                  <div key={k} className="flex flex-wrap gap-1">
                    <span className="font-semibold text-sm text-foreground">{k}:</span>
                    <span className="text-sm text-foreground">{formatValue(val)}</span>
                  </div>
                ))}
              </div>
            ) : (
              <span className="text-sm text-foreground">{String(v)}</span>
            )}
          </li>
        ))}
      </ul>
    );
  }
  if (typeof value === 'object') {
    return (
      <div className="ml-2">
        {Object.entries(value).map(([k, val]) => (
          <div key={k} className="flex gap-1">
            <span className="font-medium">{k}:</span>
            <span>{formatValue(val)}</span>
          </div>
        ))}
      </div>
    );
  }
  return String(value);
};

const parseExpectedDays = (str?: string): {min?: number; max?: number} => {
  if (!str) return {};
  // look for numbers separated by non-digit
  const nums = str.match(/\d+/g);
  if (!nums) return {};
  if (nums.length === 1) return {min: parseInt(nums[0], 10), max: parseInt(nums[0], 10)};
  return {min: parseInt(nums[0], 10), max: parseInt(nums[1], 10)};
};

const computeStayAlert = (actual?: number, expectedStr?: string): string | null => {
  if (actual == null) return null;
  const {min, max} = parseExpectedDays(expectedStr);
  if (max != null && actual > max) {
    const extra = actual - max;
    return `Estancia prolongada ${extra} día${extra !== 1 ? 's' : ''} — RIESGO ALTO. Se evalúa justificación diaria mediante evoluciones médicas documentadas.`;
  }
  return null;
};

const AnalysisPane = ({ patient, onOpenChat, onTraceToSource }: AnalysisPaneProps) => {
  const [openModules, setOpenModules] = useState<Record<string, boolean>>({
    estancia: true, cie10: true, estudios: true, glosas: true,
  });
  const [isDownloading, setIsDownloading] = useState(false);
  const { toast } = useToast();

  const toggleModule = (mod: string) => {
    setOpenModules(prev => ({ ...prev, [mod]: !prev[mod] }));
  };

  const handleDownloadPdf = async () => {
    try {
      setIsDownloading(true);
      const blob = await patientsApi.downloadOriginalPdf(patient.id);
      
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `historia_clinica_${patient.label}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      toast({
        title: 'PDF descargado',
        description: 'La historia clínica se descargó correctamente.',
      });
    } catch (error) {
      console.error('Error al descargar PDF:', error);
      toast({
        title: 'Error al descargar',
        description: error instanceof Error ? error.message : 'No se pudo descargar el PDF original.',
        variant: 'destructive',
      });
    } finally {
      setIsDownloading(false);
    }
  };

  const groupedFindings = patient.hallazgos.reduce<Record<string, AuditFinding[]>>((acc, f) => {
    if (!acc[f.modulo]) acc[f.modulo] = [];
    acc[f.modulo].push(f);
    return acc;
  }, {});

  const [openInfo, setOpenInfo] = useState(false);

  return (
    <div className="flex-1 overflow-y-auto p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <h1 className="font-display text-xl font-bold text-foreground">{patient.cama} — {patient.label}</h1>
          <RiskBadge level={patient.riesgo} />
        </div>
        <div className="grid grid-cols-3 gap-4 mt-4">
          <div>
            <p className="data-label">Diagnóstico principal</p>
            <p className="data-value">{patient.codigoCIE10} — {patient.diagnosticoPrincipal}</p>
          </div>
          <div>
            <p className="data-label">Días hospitalización</p>
            <p className="data-value">{patient.diasHospitalizacion} días (esperado: {patient.diasEsperados})</p>
          </div>
          <div>
            <p className="data-label">Estudios pendientes</p>
            <p className="data-value">{patient.estudiosPendientes.length > 0 ? patient.estudiosPendientes.join(', ') : 'Ninguno'}</p>
          </div>
        </div>
      </div>

      {/* Informacion de variables (acordeón) */}
      <div className="mb-4 border border-border rounded-md bg-card">
        <button
          onClick={() => setOpenInfo(prev => !prev)}
          className="w-full flex items-center justify-between p-4 hover:bg-secondary transition-colors"
        >
          <span className="font-display text-sm font-semibold text-foreground">Variables extraídas</span>
          <span>{openInfo ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}</span>
        </button>
        {openInfo && (
          <div className="border-t border-border p-4">
            <table className="w-full text-sm table-fixed">
              <thead className="bg-secondary/30">
                <tr>
                  <th className="text-left font-medium p-2 w-1/3">Variable</th>
                  <th className="text-left font-medium p-2">Valor extraído</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                <tr className="hover:bg-secondary/10 transition-colors">
                  <td className="p-2 align-top bg-secondary/10">Datos demográficos</td>
                  <td className="p-2 align-top">{formatValue(patient.edad)} años, {formatValue(patient.sexo)}</td>
                </tr>
                <tr className="hover:bg-secondary/10 transition-colors">
                  <td className="p-2 align-top bg-secondary/10">Diagnóstico principal</td>
                  <td className="p-2 align-top">{patient.codigoCIE10 ? `${patient.codigoCIE10} – ` : ''}{formatValue(patient.diagnosticoPrincipal)}</td>
                </tr>
                <tr className="hover:bg-secondary/10 transition-colors">
                  <td className="p-2 align-top bg-secondary/10">Diagnósticos secundarios</td>
                  <td className="p-2 align-top">{formatValue(patient.diagnosticosSecundarios)}</td>
                </tr>
                <tr className="hover:bg-secondary/10 transition-colors">
                  <td className="p-2 align-top bg-secondary/10">Medicamentos</td>
                  <td className="p-2 align-top">{formatValue(patient.medicamentos)}</td>
                </tr>
                <tr className="hover:bg-secondary/10 transition-colors">
                  <td className="p-2 align-top bg-secondary/10">Antecedentes</td>
                  <td className="p-2 align-top">{formatValue(patient.antecedentes)}</td>
                </tr>
                <tr className="hover:bg-secondary/10 transition-colors">
                  <td className="p-2 align-top bg-secondary/10">Evoluciones médicas</td>
                  <td className="p-2 align-top">{formatValue(patient.evoluciones)}</td>
                </tr>
                <tr className="hover:bg-secondary/10 transition-colors">
                  <td className="p-2 align-top bg-secondary/10">Estudios solicitados</td>
                  <td className="p-2 align-top">{formatValue(patient.estudiosSolicitados)}</td>
                </tr>
                <tr className="hover:bg-secondary/10 transition-colors">
                  <td className="p-2 align-top bg-secondary/10">Procedimientos</td>
                  <td className="p-2 align-top">{formatValue(patient.procedimientos)}</td>
                </tr>
                <tr className="hover:bg-secondary/10 transition-colors">
                  <td className="p-2 align-top bg-secondary/10">Días de estancia</td>
                  <td className="p-2 align-top">
                    {formatValue(patient.fechaIngreso)} → {formatValue(patient.diasHospitalizacion)} días
                    {(() => {
                      const alert = computeStayAlert(patient.diasHospitalizacion, patient.diasEsperados);
                      return alert ? (
                        <p className="mt-1 text-xs text-destructive font-semibold">{alert}</p>
                      ) : null;
                    })()}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modules */}
      {(['estancia', 'cie10', 'estudios', 'glosas'] as const).map((mod) => {
        const findings = groupedFindings[mod] || [];
        const isOpen = openModules[mod];
        const hasUnresolved = findings.some(f => !f.resuelto);

        return (
          <div key={mod} className="mb-4 border border-border rounded-md bg-card">
            <button
              onClick={() => toggleModule(mod)}
              className="w-full flex items-center justify-between p-4 hover:bg-secondary transition-colors"
            >
              <div className="flex items-center gap-2">
                {isOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                <span className="font-display text-sm font-semibold text-foreground">{moduloLabels[mod]}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-body text-muted-foreground">{findings.length} hallazgo{findings.length !== 1 ? 's' : ''}</span>
                {hasUnresolved && <AlertTriangle className="h-3.5 w-3.5 text-warning" />}
                {!hasUnresolved && findings.length > 0 && <CheckCircle2 className="h-3.5 w-3.5 text-success" />}
              </div>
            </button>
            {isOpen && findings.length > 0 && (
              <div className="border-t border-border">
                {findings.map((f) => (
                  <div key={f.id} className="px-4 py-3 border-b border-border last:border-b-0 flex items-start gap-3">
                    <div className="flex-1">
                      <p className={`font-body text-sm ${f.resuelto ? 'text-muted-foreground line-through' : 'text-foreground'}`}>
                        {f.descripcion}
                        {f.heredado && !f.resuelto && (
                          <span className="ml-2 text-xs text-muted-foreground italic">(heredado)</span>
                        )}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <RiskBadge level={f.riesgo} />
                      {f.pagina && (
                        <button
                          onClick={() => onTraceToSource(f.pagina!)}
                          className="text-xs font-body text-muted-foreground hover:text-foreground flex items-center gap-1 border border-border rounded px-1.5 py-0.5"
                          title="Ver en documento fuente"
                        >
                          <FileText className="h-3 w-3" />
                          p. {f.pagina}
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}

      {/* Recommendations */}
      <div className="mb-4 border border-border rounded-md bg-card">
        <div className="p-4">
          <h3 className="font-display text-sm font-semibold text-foreground mb-3">Recomendaciones</h3>
          <ul className="space-y-2">
            {patient.recomendaciones.map((r, i) => (
              <li key={i} className="font-body text-sm text-foreground flex items-start gap-2">
                <span className="text-muted-foreground shrink-0">→</span>
                {r}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-3 mt-6">
        <button
          onClick={handleDownloadPdf}
          disabled={isDownloading}
          className="font-body text-sm border border-border rounded-md px-4 py-2 hover:bg-secondary transition-colors text-foreground disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          <Download className="h-4 w-4" />
          {isDownloading ? 'Descargando...' : 'Descargar PDF Original'}
        </button>
        <button
          onClick={onOpenChat}
          className="font-body text-sm border border-border rounded-md px-4 py-2 hover:bg-secondary transition-colors text-foreground"
        >
          Consultar historia
        </button>
      </div>
    </div>
  );
};

export default AnalysisPane;
