import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { usePermissions } from '@/components/RoleGuard';
import { useNavigate } from 'react-router-dom';
import UploadScreen from '@/components/UploadScreen';
import PatientSidebar from '@/components/PatientSidebar';
import AnalysisPane from '@/components/AnalysisPane';
import ChatPanel from '@/components/ChatPanel';
import ControlTable from '@/components/ControlTable';
import { mockPatients } from '@/data/mockPatients';
import { LogOut, User } from 'lucide-react';

type View = 'upload' | 'results' | 'control';

const AppPage = () => {
  const { user, role, signOut } = useAuth();
  const permissions = usePermissions();
  const navigate = useNavigate();
  const [view, setView] = useState<View>(permissions.canUpload ? 'upload' : 'results');
  const [selectedPatientId, setSelectedPatientId] = useState(mockPatients[0].id);
  const [chatOpen, setChatOpen] = useState(false);

  const selectedPatient = mockPatients.find(p => p.id === selectedPatientId) || mockPatients[0];

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
    return (
      <ControlTable
        patients={mockPatients}
        onSelectPatient={(id) => {
          setSelectedPatientId(id);
          setView('results');
        }}
        onBack={() => setView('results')}
      />
    );
  }

  return (
    <div className="h-screen flex flex-col bg-background">
      <header className="h-12 border-b border-border bg-card flex items-center px-4 justify-between shrink-0">
        <div className="flex items-center gap-3">
          <h1 className="font-display text-sm font-bold text-foreground">Audi Med IA</h1>
          <span className="text-xs font-body text-muted-foreground">·</span>
          <span className="text-xs font-body text-muted-foreground">3 historias procesadas</span>
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
          {permissions.canViewDashboard && (
            <button
              onClick={() => setView('control')}
              className="font-body text-xs border border-border rounded px-3 py-1.5 hover:bg-secondary transition-colors text-foreground"
            >
              Cuadro de control
            </button>
          )}
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
          patients={mockPatients}
          selectedId={selectedPatientId}
          onSelect={setSelectedPatientId}
        />
        <AnalysisPane
          patient={selectedPatient}
          onOpenChat={() => setChatOpen(true)}
          onTraceToSource={(page) => {
            setChatOpen(true);
            console.log(`Trace to source: page ${page}`);
          }}
        />
        {chatOpen && (
          <ChatPanel
            patientLabel={selectedPatient.label}
            onClose={() => setChatOpen(false)}
          />
        )}
      </div>
    </div>
  );
};

export default AppPage;
