import { useState } from 'react';
import UploadScreen from '@/components/UploadScreen';
import PatientSidebar from '@/components/PatientSidebar';
import AnalysisPane from '@/components/AnalysisPane';
import ChatPanel from '@/components/ChatPanel';
import ControlTable from '@/components/ControlTable';
import { mockPatients } from '@/data/mockPatients';

type View = 'upload' | 'results' | 'control';

const Index = () => {
  const [view, setView] = useState<View>('upload');
  const [selectedPatientId, setSelectedPatientId] = useState(mockPatients[0].id);
  const [chatOpen, setChatOpen] = useState(false);

  const selectedPatient = mockPatients.find(p => p.id === selectedPatientId) || mockPatients[0];

  if (view === 'upload') {
    return <UploadScreen onStartAnalysis={() => setView('results')} />;
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
      {/* Top bar */}
      <header className="h-12 border-b border-border bg-card flex items-center px-4 justify-between shrink-0">
        <div className="flex items-center gap-3">
          <h1 className="font-display text-sm font-bold text-foreground">Audi Med IA</h1>
          <span className="text-xs font-body text-muted-foreground">·</span>
          <span className="text-xs font-body text-muted-foreground">3 historias procesadas</span>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setView('control')}
            className="font-body text-xs border border-border rounded px-3 py-1.5 hover:bg-secondary transition-colors text-foreground"
          >
            Cuadro de control
          </button>
          <button
            onClick={() => setView('upload')}
            className="font-body text-xs border border-border rounded px-3 py-1.5 hover:bg-secondary transition-colors text-foreground"
          >
            Nueva carga
          </button>
        </div>
      </header>

      {/* Three-column layout */}
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
            // In production, this would scroll the PDF viewer to the page
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

export default Index;
