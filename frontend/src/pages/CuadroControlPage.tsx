import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { patientsApi, PatientControlBoard } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import AppNavbar from '@/components/AppNavbar';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  FileText, 
  AlertCircle, 
  Clock, 
  TrendingUp,
  Download,
  Filter,
  RotateCcw,
  Search,
  X,
  Calendar,
  ChevronUp,
  ChevronDown,
  ArrowUpDown,
} from 'lucide-react';

export default function CuadroControlPage() {
  const navigate = useNavigate();
  const [patients, setPatients] = useState<PatientControlBoard[]>([]);
  const [filteredPatients, setFilteredPatients] = useState<PatientControlBoard[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filtros
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [filterRisk, setFilterRisk] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [filterCIE10, setFilterCIE10] = useState<string>('');
  const [filterFechaDesde, setFilterFechaDesde] = useState<string>('');
  const [filterFechaHasta, setFilterFechaHasta] = useState<string>('');
  const [filterDiasMin, setFilterDiasMin] = useState<string>('');
  const [filterDiasMax, setFilterDiasMax] = useState<string>('');

  // Ordenamiento
  type SortField = 'dias_hospitalizacion' | 'riesgo_glosa' | 'exposicion_glosas' | null;
  type SortDir = 'asc' | 'desc';
  const [sortField, setSortField] = useState<SortField>(null);
  const [sortDir, setSortDir] = useState<SortDir>('asc');

  // Cargar datos iniciales
  useEffect(() => {
    loadControlBoard();
  }, []);

  // Aplicar filtros cuando cambien
  useEffect(() => {
    applyFilters();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [patients, searchQuery, filterRisk, filterStatus, filterCIE10, filterFechaDesde, filterFechaHasta, filterDiasMin, filterDiasMax, sortField, sortDir]);

  const loadControlBoard = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await patientsApi.controlBoard();
      setPatients(data);
    } catch (err: any) {
      setError(err.message || 'Error al cargar el cuadro de control');
    } finally {
      setLoading(false);
    }
  };

  const applyFilters = () => {
    let filtered = [...patients];

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      filtered = filtered.filter(p =>
        p.historia?.toLowerCase().includes(q) ||
        (p.cama?.toLowerCase().includes(q) ?? false) ||
        p.diagnostico?.toLowerCase().includes(q)
      );
    }

    if (filterRisk !== 'all') {
      filtered = filtered.filter(p => p.riesgo_glosa === filterRisk);
    }

    if (filterStatus !== 'all') {
      filtered = filtered.filter(p => p.audit_status === filterStatus);
    }

    if (filterCIE10.trim()) {
      const cie = filterCIE10.toUpperCase();
      filtered = filtered.filter(p =>
        (p.codigo_cie10?.toUpperCase().includes(cie) ?? false) ||
        p.diagnostico?.toUpperCase().includes(cie)
      );
    }

    if (filterFechaDesde) {
      filtered = filtered.filter(p =>
        p.fecha_ingreso != null && new Date(p.fecha_ingreso) >= new Date(filterFechaDesde)
      );
    }

    if (filterFechaHasta) {
      filtered = filtered.filter(p =>
        p.fecha_ingreso != null && new Date(p.fecha_ingreso) <= new Date(filterFechaHasta)
      );
    }

    if (filterDiasMin !== '') {
      filtered = filtered.filter(p => p.dias_hospitalizacion >= Number(filterDiasMin));
    }

    if (filterDiasMax !== '') {
      filtered = filtered.filter(p => p.dias_hospitalizacion <= Number(filterDiasMax));
    }

    // Ordenamiento por columna
    if (sortField) {
      const riskWeight: Record<string, number> = { alto: 3, medio: 2, bajo: 1, pending: 0 };
      filtered.sort((a, b) => {
        let cmp = 0;
        if (sortField === 'dias_hospitalizacion') {
          cmp = a.dias_hospitalizacion - b.dias_hospitalizacion;
        } else if (sortField === 'riesgo_glosa') {
          cmp = (riskWeight[a.riesgo_glosa] ?? 0) - (riskWeight[b.riesgo_glosa] ?? 0);
        } else if (sortField === 'exposicion_glosas') {
          cmp = a.exposicion_glosas - b.exposicion_glosas;
        }
        return sortDir === 'asc' ? cmp : -cmp;
      });
    }

    setFilteredPatients(filtered);
  };

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir(prev => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDir('asc');
    }
  };

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) return <ArrowUpDown className="h-3 w-3 ml-1 opacity-40" />;
    return sortDir === 'asc'
      ? <ChevronUp className="h-3 w-3 ml-1" />
      : <ChevronDown className="h-3 w-3 ml-1" />;
  };

  const resetFilters = () => {
    setSearchQuery('');
    setFilterRisk('all');
    setFilterStatus('all');
    setFilterCIE10('');
    setFilterFechaDesde('');
    setFilterFechaHasta('');
    setFilterDiasMin('');
    setFilterDiasMax('');
  };

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'alto':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'medio':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'bajo':
        return 'bg-green-100 text-green-800 border-green-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getRiskLabel = (risk: string) => {
    switch (risk) {
      case 'alto':
        return 'ALTO';
      case 'medio':
        return 'MEDIO';
      case 'bajo':
        return 'BAJO';
      default:
        return 'PENDIENTE';
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'completed':
        return 'Completado';
      case 'processing':
        return 'Procesando';
      default:
        return 'Pendiente';
    }
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      minimumFractionDigits: 0,
    }).format(value);
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('es-CO', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const exportToExcel = () => {
    const header = [
      'Cama', 'Historia', 'Diagnóstico', 'CIE-10', 'Fecha Ingreso',
      'Días Hosp.', 'Días Esperados', 'Estudios Pendientes',
      'Riesgo Glosa', 'Exposición COP', 'Total Hallazgos', 'Estado',
    ];
    const rows = filteredPatients.map(p => [
      p.cama || '',
      p.historia || '',
      p.diagnostico || '',
      p.codigo_cie10 || '',
      p.fecha_ingreso ? new Date(p.fecha_ingreso).toLocaleDateString('es-CO') : '',
      p.dias_hospitalizacion,
      p.dias_esperados || '',
      p.estudios_pendientes.join(' | '),
      getRiskLabel(p.riesgo_glosa),
      p.exposicion_glosas,
      p.total_hallazgos,
      getStatusLabel(p.audit_status),
    ]);
    const csvContent = [header, ...rows]
      .map(row => row.map(val => `"${String(val).replace(/"/g, '""')}"`).join(','))
      .join('\n');
    const BOM = '\uFEFF';
    const blob = new Blob([BOM + csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `cuadro_control_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const exportToPdf = () => {
    const today = new Date().toLocaleDateString('es-CO', { day: '2-digit', month: '2-digit', year: 'numeric' });
    const tableRows = filteredPatients.map(p => `
      <tr>
        <td>${p.cama || 'N/A'}</td>
        <td>${p.historia}</td>
        <td>${p.diagnostico}</td>
        <td style="text-align:center">${p.dias_hospitalizacion}</td>
        <td style="text-align:center">${p.dias_esperados || 'N/A'}</td>
        <td>${p.estudios_pendientes.length > 0 ? p.estudios_pendientes.join(', ') : '—'}</td>
        <td style="text-align:center;font-weight:bold;color:${p.riesgo_glosa === 'alto' ? '#c0392b' : p.riesgo_glosa === 'medio' ? '#d97706' : '#16a34a'}">${getRiskLabel(p.riesgo_glosa)}</td>
        <td style="text-align:right">${formatCurrency(p.exposicion_glosas)}</td>
        <td style="text-align:center">${getStatusLabel(p.audit_status)}</td>
      </tr>`).join('');
    const html = `<!DOCTYPE html>
<html><head><meta charset="utf-8" /><title>Cuadro de Control — ${today}</title>
<style>
  body{font-family:Arial,sans-serif;font-size:11px;margin:20px;color:#222}
  h1{font-size:16px;margin-bottom:4px}
  .sub{color:#666;font-size:11px;margin-bottom:12px}
  .kpis{display:flex;gap:12px;margin-bottom:14px}
  .kpi{background:#f3f4f6;border-radius:6px;padding:8px 14px}
  .kpi-lbl{font-size:9px;color:#888;text-transform:uppercase}
  .kpi-val{font-size:16px;font-weight:bold}
  table{width:100%;border-collapse:collapse}
  th{background:#1e3a5f;color:#fff;padding:6px 8px;text-align:left;font-size:10px}
  td{padding:5px 8px;border-bottom:1px solid #e5e7eb;vertical-align:top}
  tr:nth-child(even) td{background:#f9fafb}
  @media print{body{margin:0}}
</style></head>
<body>
  <h1>AudiMedIA — Cuadro de Control</h1>
  <div class="sub">Generado el ${today} &nbsp;·&nbsp; ${filteredPatients.length} pacientes${activeFiltersCount > 0 ? ' (filtros activos)' : ''}</div>
  <div class="kpis">
    <div class="kpi"><div class="kpi-lbl">Total</div><div class="kpi-val">${stats.total}</div></div>
    <div class="kpi" style="background:#fee2e2"><div class="kpi-lbl">Riesgo Alto</div><div class="kpi-val" style="color:#c0392b">${stats.alto}</div></div>
    <div class="kpi" style="background:#fef9c3"><div class="kpi-lbl">Riesgo Medio</div><div class="kpi-val" style="color:#d97706">${stats.medio}</div></div>
    <div class="kpi" style="background:#dcfce7"><div class="kpi-lbl">Riesgo Bajo</div><div class="kpi-val" style="color:#16a34a">${stats.bajo}</div></div>
    <div class="kpi"><div class="kpi-lbl">Exposición Total</div><div class="kpi-val" style="font-size:12px">${formatCurrency(stats.exposicionTotal)}</div></div>
  </div>
  <table>
    <thead><tr>
      <th>Cama</th><th>Historia</th><th>Diagnóstico</th><th>Días Hosp.</th><th>Días Esp.</th>
      <th>Estudios Pendientes</th><th>Riesgo</th><th>Exposición</th><th>Estado</th>
    </tr></thead>
    <tbody>${tableRows}</tbody>
  </table>
</body></html>`;
    const blob = new Blob([html], { type: 'text/html;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const win = window.open(url, '_blank');
    if (win) {
      win.onload = () => { win.print(); URL.revokeObjectURL(url); };
    }
  };

  // Filtros activos
  const activeFiltersCount = [
    searchQuery.trim(),
    filterRisk !== 'all' ? filterRisk : '',
    filterStatus !== 'all' ? filterStatus : '',
    filterCIE10.trim(),
    filterFechaDesde,
    filterFechaHasta,
    filterDiasMin,
    filterDiasMax,
  ].filter(Boolean).length;

  // Estadísticas generales
  const stats = {
    total: filteredPatients.length,
    alto: filteredPatients.filter(p => p.riesgo_glosa === 'alto').length,
    medio: filteredPatients.filter(p => p.riesgo_glosa === 'medio').length,
    bajo: filteredPatients.filter(p => p.riesgo_glosa === 'bajo').length,
    exposicionTotal: filteredPatients.reduce((sum, p) => sum + p.exposicion_glosas, 0),
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Cargando cuadro de control...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto p-6">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
        <Button onClick={loadControlBoard} className="mt-4">
          Reintentar
        </Button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <AppNavbar
        title="Cuadro de Control"
        extraActions={
          <div className="flex gap-2">
            <Button variant="outline" size="sm" className="h-7 text-xs" onClick={exportToExcel}>
              <Download className="h-3.5 w-3.5 mr-1" />Excel
            </Button>
            <Button variant="outline" size="sm" className="h-7 text-xs" onClick={exportToPdf}>
              <Download className="h-3.5 w-3.5 mr-1" />PDF
            </Button>
            <Button size="sm" className="h-7 text-xs" onClick={loadControlBoard}>
              <RotateCcw className="h-3.5 w-3.5 mr-1" />Actualizar
            </Button>
          </div>
        }
      />
      <div className="container mx-auto p-6 space-y-6">

      {/* KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Pacientes</CardDescription>
            <CardTitle className="text-3xl">{stats.total}</CardTitle>
          </CardHeader>
        </Card>
        <Card className="border-red-200 bg-red-50">
          <CardHeader className="pb-2">
            <CardDescription>Riesgo Alto</CardDescription>
            <CardTitle className="text-3xl text-red-700">{stats.alto}</CardTitle>
          </CardHeader>
        </Card>
        <Card className="border-yellow-200 bg-yellow-50">
          <CardHeader className="pb-2">
            <CardDescription>Riesgo Medio</CardDescription>
            <CardTitle className="text-3xl text-yellow-700">{stats.medio}</CardTitle>
          </CardHeader>
        </Card>
        <Card className="border-green-200 bg-green-50">
          <CardHeader className="pb-2">
            <CardDescription>Riesgo Bajo</CardDescription>
            <CardTitle className="text-3xl text-green-700">{stats.bajo}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Exposición Total</CardDescription>
            <CardTitle className="text-2xl">{formatCurrency(stats.exposicionTotal)}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      {/* Filtros */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Filter className="h-5 w-5" />
            <CardTitle>Búsqueda y Filtros Avanzados</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Búsqueda general */}
          <div className="relative">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Buscar por historia, cama o diagnóstico..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>

          {/* Filtros: riesgo, estado, CIE-10 */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1.5 block">Nivel de Riesgo</label>
              <Select value={filterRisk} onValueChange={setFilterRisk}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos</SelectItem>
                  <SelectItem value="alto">Alto</SelectItem>
                  <SelectItem value="medio">Medio</SelectItem>
                  <SelectItem value="bajo">Bajo</SelectItem>
                  <SelectItem value="pending">Pendiente</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1.5 block">Estado de Auditoría</label>
              <Select value={filterStatus} onValueChange={setFilterStatus}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos</SelectItem>
                  <SelectItem value="completed">Completado</SelectItem>
                  <SelectItem value="processing">Procesando</SelectItem>
                  <SelectItem value="pending">Pendiente</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1.5 block">Código CIE-10</label>
              <Input
                placeholder="Ej: J18.9, I50, E11..."
                value={filterCIE10}
                onChange={(e) => setFilterCIE10(e.target.value)}
              />
            </div>
          </div>

          {/* Filtros: fechas y días */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1.5 block">
                <Calendar className="inline h-3 w-3 mr-1" />Ingreso desde
              </label>
              <Input
                type="date"
                value={filterFechaDesde}
                onChange={(e) => setFilterFechaDesde(e.target.value)}
              />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1.5 block">
                <Calendar className="inline h-3 w-3 mr-1" />Ingreso hasta
              </label>
              <Input
                type="date"
                value={filterFechaHasta}
                onChange={(e) => setFilterFechaHasta(e.target.value)}
              />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1.5 block">Días mín.</label>
              <Input
                type="number"
                min="0"
                placeholder="0"
                value={filterDiasMin}
                onChange={(e) => setFilterDiasMin(e.target.value)}
              />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1.5 block">Días máx.</label>
              <Input
                type="number"
                min="0"
                placeholder="365"
                value={filterDiasMax}
                onChange={(e) => setFilterDiasMax(e.target.value)}
              />
            </div>
          </div>

          {/* Indicador de filtros activos */}
          {activeFiltersCount > 0 && (
            <div className="flex items-center gap-2">
              <Badge variant="secondary">
                {activeFiltersCount} filtro{activeFiltersCount > 1 ? 's' : ''} activo{activeFiltersCount > 1 ? 's' : ''}
              </Badge>
              <Button variant="ghost" size="sm" onClick={resetFilters} className="h-6 text-xs px-2">
                <X className="h-3 w-3 mr-1" />Limpiar todo
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Tabla */}
      <Card>
        <CardHeader>
          <CardTitle>Pacientes Hospitalizados ({filteredPatients.length})</CardTitle>
          <CardDescription>
            Click en una fila para ver el reporte individual completo
          </CardDescription>
        </CardHeader>
        <CardContent>
          {filteredPatients.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <AlertCircle className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No se encontraron pacientes con los filtros aplicados</p>
            </div>
          ) : (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Cama</TableHead>
                    <TableHead>Historia</TableHead>
                    <TableHead>Diagnóstico</TableHead>
                    <TableHead
                      className="text-center cursor-pointer select-none hover:bg-muted/50"
                      onClick={() => toggleSort('dias_hospitalizacion')}
                    >
                      <span className="inline-flex items-center justify-center">
                        Días Hosp.<SortIcon field="dias_hospitalizacion" />
                      </span>
                    </TableHead>
                    <TableHead className="text-center">Días Esperados</TableHead>
                    <TableHead>Estudios Pendientes</TableHead>
                    <TableHead
                      className="text-center cursor-pointer select-none hover:bg-muted/50"
                      onClick={() => toggleSort('riesgo_glosa')}
                    >
                      <span className="inline-flex items-center justify-center">
                        Riesgo Glosa<SortIcon field="riesgo_glosa" />
                      </span>
                    </TableHead>
                    <TableHead
                      className="text-right cursor-pointer select-none hover:bg-muted/50"
                      onClick={() => toggleSort('exposicion_glosas')}
                    >
                      <span className="inline-flex items-center justify-end">
                        Exposición<SortIcon field="exposicion_glosas" />
                      </span>
                    </TableHead>
                    <TableHead className="text-center">Estado</TableHead>
                    <TableHead className="text-center">Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredPatients.map((patient) => (
                    <TableRow
                      key={patient.id}
                      className="cursor-pointer hover:bg-gray-50"
                      onClick={() => navigate(`/patients/${patient.id}/report`)}
                    >
                      <TableCell className="font-medium">
                        {patient.cama || 'N/A'}
                      </TableCell>
                      <TableCell>{patient.historia}</TableCell>
                      <TableCell className="max-w-xs truncate">
                        {patient.diagnostico}
                      </TableCell>
                      <TableCell className="text-center">
                        <div className="flex items-center justify-center gap-1">
                          <Clock className="h-4 w-4 text-gray-400" />
                          {patient.dias_hospitalizacion}
                        </div>
                      </TableCell>
                      <TableCell className="text-center text-gray-600">
                        {patient.dias_esperados}
                      </TableCell>
                      <TableCell>
                        {patient.estudios_pendientes.length > 0 ? (
                          <div className="flex flex-col gap-1">
                            {patient.estudios_pendientes.slice(0, 2).map((estudio, idx) => (
                              <Badge key={idx} variant="outline" className="text-xs">
                                {estudio}
                              </Badge>
                            ))}
                            {patient.estudios_pendientes.length > 2 && (
                              <span className="text-xs text-gray-500">
                                +{patient.estudios_pendientes.length - 2} más
                              </span>
                            )}
                          </div>
                        ) : (
                          <span className="text-gray-400 text-sm">Sin pendientes</span>
                        )}
                      </TableCell>
                      <TableCell className="text-center">
                        <Badge className={getRiskColor(patient.riesgo_glosa)}>
                          {getRiskLabel(patient.riesgo_glosa)}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right font-medium">
                        {formatCurrency(patient.exposicion_glosas)}
                      </TableCell>
                      <TableCell className="text-center">
                        <Badge variant="secondary" className="text-xs">
                          {getStatusLabel(patient.audit_status)}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-center">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            navigate(`/patients/${patient.id}/report`);
                          }}
                        >
                          <FileText className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  </div>
  );
}
