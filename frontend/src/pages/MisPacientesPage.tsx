import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { RoleGuard } from '@/components/RoleGuard';
import AppNavbar from '@/components/AppNavbar';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  AlertTriangle,
  Bell,
  BellOff,
  CheckCircle2,
  FileText,
  RefreshCw,
  Stethoscope,
  Clock,
  TrendingUp,
} from 'lucide-react';
import { toast } from 'sonner';
import { patientsApi, notificationsApi, type PatientSummary, type AppNotification } from '@/lib/api';

// ── Helpers ────────────────────────────────────────────────────────────────

const RIESGO_CONFIG = {
  alto:   { label: 'Alto',   className: 'bg-red-100 text-red-700 border-red-200' },
  medio:  { label: 'Medio',  className: 'bg-yellow-100 text-yellow-700 border-yellow-200' },
  bajo:   { label: 'Bajo',   className: 'bg-green-100 text-green-700 border-green-200' },
  pending:{ label: 'Pendiente', className: 'bg-gray-100 text-gray-600 border-gray-200' },
} as const;

type Riesgo = keyof typeof RIESGO_CONFIG;

function RiskBadge({ riesgo }: { riesgo: string }) {
  const cfg = RIESGO_CONFIG[(riesgo as Riesgo)] ?? RIESGO_CONFIG.pending;
  return (
    <Badge variant="outline" className={`text-xs font-semibold ${cfg.className}`}>
      {cfg.label}
    </Badge>
  );
}

const TIPO_CONFIG: Record<string, { label: string; icon: React.ReactNode; className: string }> = {
  alerta_auditoria: {
    label: 'Alerta Auditoría',
    icon: <AlertTriangle className="h-4 w-4 text-red-500" />,
    className: 'border-red-200 bg-red-50',
  },
  hallazgo_critico: {
    label: 'Hallazgo Crítico',
    icon: <AlertTriangle className="h-4 w-4 text-red-500" />,
    className: 'border-red-200 bg-red-50',
  },
  pendiente: {
    label: 'Pendiente',
    icon: <Clock className="h-4 w-4 text-yellow-500" />,
    className: 'border-yellow-200 bg-yellow-50',
  },
};

function tipoConfig(tipo: string) {
  return TIPO_CONFIG[tipo] ?? {
    label: tipo,
    icon: <Bell className="h-4 w-4 text-blue-500" />,
    className: 'border-blue-200 bg-blue-50',
  };
}

function formatRelative(dateStr: string) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `Hace ${mins} min`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `Hace ${hrs} h`;
  return `Hace ${Math.floor(hrs / 24)} días`;
}

// ── Componente principal ───────────────────────────────────────────────────

const MisPacientesPage = () => {
  const navigate = useNavigate();
  const [patients, setPatients] = useState<PatientSummary[]>([]);
  const [alerts, setAlerts] = useState<AppNotification[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingAlerts, setLoadingAlerts] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [patientsData, alertsData] = await Promise.all([
        patientsApi.list(),
        notificationsApi.list(false), // solo no leídas
      ]);
      setPatients(patientsData);
      setAlerts(alertsData);
    } catch {
      toast.error('No se pudieron cargar los datos');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleMarkRead = async (id: string) => {
    try {
      setLoadingAlerts(true);
      await notificationsApi.markRead(id);
      setAlerts(prev => prev.filter(a => a.id !== id));
    } catch {
      toast.error('No se pudo marcar como leída');
    } finally {
      setLoadingAlerts(false);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      setLoadingAlerts(true);
      await notificationsApi.markAllRead();
      setAlerts([]);
      toast.success('Todas las alertas marcadas como leídas');
    } catch {
      toast.error('No se pudo marcar todas como leídas');
    } finally {
      setLoadingAlerts(false);
    }
  };

  // Ordenar: alto → medio → bajo
  const ORDER: Record<string, number> = { alto: 0, medio: 1, bajo: 2 };
  const sortedPatients = [...patients].sort(
    (a, b) => (ORDER[a.riesgo] ?? 3) - (ORDER[b.riesgo] ?? 3)
  );

  return (
    <RoleGuard roles={['admin', 'equipo_medico']} redirectTo="/app">
      <div className="min-h-screen bg-background">
        <AppNavbar title="Mis Pacientes" />

        <div className="container mx-auto px-6 py-8 space-y-8 max-w-6xl">

          {/* ── Encabezado ── */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold tracking-tight">Mis Pacientes</h1>
              <p className="text-sm text-muted-foreground mt-1">
                Reportes resumidos y alertas activas de auditoría
              </p>
            </div>
            <Button variant="outline" size="sm" onClick={fetchData} disabled={loading}>
              <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              Actualizar
            </Button>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-24">
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary" />
            </div>
          ) : (
            <>
              {/* ── Alertas Activas ── */}
              <section>
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <Bell className="h-5 w-5 text-foreground" />
                    <h2 className="text-lg font-semibold">Alertas Activas</h2>
                    {alerts.length > 0 && (
                      <Badge className="bg-red-500 text-white text-xs px-2">
                        {alerts.length}
                      </Badge>
                    )}
                  </div>
                  {alerts.length > 0 && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleMarkAllRead}
                      disabled={loadingAlerts}
                      className="text-xs text-muted-foreground hover:text-foreground"
                    >
                      <CheckCircle2 className="h-3.5 w-3.5 mr-1.5" />
                      Marcar todas como leídas
                    </Button>
                  )}
                </div>

                {alerts.length === 0 ? (
                  <Card className="border-dashed">
                    <CardContent className="flex flex-col items-center justify-center py-10 text-center gap-3">
                      <BellOff className="h-8 w-8 text-muted-foreground/40" />
                      <p className="text-sm text-muted-foreground">Sin alertas activas. Todo al día.</p>
                    </CardContent>
                  </Card>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {alerts.map(alert => {
                      const cfg = tipoConfig(alert.tipo);
                      return (
                        <Card key={alert.id} className={`border ${cfg.className}`}>
                          <CardContent className="p-4 flex items-start gap-3">
                            <div className="mt-0.5 shrink-0">{cfg.icon}</div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center justify-between gap-2 mb-1">
                                <p className="text-sm font-medium truncate">{alert.titulo}</p>
                                <Badge variant="outline" className="text-[10px] shrink-0">
                                  {cfg.label}
                                </Badge>
                              </div>
                              <p className="text-xs text-muted-foreground leading-relaxed line-clamp-2">
                                {alert.mensaje}
                              </p>
                              <div className="flex items-center justify-between mt-2">
                                <span className="text-[10px] text-muted-foreground/60">
                                  {formatRelative(alert.created_at)}
                                </span>
                                <div className="flex gap-2">
                                  {alert.patient_id && (
                                    <Button
                                      variant="link"
                                      size="sm"
                                      className="h-auto p-0 text-xs text-primary"
                                      onClick={() => navigate(`/patients/${alert.patient_id}/report`)}
                                    >
                                      Ver paciente
                                    </Button>
                                  )}
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    className="h-auto p-0 text-xs text-muted-foreground hover:text-foreground"
                                    onClick={() => handleMarkRead(alert.id)}
                                    disabled={loadingAlerts}
                                  >
                                    Marcar leída
                                  </Button>
                                </div>
                              </div>
                            </div>
                          </CardContent>
                        </Card>
                      );
                    })}
                  </div>
                )}
              </section>

              {/* ── Reportes Resumidos de Pacientes ── */}
              <section>
                <div className="flex items-center gap-2 mb-4">
                  <Stethoscope className="h-5 w-5 text-foreground" />
                  <h2 className="text-lg font-semibold">Resumen de Pacientes</h2>
                  <span className="text-sm text-muted-foreground">
                    ({sortedPatients.length} {sortedPatients.length === 1 ? 'paciente' : 'pacientes'})
                  </span>
                </div>

                {sortedPatients.length === 0 ? (
                  <Card className="border-dashed">
                    <CardContent className="flex flex-col items-center justify-center py-12 gap-3">
                      <Stethoscope className="h-8 w-8 text-muted-foreground/40" />
                      <p className="text-sm text-muted-foreground">No hay pacientes hospitalizados.</p>
                    </CardContent>
                  </Card>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                    {sortedPatients.map(patient => (
                      <Card key={patient.id} className="hover:shadow-md transition-shadow">
                        <CardHeader className="pb-3">
                          <div className="flex items-start justify-between gap-2">
                            <div className="min-w-0">
                              <CardTitle className="text-sm font-semibold truncate">
                                {patient.label}
                              </CardTitle>
                              {patient.cama && (
                                <CardDescription className="text-xs mt-0.5">
                                  Cama {patient.cama}
                                </CardDescription>
                              )}
                            </div>
                            <RiskBadge riesgo={patient.riesgo} />
                          </div>
                        </CardHeader>

                        <CardContent className="space-y-3">
                          {/* Diagnóstico */}
                          <div>
                            <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide mb-0.5">
                              Diagnóstico
                            </p>
                            <p className="text-sm leading-snug line-clamp-2">
                              {patient.diagnostico_principal ?? '—'}
                              {patient.codigo_cie10 && (
                                <span className="ml-1 text-xs text-muted-foreground">
                                  ({patient.codigo_cie10})
                                </span>
                              )}
                            </p>
                          </div>

                          {/* Estancia */}
                          <div className="flex gap-4">
                            <div>
                              <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide mb-0.5">
                                Días hospitali.
                              </p>
                              <p className="text-sm font-semibold">
                                {patient.dias_hospitalizacion ?? '—'}
                              </p>
                            </div>
                            <div>
                              <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide mb-0.5">
                                Días esperados
                              </p>
                              <p className="text-sm font-semibold">
                                {patient.dias_esperados ?? '—'}
                              </p>
                            </div>
                          </div>

                          {/* Indicadores auditoría */}
                          <div className="flex items-center gap-3 pt-1 border-t border-border">
                            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                              <AlertTriangle className="h-3.5 w-3.5" />
                              <span>
                                {(patient as any).total_hallazgos ?? 0} hallazgo
                                {((patient as any).total_hallazgos ?? 0) !== 1 ? 's' : ''}
                              </span>
                            </div>
                            {(patient as any).exposicion_glosas > 0 && (
                              <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                                <TrendingUp className="h-3.5 w-3.5" />
                                <span>
                                  ${((patient as any).exposicion_glosas / 1000).toFixed(0)}K riesgo
                                </span>
                              </div>
                            )}
                          </div>

                          {/* Acción principal */}
                          <Button
                            size="sm"
                            variant="outline"
                            className="w-full text-xs"
                            onClick={() => navigate(`/patients/${patient.id}/report`)}
                          >
                            <FileText className="h-3.5 w-3.5 mr-1.5" />
                            Ver Reporte Completo
                          </Button>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                )}
              </section>
            </>
          )}
        </div>
      </div>
    </RoleGuard>
  );
};

export default MisPacientesPage;
