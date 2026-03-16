import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { RoleGuard } from '@/components/RoleGuard';
import AppNavbar from '@/components/AppNavbar';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { TrendingUp, TrendingDown, DollarSign, FileText, Clock, AlertTriangle, CheckCircle2, Download, LogOut } from 'lucide-react';
import { toast } from 'sonner';
import { getToken } from '@/lib/api';

// Tipos
interface DashboardFinanciero {
  periodo_tipo: string;
  fecha_inicio: string;
  fecha_fin: string;
  glosas_evitadas_mes_cop: number;
  glosas_evitadas_anio_cop: number;
  estancias_prolongadas_dias: number;
  ahorro_estancia_mes_cop: number;
  historias_auditadas_periodo: number;
  tasa_riesgo_alto_porcentaje: number;
  pendientes_resueltos_porcentaje: number;
  tiempo_promedio_auditoria_min: number;
  ahorro_por_estancia: number;
  ahorro_por_procedimientos: number;
  ahorro_por_medicamentos: number;
  ahorro_por_evoluciones: number;
  roi_periodo: number;
  proyeccion_ahorro_anual: number;
}

interface MetricaTemporal {
  fecha: string;
  valor: number;
  etiqueta: string;
}

interface DashboardGraficos {
  glosas_tiempo: MetricaTemporal[];
  ahorro_acumulado: MetricaTemporal[];
  hallazgos_por_modulo: Record<string, number>;
  ahorro_por_servicio: Record<string, number>;
}

// Colores del tema
const COLORS = {
  primary: '#2563eb',
  success: '#10b981',
  warning: '#f59e0b',
  danger: '#ef4444',
  purple: '#8b5cf6',
  cyan: '#06b6d4',
};

const CHART_COLORS = ['#2563eb', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'];

const DashboardPage = () => {
  const { user, signOut } = useAuth();
  const [periodo, setPeriodo] = useState<'dia' | 'semana' | 'mes' | 'anio'>('mes');
  const [financiero, setFinanciero] = useState<DashboardFinanciero | null>(null);
  const [graficos, setGraficos] = useState<DashboardGraficos | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, [periodo]);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const token = getToken();
      
      if (!token) {
        toast.error('No está autenticado');
        return;
      }
      
      // Fetch financiero
      const finRes = await fetch(`/api/v1/dashboard/financiero?periodo=${periodo}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (!finRes.ok) {
        throw new Error(`Error ${finRes.status}: ${finRes.statusText}`);
      }
      
      const finData = await finRes.json();
      setFinanciero(finData);
      
      // Fetch gráficos
      const dias = periodo === 'dia' ? 7 : periodo === 'semana' ? 14 : periodo === 'mes' ? 30 : 90;
      const grafRes = await fetch(`/api/v1/dashboard/graficos?dias=${dias}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (!grafRes.ok) {
        throw new Error(`Error ${grafRes.status}: ${grafRes.statusText}`);
      }
      
      const grafData = await grafRes.json();
      setGraficos(grafData);
    } catch (error) {
      console.error('Error fetching dashboard:', error);
      toast.error('Error al cargar el dashboard');
    } finally {
      setLoading(false);
    }
  };

  const formatCOP = (value: number) => {
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatPercent = (value: number) => `${value.toFixed(1)}%`;

  const handleExport = async (formato: 'excel' | 'pdf') => {
    try {
      const token = getToken();
      if (!token) {
        toast.error('No está autenticado');
        return;
      }

      const payload = {
        formato,
        periodo_inicio: financiero.fecha_inicio,
        periodo_fin: financiero.fecha_fin,
        incluir_graficos: true,
        incluir_detalle_pacientes: false,
      };

      const response = await fetch('/api/v1/dashboard/export', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error('Error al exportar');
      }

      // Descargar el archivo
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      
      // Obtener nombre del archivo de headers o generar uno
      const contentDisposition = response.headers.get('Content-Disposition');
      const filename = contentDisposition
        ? contentDisposition.split('filename=')[1].replace(/"/g, '')
        : `dashboard_${formato}.${formato === 'excel' ? 'csv' : 'json'}`;
      
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      toast.success(`Reporte ${formato.toUpperCase()} descargado`);
    } catch (error) {
      console.error('Error exporting:', error);
      toast.error(`Error al exportar ${formato.toUpperCase()}`);
    }
  };

  const handleExecutiveReport = async () => {
    try {
      const token = getToken();
      if (!token) {
        toast.error('No está autenticado');
        return;
      }

      toast.info('Generando reporte ejecutivo…');

      const response = await fetch(`/api/v1/dashboard/executive-report?periodo=${periodo}`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });

      if (!response.ok) {
        throw new Error(`Error ${response.status}`);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const cd = response.headers.get('Content-Disposition');
      a.download = cd ? cd.split('filename=')[1].replace(/"/g, '') : 'reporte_ejecutivo.pdf';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      toast.success('Reporte ejecutivo descargado');
    } catch (error) {
      console.error(error);
      toast.error('Error al generar el reporte ejecutivo');
    }
  };

  if (loading || !financiero || !graficos) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
          <p className="mt-4 text-muted-foreground">Cargando dashboard...</p>
        </div>
      </div>
    );
  }

  // Preparar datos para gráficos
  const desgloseAhorro = [
    { name: 'Estancia', value: financiero.ahorro_por_estancia },
    { name: 'Procedimientos', value: financiero.ahorro_por_procedimientos },
    { name: 'Medicamentos', value: financiero.ahorro_por_medicamentos },
    { name: 'Evoluciones', value: financiero.ahorro_por_evoluciones },
  ];

  const modulosData = graficos.hallazgos_por_modulo 
    ? Object.entries(graficos.hallazgos_por_modulo).map(([name, value]) => ({
        name: name.charAt(0).toUpperCase() + name.slice(1),
        value
      }))
    : [];

  return (
    <RoleGuard roles={['admin', 'coordinador']}>
      <div className="min-h-screen bg-background">
        <AppNavbar
          title="Dashboard Financiero"
          extraActions={
            <Select value={periodo} onValueChange={(v) => setPeriodo(v as any)}>
              <SelectTrigger className="w-[160px] h-8 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="dia">Último día</SelectItem>
                <SelectItem value="semana">Última semana</SelectItem>
                <SelectItem value="mes">Último mes</SelectItem>
                <SelectItem value="anio">Último año</SelectItem>
              </SelectContent>
            </Select>
          }
        />

        <div className="container mx-auto px-6 py-8 space-y-8">
          {/* KPIs Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* Glosas Evitadas Mes */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Glosas Evitadas (Mes)</CardTitle>
                <DollarSign className="h-4 w-4 text-success" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-success">{formatCOP(financiero.glosas_evitadas_mes_cop)}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  Período actual
                </p>
              </CardContent>
            </Card>

            {/* Glosas Evitadas Año */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Acumulado Anual</CardTitle>
                <TrendingUp className="h-4 w-4 text-primary" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-primary">{formatCOP(financiero.glosas_evitadas_anio_cop)}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  Año {new Date().getFullYear()}
                </p>
              </CardContent>
            </Card>

            {/* Historias Auditadas */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Historias Auditadas</CardTitle>
                <FileText className="h-4 w-4 text-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{financiero.historias_auditadas_periodo}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  Tiempo promedio: {financiero.tiempo_promedio_auditoria_min} min
                </p>
              </CardContent>
            </Card>

            {/* ROI */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">ROI Período</CardTitle>
                {financiero.roi_periodo > 0 ? (
                  <TrendingUp className="h-4 w-4 text-success" />
                ) : (
                  <TrendingDown className="h-4 w-4 text-danger" />
                )}
              </CardHeader>
              <CardContent>
                <div className={`text-2xl font-bold ${financiero.roi_periodo > 0 ? 'text-success' : 'text-danger'}`}>
                  {formatPercent(financiero.roi_periodo)}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  Retorno de inversión
                </p>
              </CardContent>
            </Card>

            {/* Estancias Prolongadas */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Días Estancia Extra</CardTitle>
                <AlertTriangle className="h-4 w-4 text-warning" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-warning">{financiero.estancias_prolongadas_dias}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  Ahorro: {formatCOP(financiero.ahorro_estancia_mes_cop)}
                </p>
              </CardContent>
            </Card>

            {/* Tasa Riesgo Alto */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Tasa Riesgo Alto</CardTitle>
                <AlertTriangle className="h-4 w-4 text-danger" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-danger">{formatPercent(financiero.tasa_riesgo_alto_porcentaje)}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  De historias auditadas
                </p>
              </CardContent>
            </Card>

            {/* Pendientes Resueltos */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Pendientes Resueltos</CardTitle>
                <CheckCircle2 className="h-4 w-4 text-success" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-success">{formatPercent(financiero.pendientes_resueltos_porcentaje)}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  Tasa de resolución
                </p>
              </CardContent>
            </Card>

            {/* Proyección Anual */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Proyección Anual</CardTitle>
                <TrendingUp className="h-4 w-4 text-primary" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-primary">{formatCOP(financiero.proyeccion_ahorro_anual)}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  Estimación basada en tendencia
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Gráficos */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Ahorro Acumulado */}
            <Card>
              <CardHeader>
                <CardTitle>Ahorro Acumulado</CardTitle>
                <CardDescription>Evolución temporal del ahorro en COP</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={graficos.ahorro_acumulado}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="etiqueta" />
                    <YAxis tickFormatter={(v) => `${(v / 1000000).toFixed(1)}M`} />
                    <Tooltip formatter={(v: number) => formatCOP(v)} />
                    <Line type="monotone" dataKey="valor" stroke={COLORS.primary} strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Glosas por Día */}
            <Card>
              <CardHeader>
                <CardTitle>Glosas Evitadas por Día</CardTitle>
                <CardDescription>Cantidad de hallazgos resueltos</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={graficos.glosas_tiempo}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="etiqueta" />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="valor" fill={COLORS.success} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Desglose de Ahorro */}
            <Card>
              <CardHeader>
                <CardTitle>Desglose de Ahorro</CardTitle>
                <CardDescription>Distribución por tipo de hallazgo</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={desgloseAhorro}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={(entry) => `${entry.name}: ${((entry.value / financiero.glosas_evitadas_mes_cop) * 100).toFixed(0)}%`}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {desgloseAhorro.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(v: number) => formatCOP(v)} />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Hallazgos por Módulo */}
            <Card>
              <CardHeader>
                <CardTitle>Hallazgos por Módulo</CardTitle>
                <CardDescription>Distribución por tipo de auditoría</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={modulosData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="value" fill={COLORS.purple} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>

          {/* Acciones */}
          <Card>
            <CardHeader>
              <CardTitle>Exportar Reportes</CardTitle>
              <CardDescription>Descarga reportes en formato PDF o Excel</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-4">
              <Button onClick={() => handleExecutiveReport()}>
                <FileText className="h-4 w-4 mr-2" />
                Reporte Ejecutivo PDF
              </Button>
              <Button variant="outline" onClick={() => handleExport('excel')}>
                <Download className="h-4 w-4 mr-2" />
                Exportar CSV
              </Button>
              <Button variant="outline" onClick={() => handleExport('pdf')}>
                <Download className="h-4 w-4 mr-2" />
                Exportar JSON
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </RoleGuard>
  );
};

export default DashboardPage;
