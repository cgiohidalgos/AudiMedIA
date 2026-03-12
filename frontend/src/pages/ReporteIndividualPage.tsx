import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { patientsApi, AuditSummary } from '@/lib/api';
import { toast } from 'sonner';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { 
  FileDown, 
  FileText, 
  Sheet, 
  Code, 
  AlertTriangle, 
  CheckCircle2, 
  ArrowLeft,
  Clock,
  Stethoscope,
  DollarSign,
  Activity
} from 'lucide-react';

const ReporteIndividualPage = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [audit, setAudit] = useState<AuditSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState<'pdf' | 'excel' | 'html' | null>(null);

  useEffect(() => {
    if (id) {
      fetchAuditData();
    }
  }, [id]);

  const fetchAuditData = async () => {
    try {
      setLoading(true);
      const data = await patientsApi.audit(id!);
      setAudit(data);
    } catch (error: any) {
      toast.error(error.message || 'Error al cargar auditoría');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleExportPdf = async () => {
    try {
      setExporting('pdf');
      const blob = await patientsApi.exportPdf(id!);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `reporte_auditoria_${audit?.paciente.label}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success('PDF descargado exitosamente');
    } catch (error: any) {
      toast.error(error.message || 'Error al exportar PDF');
    } finally {
      setExporting(null);
    }
  };

  const handleExportExcel = async () => {
    try {
      setExporting('excel');
      const blob = await patientsApi.exportExcel(id!);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `reporte_auditoria_${audit?.paciente.label}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success('Excel descargado exitosamente');
    } catch (error: any) {
      toast.error(error.message || 'Error al exportar Excel');
    } finally {
      setExporting(null);
    }
  };

  const handleExportHtml = async () => {
    try {
      setExporting('html');
      const html = await patientsApi.exportHtml(id!);
      const blob = new Blob([html], { type: 'text/html' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `reporte_auditoria_${audit?.paciente.label}.html`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success('HTML descargado exitosamente');
    } catch (error: any) {
      toast.error(error.message || 'Error al exportar HTML');
    } finally {
      setExporting(null);
    }
  };

  const getRiskBadgeVariant = (riesgo: string): "default" | "secondary" | "destructive" | "outline" => {
    switch (riesgo) {
      case 'alto':
        return 'destructive';
      case 'medio':
        return 'default';
      case 'bajo':
        return 'secondary';
      default:
        return 'outline';
    }
  };

  const getModuleIcon = (modulo: string) => {
    switch (modulo) {
      case 'estancia':
        return <Clock className="h-4 w-4" />;
      case 'cie10':
        return <Stethoscope className="h-4 w-4" />;
      case 'estudios':
        return <Activity className="h-4 w-4" />;
      case 'glosas':
        return <DollarSign className="h-4 w-4" />;
      default:
        return <FileText className="h-4 w-4" />;
    }
  };

  const formatCurrency = (value: number | null) => {
    if (!value) return 'N/A';
    return `$${value.toLocaleString('es-CO', { maximumFractionDigits: 0 })} COP`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto" />
          <p className="mt-4 text-gray-600">Cargando reporte de auditoría...</p>
        </div>
      </div>
    );
  }

  if (!audit) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <AlertTriangle className="h-16 w-16 text-red-500 mx-auto mb-4" />
          <h2 className="text-2xl font-semibold mb-2">No se pudo cargar el reporte</h2>
          <Button onClick={() => navigate('/app')}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Volver
          </Button>
        </div>
      </div>
    );
  }

  // Agrupar hallazgos por módulo
  const hallazgosPorModulo = audit.hallazgos.reduce((acc, h) => {
    if (!acc[h.modulo]) {
      acc[h.modulo] = [];
    }
    acc[h.modulo].push(h);
    return acc;
  }, {} as Record<string, typeof audit.hallazgos>);

  const moduloNames: Record<string, string> = {
    estancia: 'Análisis de Estancia',
    cie10: 'Pertinencia CIE-10',
    estudios: 'Estudios y Procedimientos',
    glosas: 'Detección de Glosas',
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button variant="ghost" onClick={() => navigate('/app')}>
                <ArrowLeft className="h-4 w-4" />
              </Button>
              <div>
                <h1 className="text-3xl font-bold text-gray-900">📋 Reporte de Auditoría</h1>
                <p className="text-gray-600 mt-1">Sistema AudiMedIA - Auditoría Concurrente con IA</p>
              </div>
            </div>
            
            {/* Botones de exportación */}
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={handleExportHtml}
                disabled={exporting !== null}
              >
                {exporting === 'html' ? (
                  <div className="animate-spin h-4 w-4 border-2 border-current border-t-transparent rounded-full mr-2" />
                ) : (
                  <Code className="mr-2 h-4 w-4" />
                )}
                HTML
              </Button>
              <Button
                variant="outline"
                onClick={handleExportExcel}
                disabled={exporting !== null}
              >
                {exporting === 'excel' ? (
                  <div className="animate-spin h-4 w-4 border-2 border-current border-t-transparent rounded-full mr-2" />
                ) : (
                  <Sheet className="mr-2 h-4 w-4" />
                )}
                Excel
              </Button>
              <Button
                onClick={handleExportPdf}
                disabled={exporting !== null}
              >
                {exporting === 'pdf' ? (
                  <div className="animate-spin h-4 w-4 border-2 border-current border-t-transparent rounded-full mr-2" />
                ) : (
                  <FileDown className="mr-2 h-4 w-4" />
                )}
                PDF
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-8 space-y-6">
        {/* Encabezado del paciente */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>Información del Paciente</span>
              <Badge variant={getRiskBadgeVariant(audit.riesgo_global)} className="text-lg px-4 py-1">
                RIESGO {audit.riesgo_global.toUpperCase()}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div>
                <p className="text-sm text-gray-600">Identificador</p>
                <p className="text-lg font-semibold">{audit.paciente.label}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Diagnóstico Principal</p>
                <p className="text-lg font-semibold">{audit.paciente.diagnostico_principal || 'N/A'}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Código CIE-10</p>
                <p className="text-lg font-semibold">{audit.paciente.codigo_cie10 || 'N/A'}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Días Hospitalización</p>
                <p className="text-lg font-semibold">{audit.paciente.dias_hospitalizacion || 'N/A'}</p>
              </div>
            </div>
            
            <Separator className="my-4" />
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-blue-50 rounded-lg p-4">
                <p className="text-sm text-blue-600 font-medium">Total Hallazgos</p>
                <p className="text-2xl font-bold text-blue-900">{audit.total_hallazgos}</p>
              </div>
              <div className="bg-red-50 rounded-lg p-4">
                <p className="text-sm text-red-600 font-medium">Exposición a Glosas</p>
                <p className="text-2xl font-bold text-red-900">{formatCurrency(audit.exposicion_glosas)}</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-sm text-gray-600 font-medium mb-2">Hallazgos por Riesgo</p>
                <div className="flex gap-2 flex-wrap">
                  {Object.entries(audit.hallazgos_por_riesgo).map(([riesgo, count]) => (
                    <Badge key={riesgo} variant={getRiskBadgeVariant(riesgo)}>
                      {riesgo}: {count}
                    </Badge>
                  ))}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Hallazgos por módulo */}
        <Card>
          <CardHeader>
            <CardTitle>🔍 Hallazgos por Módulo de Auditoría</CardTitle>
            <CardDescription>
              Hallazgos agrupados por cada módulo analizado
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {Object.entries(hallazgosPorModulo).map(([modulo, hallazgos]) => (
              <div key={modulo} className="space-y-3">
                <div className="flex items-center gap-2 mb-3">
                  {getModuleIcon(modulo)}
                  <h3 className="text-lg font-semibold text-blue-900">
                    {moduloNames[modulo] || modulo}
                  </h3>
                  <Badge variant="outline">{hallazgos.length} hallazgos</Badge>
                </div>
                
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[100px]">Riesgo</TableHead>
                      <TableHead>Descripción</TableHead>
                      <TableHead>Recomendación</TableHead>
                      <TableHead className="text-right">Valor Glosa</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {hallazgos.map((finding) => (
                      <TableRow key={finding.id}>
                        <TableCell>
                          <Badge variant={getRiskBadgeVariant(finding.riesgo)}>
                            {finding.riesgo.toUpperCase()}
                          </Badge>
                        </TableCell>
                        <TableCell className="font-medium">
                          {finding.descripcion}
                          {finding.normativa_aplicable && (
                            <p className="text-xs text-gray-500 mt-1">
                              📜 {finding.normativa_aplicable}
                            </p>
                          )}
                        </TableCell>
                        <TableCell className="text-sm text-gray-700">
                          💡 {finding.recomendacion}
                        </TableCell>
                        <TableCell className="text-right font-semibold">
                          {formatCurrency(finding.valor_glosa_estimado)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            ))}

            {audit.hallazgos.length === 0 && (
              <div className="text-center py-8">
                <CheckCircle2 className="h-16 w-16 text-green-500 mx-auto mb-4" />
                <p className="text-lg text-gray-600">No se encontraron hallazgos para este paciente</p>
                <p className="text-sm text-gray-500 mt-2">El caso ha pasado todas las validaciones</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recomendación general */}
        <Card className="bg-green-50 border-green-200">
          <CardHeader>
            <CardTitle className="text-green-900">📝 Recomendación General</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-green-800 leading-relaxed">{audit.recomendacion_general}</p>
          </CardContent>
        </Card>

        {/* Footer */}
        <Card className="bg-gray-100">
          <CardContent className="py-4">
            <p className="text-sm text-gray-600 text-center">
              <strong>AudiMedIA</strong> - Sistema de Auditoría Médica Concurrente con Inteligencia Artificial.
              <br />
              Este reporte fue generado automáticamente. La información presentada debe ser validada por personal médico calificado.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default ReporteIndividualPage;
