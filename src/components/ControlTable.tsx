import { useState } from 'react';
import { PatientCase } from '@/types/audit';
import RiskBadge from '@/components/RiskBadge';
import { ArrowUpDown, Download, Check } from 'lucide-react';

interface ControlTableProps {
  patients: PatientCase[];
  onSelectPatient: (id: string) => void;
  onBack: () => void;
}

type SortField = 'cama' | 'dias' | 'riesgo';
type RiskFilter = 'todos' | 'ALTO' | 'MEDIO' | 'BAJO';

const riskOrder = { ALTO: 3, MEDIO: 2, BAJO: 1 };

const ControlTable = ({ patients, onSelectPatient, onBack }: ControlTableProps) => {
  const [sortField, setSortField] = useState<SortField>('riesgo');
  const [sortAsc, setSortAsc] = useState(false);
  const [filter, setFilter] = useState<RiskFilter>('todos');
  const [resolved, setResolved] = useState<Set<string>>(new Set());

  const toggleSort = (field: SortField) => {
    if (sortField === field) setSortAsc(!sortAsc);
    else { setSortField(field); setSortAsc(false); }
  };

  const filtered = patients.filter(p => filter === 'todos' || p.riesgo === filter);
  const sorted = [...filtered].sort((a, b) => {
    let cmp = 0;
    if (sortField === 'cama') cmp = a.cama.localeCompare(b.cama);
    else if (sortField === 'dias') cmp = a.diasHospitalizacion - b.diasHospitalizacion;
    else cmp = riskOrder[a.riesgo] - riskOrder[b.riesgo];
    return sortAsc ? cmp : -cmp;
  });

  const markResolved = (id: string) => setResolved(prev => new Set(prev).add(id));

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="font-display text-xl font-bold text-foreground">Cuadro de Control</h1>
            <p className="font-body text-sm text-muted-foreground">{patients.length} historias procesadas en esta sesión</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={onBack}
              className="font-body text-sm border border-border rounded-md px-4 py-2 hover:bg-secondary transition-colors text-foreground"
            >
              Volver a reportes
            </button>
            <button className="font-body text-sm border border-border rounded-md px-4 py-2 hover:bg-secondary transition-colors text-foreground flex items-center gap-1.5">
              <Download className="h-3.5 w-3.5" />
              Exportar Excel
            </button>
            <button className="font-body text-sm border border-border rounded-md px-4 py-2 hover:bg-secondary transition-colors text-foreground flex items-center gap-1.5">
              <Download className="h-3.5 w-3.5" />
              Exportar PDF
            </button>
          </div>
        </div>

        {/* Filters */}
        <div className="flex gap-2 mb-4">
          {(['todos', 'ALTO', 'MEDIO', 'BAJO'] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`font-body text-xs px-3 py-1.5 rounded-md border transition-colors ${
                filter === f ? 'bg-primary text-primary-foreground border-primary' : 'border-border text-muted-foreground hover:text-foreground'
              }`}
            >
              {f === 'todos' ? 'Todos' : `Riesgo ${f}`}
            </button>
          ))}
        </div>

        {/* Table */}
        <div className="border border-border rounded-md overflow-hidden bg-card">
          <table className="w-full">
            <thead>
              <tr className="bg-secondary">
                <th className="text-left px-4 py-3">
                  <button onClick={() => toggleSort('cama')} className="data-label flex items-center gap-1">
                    N° Historia / Cama <ArrowUpDown className="h-3 w-3" />
                  </button>
                </th>
                <th className="text-left px-4 py-3 data-label">Diagnóstico (CIE-10)</th>
                <th className="text-left px-4 py-3">
                  <button onClick={() => toggleSort('dias')} className="data-label flex items-center gap-1">
                    Días hosp. <ArrowUpDown className="h-3 w-3" />
                  </button>
                </th>
                <th className="text-left px-4 py-3 data-label">Días esperados</th>
                <th className="text-left px-4 py-3 data-label">Estudios pendientes</th>
                <th className="text-left px-4 py-3">
                  <button onClick={() => toggleSort('riesgo')} className="data-label flex items-center gap-1">
                    Riesgo glosa <ArrowUpDown className="h-3 w-3" />
                  </button>
                </th>
                <th className="text-left px-4 py-3 data-label">Acción</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((p) => (
                <tr key={p.id} className="border-t border-border hover:bg-secondary/50 transition-colors">
                  <td className="px-4 py-3">
                    <button onClick={() => onSelectPatient(p.id)} className="font-body text-sm font-medium text-foreground hover:underline">
                      {p.cama}
                    </button>
                    <p className="font-body text-xs text-muted-foreground">{p.label}</p>
                  </td>
                  <td className="px-4 py-3 font-body text-sm text-foreground">{p.codigoCIE10} — {p.diagnosticoPrincipal}</td>
                  <td className="px-4 py-3 font-body text-sm text-foreground">{p.diasHospitalizacion} días</td>
                  <td className="px-4 py-3 font-body text-sm text-muted-foreground">{p.diasEsperados} días</td>
                  <td className="px-4 py-3">
                    {p.estudiosPendientes.length > 0 ? (
                      <ul className="font-body text-xs text-foreground space-y-0.5">
                        {p.estudiosPendientes.map((e, i) => (
                          <li key={i}>• {e}</li>
                        ))}
                      </ul>
                    ) : (
                      <span className="font-body text-xs text-muted-foreground">Sin pendientes</span>
                    )}
                  </td>
                  <td className="px-4 py-3"><RiskBadge level={p.riesgo} /></td>
                  <td className="px-4 py-3">
                    {resolved.has(p.id) ? (
                      <span className="font-body text-xs text-success flex items-center gap-1">
                        <Check className="h-3 w-3" /> Resuelto
                      </span>
                    ) : (
                      <button
                        onClick={() => markResolved(p.id)}
                        className="font-body text-xs text-muted-foreground hover:text-foreground border border-border rounded px-2 py-1"
                      >
                        Marcar resuelto
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default ControlTable;
