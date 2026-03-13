import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { usePermissions } from '@/components/RoleGuard';
import { useNavigate } from 'react-router-dom';
import UploadScreen from '@/components/UploadScreen';
import PatientSidebar from '@/components/PatientSidebar';
import AnalysisPane from '@/components/AnalysisPane';
import ChatPanel from '@/components/ChatPanel';
import ControlTable from '@/components/ControlTable';
import { mockPatients } from '@/data/mockPatients';
import { patientsApi, type AuditSummary } from '@/lib/api';
import { LogOut, User, Loader2 } from 'lucide-react';
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
  const { user, role, signOut } = useAuth();
  const permissions = usePermissions();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [view, setView] = useState<View>(permissions.canUpload ? 'upload' : 'results');
  const [patients, setPatients] = useState<PatientForUI[]>([]);
  const [isLoadingPatients, setIsLoadingPatients] = useState(false);
  const [selectedPatientId, setSelectedPatientId] = useState<string>('');
  const [chatOpen, setChatOpen] = useState(false);

  // Fetch patients from API
  useEffect(() => {
    const fetchPatients = async () => {
      try {
        setIsLoadingPatients(true);
        const summaries = await patientsApi.list();
        
        // Si no hay pacientes reales, usar mock data para demo
        if (summaries.length === 0) {
          setPatients(mockPatients as any);
          setSelectedPatientId(mockPatients[0].id);
          return;
        }
        
        // Fetch audit details for each patient
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
        toast({
          title: 'Error al cargar pacientes',
          description: 'Usando datos de demostración',
          variant: 'destructive',
        });
        // Fallback to mock data
        setPatients(mockPatients as any);
        setSelectedPatientId(mockPatients[0].id);
      } finally {
        setIsLoadingPatients(false);
      }
    };

    if (view === 'results' || view === 'control') {
      fetchPatients();
    }
  }, [view, toast]);

  const selectedPatient = patients.find(p => p.id === selectedPatientId) || patients[0];

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

  const roleLabel =
    role === 'admin' ? 'Administrador' :
    role === 'auditor' ? 'Auditor' :
    role === 'coordinador' ? 'Coordinador' :
    role === 'equipo_medico' ? 'Equipo Médico' : 'Usuario';

  if (view === 'upload' && permissions.canUpload) {
    return (
      <div className="min-h-screen bg-background">
        {/* User bar */}
        <div className="border-b border-border bg-card px-4 h-10 flex items-center justify-between">
          <span className="font-display text-xs font-semibold text-foreground">Audi Med IA</span>
          <div className="flex items-center gap-3">
            <span className="font-body text-xs text-muted-foreground flex items-center gap-1">
              <User className="h-3 w-3" />
              {user?.email} · {roleLabel}
            </span>
            
            {/* Botón Dashboard - visible para admin y coordinador */}
            {permissions.canViewDashboard && (
              <button
                onClick={() => navigate('/dashboard')}
                className="font-body text-xs border border-border rounded px-3 py-1.5 hover:bg-secondary transition-colors text-foreground"
              >
                Dashboard Financiero
              </button>
            )}
            
            {/* Botón Cuadro de Control */}
            <button
              onClick={() => navigate('/control-board')}
              className="font-body text-xs border border-border rounded px-3 py-1.5 hover:bg-secondary transition-colors text-foreground"
            >
              Cuadro de Control
            </button>
            
            {/* Botón para ir a ver resultados */}
            <button
              onClick={() => setView('results')}
              className="font-body text-xs border border-border rounded px-3 py-1.5 hover:bg-secondary transition-colors text-foreground"
            >
              Ver resultados
            </button>
            
            <button onClick={signOut} className="text-muted-foreground hover:text-foreground" title="Cerrar sesión">
              <LogOut className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
        <UploadScreen onStartAnalysis={() => setView('results')} />
      </div>
    );
  }

  if (view === 'control') {
    if (isLoadingPatients) {
      return (
        <div className="min-h-screen flex items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      );
    }
    return (
      <ControlTable
        patients={patients}
        onSelectPatient={(id) => {
          setSelectedPatientId(id);
          setView('results');
        }}
        onBack={() => setView('results')}
      />
    );
  }

  // Loading state
  if (isLoadingPatients) {
    return (
      <div className="h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  // Empty state
  if (patients.length === 0) {
    return (
      <div className="h-screen flex flex-col items-center justify-center bg-background">
        <p className="text-muted-foreground mb-4">No hay pacientes cargados aún</p>
        {permissions.canUpload && (
          <button
            onClick={() => setView('upload')}
            className="px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90"
          >
            Cargar primera historia clínica
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-background">
      <header className="h-12 border-b border-border bg-card flex items-center px-4 justify-between shrink-0">
        <div className="flex items-center gap-3">
          <h1 className="font-display text-sm font-bold text-foreground">Audi Med IA</h1>
          <span className="text-xs font-body text-muted-foreground">·</span>
          <span className="text-xs font-body text-muted-foreground">{patients.length} historias procesadas</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="font-body text-xs text-muted-foreground flex items-center gap-1">
            <User className="h-3 w-3" />
            {roleLabel}
          </span>
          {permissions.canViewDashboard && (
            <button
              onClick={() => navigate('/dashboard')}
              className="font-body text-xs border border-border rounded px-3 py-1.5 hover:bg-secondary transition-colors text-foreground"
            >
              Dashboard Financiero
            </button>
          )}
          <button
            onClick={() => navigate('/control-board')}
            className="font-body text-xs border border-border rounded px-3 py-1.5 hover:bg-secondary transition-colors text-foreground"
          >
            Cuadro de Control
          </button>
          {permissions.canUpload && (
            <button
              onClick={() => setView('upload')}
              className="font-body text-xs border border-border rounded px-3 py-1.5 hover:bg-secondary transition-colors text-foreground"
            >
              Nueva carga
            </button>
          )}
          <button onClick={signOut} className="text-muted-foreground hover:text-foreground" title="Cerrar sesión">
            <LogOut className="h-3.5 w-3.5" />
          </button>
        </div>
      </header>

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
    </div>
  );
};

export default AppPage;
