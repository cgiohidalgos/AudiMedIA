import { PatientCase } from '@/types/audit';
import RiskBadge from '@/components/RiskBadge';

interface PatientSidebarProps {
  patients: PatientCase[];
  selectedId: string;
  onSelect: (id: string) => void;
}

const PatientSidebar = ({ patients, selectedId, onSelect }: PatientSidebarProps) => {
  return (
    <aside className="w-64 border-r border-border bg-card flex flex-col h-full shrink-0">
      <div className="p-4 border-b border-border">
        <h2 className="panel-header">Pacientes</h2>
      </div>
      <nav className="flex-1 overflow-y-auto">
        {patients.map((p) => (
          <button
            key={p.id}
            onClick={() => onSelect(p.id)}
            className={`w-full text-left px-4 py-3 border-b border-border transition-colors ${
              selectedId === p.id ? 'bg-accent' : 'hover:bg-secondary'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="font-display text-sm font-semibold text-foreground">{p.cama}</span>
              <RiskBadge level={p.riesgo} />
            </div>
            <p className="font-body text-xs text-muted-foreground truncate">{p.codigoCIE10} — {p.diagnosticoPrincipal}</p>
            <p className="font-body text-xs text-muted-foreground mt-0.5">
              {p.diasHospitalizacion} días / esperado {p.diasEsperados}
            </p>
          </button>
        ))}
      </nav>
    </aside>
  );
};

export default PatientSidebar;
