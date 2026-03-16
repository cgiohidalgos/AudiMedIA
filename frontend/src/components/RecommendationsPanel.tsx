import { useState, useEffect, useCallback } from 'react';
import { recommendationsApi, Recommendation, RecommendationSummary } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';
import {
  AlertTriangle, CheckCircle2, RefreshCw, ChevronDown, ChevronRight,
  Loader2, ClipboardList, BookOpen, Wrench, Activity, Building2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';

interface Props {
  patientId: string;
}

// ── Configuración visual ──────────────────────────────────────────────────────

const TIPO_CONFIG: Record<string, { label: string; Icon: React.ElementType; color: string }> = {
  documentacion: { label: 'Documentación',  Icon: BookOpen,      color: 'text-blue-600' },
  estancia:      { label: 'Estancia',        Icon: Activity,      color: 'text-amber-600' },
  estudios:      { label: 'Estudios',        Icon: ClipboardList, color: 'text-purple-600' },
  complicacion:  { label: 'Complicación',    Icon: AlertTriangle, color: 'text-red-600' },
  institucional: { label: 'Institucional',   Icon: Building2,     color: 'text-gray-600' },
};

const PRIORIDAD_BADGE: Record<string, string> = {
  alta:  'bg-red-100 text-red-700 border-red-200',
  media: 'bg-amber-100 text-amber-700 border-amber-200',
  baja:  'bg-green-100 text-green-700 border-green-200',
};

const CATEGORIA_BADGE: Record<string, string> = {
  critica:      'bg-red-50 text-red-600 border-red-200',
  alerta:       'bg-orange-50 text-orange-600 border-orange-200',
  mejora:       'bg-blue-50 text-blue-600 border-blue-200',
  optimizacion: 'bg-teal-50 text-teal-600 border-teal-200',
};

// ── Sub-componente: tarjeta de recomendación ──────────────────────────────────

interface CardProps {
  rec: Recommendation;
  onUpdate: (id: string, payload: { estado?: string; notas?: string }) => void;
}

const RecCard = ({ rec, onUpdate }: CardProps) => {
  const [expanded, setExpanded] = useState(false);
  const [showNotes, setShowNotes] = useState(false);
  const [notes, setNotes] = useState(rec.notas_resolucion ?? '');
  const [saving, setSaving] = useState(false);
  const { toast } = useToast();

  const tipoConf = TIPO_CONFIG[rec.tipo] ?? TIPO_CONFIG['documentacion'];
  const { Icon } = tipoConf;

  const isDone = rec.estado !== 'pendiente';

  const handleEstado = async (estado: string) => {
    setSaving(true);
    try {
      await onUpdate(rec.id, { estado });
    } finally {
      setSaving(false);
    }
  };

  const handleSaveNotes = async () => {
    setSaving(true);
    try {
      await onUpdate(rec.id, { notas: notes });
      setShowNotes(false);
      toast({ title: 'Notas guardadas' });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className={`border rounded-lg mb-2 transition-opacity ${isDone ? 'opacity-60' : ''}`}>
      {/* Header de la tarjeta */}
      <div
        className="flex items-start gap-3 p-3 cursor-pointer hover:bg-secondary/30 rounded-t-lg"
        onClick={() => setExpanded(prev => !prev)}
      >
        <Icon className={`h-4 w-4 mt-0.5 shrink-0 ${tipoConf.color}`} />
        <div className="flex-1 min-w-0">
          <p className={`text-sm font-medium leading-snug ${isDone ? 'line-through text-muted-foreground' : 'text-foreground'}`}>
            {rec.mensaje}
          </p>
          <div className="flex flex-wrap items-center gap-1.5 mt-1.5">
            <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border ${PRIORIDAD_BADGE[rec.prioridad]}`}>
              {rec.prioridad.toUpperCase()}
            </span>
            <span className={`text-[10px] px-1.5 py-0.5 rounded border ${CATEGORIA_BADGE[rec.categoria] ?? ''}`}>
              {rec.categoria}
            </span>
            <span className="text-[10px] text-muted-foreground">{tipoConf.label}</span>
            {rec.estado === 'implementada' && (
              <span className="text-[10px] text-green-600 flex items-center gap-0.5">
                <CheckCircle2 className="h-3 w-3" /> Implementada
              </span>
            )}
            {rec.estado === 'descartada' && (
              <span className="text-[10px] text-muted-foreground">Descartada</span>
            )}
          </div>
        </div>
        <span className="text-muted-foreground shrink-0 mt-0.5">
          {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </span>
      </div>

      {/* Cuerpo expandido */}
      {expanded && (
        <div className="border-t px-3 pb-3 pt-2 space-y-2">
          {rec.detalle && (
            <p className="text-xs text-muted-foreground">{rec.detalle}</p>
          )}
          {rec.notas_resolucion && (
            <p className="text-xs italic text-muted-foreground bg-secondary/20 px-2 py-1 rounded">
              Nota: {rec.notas_resolucion}
            </p>
          )}

          <div className="flex flex-wrap gap-2 pt-1">
            {rec.estado === 'pendiente' && (
              <>
                <Button
                  size="sm"
                  variant="outline"
                  className="h-7 text-xs text-green-700 border-green-300 hover:bg-green-50"
                  disabled={saving}
                  onClick={(e) => { e.stopPropagation(); handleEstado('implementada'); }}
                >
                  {saving ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <CheckCircle2 className="h-3 w-3 mr-1" />}
                  Marcar implementada
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  className="h-7 text-xs text-muted-foreground"
                  disabled={saving}
                  onClick={(e) => { e.stopPropagation(); handleEstado('descartada'); }}
                >
                  Descartar
                </Button>
              </>
            )}
            {rec.estado !== 'pendiente' && (
              <Button
                size="sm"
                variant="ghost"
                className="h-7 text-xs"
                disabled={saving}
                onClick={(e) => { e.stopPropagation(); handleEstado('pendiente'); }}
              >
                Reabrir
              </Button>
            )}
            <Button
              size="sm"
              variant="ghost"
              className="h-7 text-xs"
              onClick={(e) => { e.stopPropagation(); setShowNotes(true); }}
            >
              <Wrench className="h-3 w-3 mr-1" />
              Agregar nota
            </Button>
          </div>
        </div>
      )}

      {/* Modal de notas */}
      <Dialog open={showNotes} onOpenChange={setShowNotes}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle className="text-sm">Notas de resolución</DialogTitle>
          </DialogHeader>
          <Textarea
            className="text-sm"
            rows={4}
            placeholder="Describe las acciones tomadas o el motivo de descarte..."
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
          <DialogFooter>
            <Button size="sm" variant="outline" onClick={() => setShowNotes(false)}>Cancelar</Button>
            <Button size="sm" disabled={saving} onClick={handleSaveNotes}>
              {saving ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : null}
              Guardar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

// ── Componente principal ──────────────────────────────────────────────────────

const RecommendationsPanel = ({ patientId }: Props) => {
  const [recs, setRecs] = useState<Recommendation[]>([]);
  const [summary, setSummary] = useState<RecommendationSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [filterEstado, setFilterEstado] = useState<string>('pendiente');
  const { toast } = useToast();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [data, sumData] = await Promise.all([
        recommendationsApi.list(patientId, { estado: filterEstado === 'todas' ? undefined : filterEstado }),
        recommendationsApi.summary(patientId),
      ]);
      setRecs(data);
      setSummary(sumData);
    } catch {
      // puede estar vacío si aún no se generaron
      setRecs([]);
    } finally {
      setLoading(false);
    }
  }, [patientId, filterEstado]);

  useEffect(() => { load(); }, [load]);

  const handleGenerate = async (overwrite = false) => {
    setGenerating(true);
    try {
      const res = await recommendationsApi.generate(patientId, overwrite);
      toast({ title: res.message });
      await load();
    } catch (e: any) {
      toast({ title: 'Error al generar', description: e.message, variant: 'destructive' });
    } finally {
      setGenerating(false);
    }
  };

  const handleUpdate = async (id: string, payload: { estado?: string; notas?: string }) => {
    await recommendationsApi.update(id, {
      estado: payload.estado,
      notas_resolucion: payload.notas,
    });
    await load();
  };

  // Agrupar por prioridad
  const grouped = recs.reduce<Record<string, Recommendation[]>>((acc, r) => {
    if (!acc[r.prioridad]) acc[r.prioridad] = [];
    acc[r.prioridad].push(r);
    return acc;
  }, {});

  return (
    <div className="mb-4 border border-border rounded-md bg-card">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border">
        <div className="flex items-center gap-2">
          <ClipboardList className="h-4 w-4 text-primary" />
          <h3 className="font-display text-sm font-semibold text-foreground">
            Recomendaciones estructuradas
          </h3>
          {summary && summary.total > 0 && (
            <span className="text-xs bg-primary/10 text-primary px-1.5 py-0.5 rounded-full font-medium">
              {summary.por_estado?.pendiente ?? 0} pendientes
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="ghost"
            className="h-7 text-xs"
            disabled={loading}
            onClick={() => load()}
          >
            <RefreshCw className={`h-3 w-3 ${loading ? 'animate-spin' : ''}`} />
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="h-7 text-xs"
            disabled={generating}
            onClick={() => handleGenerate(false)}
          >
            {generating ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : null}
            {recs.length === 0 ? 'Generar' : '+ Nuevas'}
          </Button>
          {recs.length > 0 && (
            <Button
              size="sm"
              variant="ghost"
              className="h-7 text-xs text-muted-foreground"
              disabled={generating}
              onClick={() => handleGenerate(true)}
              title="Regenerar todas desde cero"
            >
              Regenerar
            </Button>
          )}
        </div>
      </div>

      {/* Estadísticas rápidas */}
      {summary && summary.total > 0 && (
        <div className="grid grid-cols-3 gap-0 border-b border-border text-center text-xs">
          {[
            { label: 'Pendientes', val: summary.por_estado.pendiente ?? 0, cls: 'text-amber-600' },
            { label: 'Implementadas', val: summary.por_estado.implementada ?? 0, cls: 'text-green-600' },
            { label: 'Descartadas', val: summary.por_estado.descartada ?? 0, cls: 'text-muted-foreground' },
          ].map(({ label, val, cls }) => (
            <div key={label} className="py-2 border-r last:border-r-0 border-border">
              <span className={`font-bold text-base ${cls}`}>{val}</span>
              <p className="text-muted-foreground">{label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Filtro */}
      {summary && summary.total > 0 && (
        <div className="flex gap-1 px-4 pt-3">
          {(['pendiente', 'implementada', 'descartada', 'todas'] as const).map(f => (
            <button
              key={f}
              onClick={() => setFilterEstado(f)}
              className={`text-xs px-2 py-1 rounded-full border transition-colors ${
                filterEstado === f
                  ? 'bg-primary text-primary-foreground border-primary'
                  : 'border-border text-muted-foreground hover:bg-secondary'
              }`}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
      )}

      {/* Lista */}
      <div className="p-4">
        {loading && (
          <div className="flex items-center justify-center py-6 text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin mr-2" />
            <span className="text-xs">Cargando...</span>
          </div>
        )}

        {!loading && recs.length === 0 && (
          <div className="text-center py-6 text-muted-foreground">
            <ClipboardList className="h-8 w-8 mx-auto mb-2 opacity-30" />
            <p className="text-xs">
              {summary && summary.total > 0
                ? 'No hay recomendaciones con este filtro.'
                : 'Haz clic en "Generar" para crear recomendaciones a partir de los hallazgos.'}
            </p>
          </div>
        )}

        {!loading && (['alta', 'media', 'baja'] as const).map(prioridad => {
          const group = grouped[prioridad];
          if (!group?.length) return null;
          return (
            <div key={prioridad} className="mb-3">
              <p className={`text-[11px] font-semibold uppercase tracking-wide mb-1.5 ${
                prioridad === 'alta' ? 'text-red-500' :
                prioridad === 'media' ? 'text-amber-500' : 'text-green-600'
              }`}>
                Prioridad {prioridad} ({group.length})
              </p>
              {group.map(r => (
                <RecCard key={r.id} rec={r} onUpdate={handleUpdate} />
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default RecommendationsPanel;
