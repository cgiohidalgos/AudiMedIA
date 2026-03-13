import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { usePermissions } from '@/components/RoleGuard';
import { useLocation } from 'react-router-dom';
import UploadScreen from '@/components/UploadScreen';
import PatientSidebar from '@/components/PatientSidebar';
import AnalysisPane from '@/components/AnalysisPane';
import ChatPanel from '@/components/ChatPanel';
import ControlTable from '@/components/ControlTable';
import AppNavbar from '@/components/AppNavbar';
import { patientsApi, type AuditSummary } from '@/lib/api';
import { Loader2, ChevronDown, FileText } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

type View = 'upload' | 'results' | 'control';

// Tipo adaptado para el componente (mapea de API a UI)
interface PatientForUI {
  id: string;
  label: string;
  cama: string;
  edad?: number;
  sexo?: string;
  diagnosticoPrincipal: string;
  codigoCIE10: string;
  diagnosticosSecundarios?: any[];
  fechaIngreso?: string;
  fechaEgreso?: string;
  diasHospitalizacion: number;
  diasEsperados: string;
  medicamentos?: any[];
  antecedentes?: any;
  estudiosSolicitados?: any[];
  procedimientos?: any[];
  evoluciones?: any[];
  riesgo: 'ALTO' | 'MEDIO' | 'BAJO';
  estudiosPendientes: string[];
  hallazgos: any[];
  recomendaciones: string[];
}

const AppPage = () => {
  const { role } = useAuth();
  const permissions = usePermissions();
  const location = useLocation();
  const { toast } = useToast();

  // Si venimos de otra página con state.view, usarlo como vista inicial
  const initialView = (location.state as any)?.view ?? (permissions.canUpload ? 'upload' : 'results');
  const [view, setView] = useState<View>(initialView);
  const [patients, setPatients] = useState<PatientForUI[]>([]);
  const [isLoadingPatients, setIsLoadingPatients] = useState(false);
  const [pollingForUpload, setPollingForUpload] = useState(false);
  const [uploadError, setUploadError] = useState(false);
  const [pollCounter, setPollCounter] = useState(0);
  const [toastMinimized, setToastMinimized] = useState(false);
  const [selectedPatientId, setSelectedPatientId] = useState<string>('');
  const [chatOpen, setChatOpen] = useState(false);

  // Fetch patients from API
  useEffect(() => {
    if (view !== 'results' && view !== 'control') return;

    const fetchPatients = async () => {
      try {
        setIsLoadingPatients(true);
        const summaries = await patientsApi.list();

        if (summaries.length === 0) {
          setPatients([]);
          return;
        }

        // Pacientes encontrados — detener polling
        setPollingForUpload(false);

        const patientsWithDetails = await Promise.all(
          summaries.map(async (summary) => {
            try {
              const auditData = await patientsApi.audit(summary.id);
              return mapAuditToPatient(auditData);
            } catch (error) {
              console.error(`Error fetching audit for patient ${summary.id}:`, error);
              return mapSummaryToPatient(summary);
            }
          })
        );

        setPatients(patientsWithDetails);
        if (patientsWithDetails.length > 0) {
          setSelectedPatientId(patientsWithDetails[0].id);
        }
      } catch (error) {
        console.error('Error fetching patients:', error);
        if (!pollingForUpload) {
          toast({
            title: 'Error al cargar pacientes',
            description: 'No se pudo conectar con el servidor',
            variant: 'destructive',
          });
        }
        setPatients([]);
      } finally {
        setIsLoadingPatients(false);
      }
    };

    fetchPatients();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view, pollCounter]);

  // Polling loop: cuando viene de upload y no hay pacientes aún, reintenta cada 5s
  useEffect(() => {
    if (!pollingForUpload || patients.length > 0 || view !== 'results') return;

    const timer = setTimeout(() => {
      setPollCounter(c => c + 1);
    }, 5000);

    return () => clearTimeout(timer);
  }, [pollingForUpload, patients.length, view, isLoadingPatients]);

  // Helper: Map AuditSummary to PatientForUI
  function mapAuditToPatient(audit: AuditSummary): PatientForUI {
    return {
      id: audit.paciente.id,
      label: audit.paciente.label || 'N/A',
      cama: 'Cama N/A', // Not in audit response
      edad: audit.paciente.edad,
      sexo: audit.paciente.sexo,
      diagnosticoPrincipal: audit.paciente.diagnostico_principal || 'N/A',
      codigoCIE10: audit.paciente.codigo_cie10 || 'N/A',
      diagnosticosSecundarios: audit.paciente.diagnosticos_secundarios || [],
      fechaIngreso: audit.paciente.fecha_ingreso || undefined,
      fechaEgreso: audit.paciente.fecha_egreso || undefined,
      diasHospitalizacion: audit.paciente.dias_hospitalizacion || 0,
      diasEsperados: audit.paciente.dias_esperados || 'N/A',
      medicamentos: audit.paciente.medicamentos || [],
      antecedentes: audit.paciente.antecedentes || {},
      estudiosSolicitados: audit.paciente.estudios_solicitados || [],
      procedimientos: audit.paciente.procedimientos || [],
      evoluciones: audit.paciente.evoluciones || [],
      riesgo: audit.riesgo_global.toUpperCase() as 'ALTO' | 'MEDIO' | 'BAJO',
      estudiosPendientes: [],
      hallazgos: audit.hallazgos.map(h => ({
        id: h.id,
        modulo: h.modulo,
        descripcion: h.descripcion,
        riesgo: h.riesgo.toUpperCase(),
        pagina: h.pagina,
        resuelto: h.estado === 'resuelto',
        heredado: h.heredado || false,
        recomendacion: h.recomendacion,
        categoria: h.categoria,
        normativa_aplicable: h.normativa_aplicable,
        valor_glosa_estimado: h.valor_glosa_estimado,
      })),
      recomendaciones: [audit.recomendacion_general],
    };
  }

  // Helper: Map PatientSummary to PatientForUI (fallback)
  function mapSummaryToPatient(summary: any): PatientForUI {
    return {
      id: summary.id,
      label: summary.label || 'N/A',
      cama: summary.cama || 'N/A',
      diagnosticoPrincipal: summary.diagnostico_principal || 'N/A',
      codigoCIE10: summary.codigo_cie10 || 'N/A',
      diasHospitalizacion: summary.dias_hospitalizacion || 0,
      diasEsperados: summary.dias_esperados || 'N/A',
      riesgo: (summary.riesgo || 'bajo').toUpperCase() as 'ALTO' | 'MEDIO' | 'BAJO',
      estudiosPendientes: [],
      hallazgos: [],
      recomendaciones: [],
    };
  }

  const selectedPatient = patients.find(p => p.id === selectedPatientId) || patients[0];

  if (view === 'upload' && permissions.canUpload) {
    return (
      <div className="min-h-screen flex flex-col bg-background">
        <AppNavbar currentView="upload" onViewChange={setView} />
        <div className="flex-1">
          <UploadScreen
            onStartAnalysis={(hadErrors) => {
              setPollingForUpload(!hadErrors);
              setUploadError(hadErrors);
              setView('results');
            }}
          />
        </div>
      </div>
    );
  }

  if (view === 'control') {
    return (
      <div className="min-h-screen flex flex-col bg-background">
        <AppNavbar currentView="control" onViewChange={setView} />
        <ControlTable
          patients={patients}
          onSelectPatient={(id) => {
            setSelectedPatientId(id);
            setView('results');
          }}
          onBack={() => setView('results')}
        />
      </div>
    );
  }

  // Floating processing toast (Drive-style)
  const ProcessingToast = () => {
    const isError = uploadError && !pollingForUpload;
    return (
      <div className="fixed bottom-4 right-4 z-50 w-72 bg-card border border-border shadow-lg rounded-lg overflow-hidden">
        {toastMinimized ? (
          <button
            onClick={() => setToastMinimized(false)}
            className="flex items-center gap-2 px-3 py-2 text-xs w-full hover:bg-secondary transition-colors"
          >
            {isError
              ? <span className="h-3 w-3 rounded-full bg-destructive shrink-0" />
              : <Loader2 className="h-3 w-3 animate-spin text-primary shrink-0" />}
            <span className="text-foreground flex-1 text-left">
              {isError ? 'Error al procesar el archivo' : 'Procesando historia clínica…'}
            </span>
          </button>
        ) : (
          <>
            <div className="flex items-center justify-between px-3 py-2 border-b border-border bg-muted/30">
              <span className="text-xs font-medium text-foreground">
                {isError ? 'Error al procesar' : 'Procesando historia clínica'}
              </span>
              <button
                onClick={() => { setUploadError(false); setPollingForUpload(false); setToastMinimized(false); }}
                className="text-muted-foreground hover:text-foreground p-0.5 rounded text-lg leading-none"
                title="Cerrar"
              >
                ×
              </button>
            </div>
            {isError ? (
              <div className="px-3 py-3 flex items-start gap-2.5">
                <div className="mt-0.5 shrink-0 h-7 w-7 rounded bg-destructive/10 flex items-center justify-center">
                  <FileText className="h-3.5 w-3.5 text-destructive" />
                </div>
                <div className="flex flex-col gap-1.5">
                  <span className="text-xs text-destructive font-medium">No se pudo procesar el archivo</span>
                  <span className="text-xs text-muted-foreground/70">La IA encontró un error durante el análisis</span>
                  {permissions.canUpload && (
                    <button
                      onClick={() => { setUploadError(false); setPollingForUpload(false); setView('upload'); }}
                      className="mt-1 text-xs text-primary hover:underline text-left"
                    >
                      Reintentar con otro archivo
                    </button>
                  )}
                </div>
              </div>
            ) : (
              <div className="px-3 py-3 flex items-start gap-2.5">
                <div className="mt-0.5 shrink-0 h-7 w-7 rounded bg-primary/10 flex items-center justify-center">
                  <FileText className="h-3.5 w-3.5 text-primary" />
                </div>
                <div className="flex flex-col gap-1">
                  <div className="flex items-center gap-1.5">
                    <Loader2 className="h-3 w-3 animate-spin text-primary" />
                    <span className="text-xs text-foreground">Analizando con IA…</span>
                  </div>
                  <span className="text-xs text-muted-foreground/70">Esto puede tardar 1–2 minutos</span>
                  <button
                    onClick={() => setToastMinimized(true)}
                    className="mt-1 text-xs text-muted-foreground hover:text-foreground text-left flex items-center gap-1"
                  >
                    <ChevronDown className="h-3 w-3" /> Minimizar
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    );
  };

  // Loading state (solo en carga inicial, no durante polling)
  if (isLoadingPatients && !pollingForUpload) {
    return (
      <div className="h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  // Empty state
  if (patients.length === 0) {
    return (
      <>
        <div className="h-screen flex flex-col bg-background">
          <AppNavbar currentView="results" onViewChange={setView} />
          <div className="flex-1 flex flex-col items-center justify-center gap-4">
            <p className="text-muted-foreground">No hay historias clínicas cargadas aún</p>
            {permissions.canUpload && (
              <button
                onClick={() => setView('upload')}
                className="px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90"
              >
                Cargar primera historia clínica
              </button>
            )}
          </div>
        </div>
        {(pollingForUpload || uploadError) && <ProcessingToast />}
      </>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-background">
      <AppNavbar
        currentView="results"
        onViewChange={setView}
        extraActions={
          <span className="font-body text-xs text-muted-foreground">
            {patients.length} {patients.length === 1 ? 'historia' : 'historias'}
          </span>
        }
      />

      <div className="flex flex-1 overflow-hidden">
        <PatientSidebar
          patients={patients}
          selectedId={selectedPatientId}
          onSelect={setSelectedPatientId}
        />
        {selectedPatient && (
          <AnalysisPane
            patient={selectedPatient}
            onOpenChat={() => setChatOpen(true)}
            onTraceToSource={(page) => {
              setChatOpen(true);
              console.log(`Trace to source: page ${page}`);
            }}
          />
        )}
        {chatOpen && selectedPatient && (
          <ChatPanel
            patientId={selectedPatient.id}
            patientLabel={selectedPatient.label}
            allPatientIds={patients.map(p => p.id)}
            onClose={() => setChatOpen(false)}
          />
        )}
      </div>
      {(pollingForUpload || uploadError) && <ProcessingToast />}
    </div>
  );
};

export default AppPage;
