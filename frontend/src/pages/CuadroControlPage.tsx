import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { patientsApi, PatientControlBoard } from '@/lib/api';
import { Button } from '@/components/ui/button';
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
  RotateCcw
} from 'lucide-react';

export default function CuadroControlPage() {
  const navigate = useNavigate();
  const [patients, setPatients] = useState<PatientControlBoard[]>([]);
  const [filteredPatients, setFilteredPatients] = useState<PatientControlBoard[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filtros
  const [filterRisk, setFilterRisk] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');

  // Cargar datos iniciales
  useEffect(() => {
    loadControlBoard();
  }, []);

  // Aplicar filtros cuando cambien
  useEffect(() => {
    applyFilters();
  }, [patients, filterRisk, filterStatus]);

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

    if (filterRisk !== 'all') {
      filtered = filtered.filter(p => p.riesgo_glosa === filterRisk);
    }

    if (filterStatus !== 'all') {
      filtered = filtered.filter(p => p.audit_status === filterStatus);
    }

    setFilteredPatients(filtered);
  };

  const resetFilters = () => {
    setFilterRisk('all');
    setFilterStatus('all');
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
    // TODO: Implementar exportación a Excel del cuadro completo
    alert('Exportación a Excel - próximamente');
  };

  const exportToPdf = () => {
    // TODO: Implementar exportación a PDF del cuadro completo
    alert('Exportación a PDF - próximamente');
  };

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
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Filter className="h-5 w-5" />
              <CardTitle>Filtros</CardTitle>
            </div>
            <Button variant="ghost" size="sm" onClick={resetFilters}>
              Limpiar filtros
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <div className="flex-1">
              <label className="text-sm font-medium mb-2 block">Nivel de Riesgo</label>
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
            <div className="flex-1">
              <label className="text-sm font-medium mb-2 block">Estado de Auditoría</label>
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
          </div>
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
                    <TableHead className="text-center">Días Hosp.</TableHead>
                    <TableHead className="text-center">Días Esperados</TableHead>
                    <TableHead>Estudios Pendientes</TableHead>
                    <TableHead className="text-center">Riesgo Glosa</TableHead>
                    <TableHead className="text-right">Exposición</TableHead>
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
