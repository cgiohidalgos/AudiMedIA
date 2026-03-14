import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { patientsApi, AuditSummary, AuditSessionStatus, ResetResponse } from '@/lib/api';
import { toast } from 'sonner';
import AppNavbar from '@/components/AppNavbar';
import PDFViewer from '@/components/PDFViewer';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
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
  Activity,
  RotateCcw,
  PlayCircle,
  BookOpen,
  Eye,
  EyeOff,
} from 'lucide-react';

const ReporteIndividualPage = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [audit, setAudit] = useState<AuditSummary | null>(null);
  const [session, setSession] = useState<AuditSessionStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState<'pdf' | 'excel' | 'html' | null>(null);
  const [showResumeModal, setShowResumeModal] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [isReanalyzing, setIsReanalyzing] = useState(false);
  const [reanalyzingStatus, setReanalyzingStatus] = useState('');
  const [showPdfViewer, setShowPdfViewer] = useState(false);

  useEffect(() => {
    if (id) {
      fetchReportData();
    }
  }, [id]);

  const fetchReportData = async () => {
    try {
      setLoading(true);
      // Cargar datos de auditoría y sesión en paralelo
      const [auditData, sessionData] = await Promise.allSettled([
        patientsApi.audit(id!),
        patientsApi.getSession(id!),
      ]);

      if (auditData.status === 'fulfilled') {
        setAudit(auditData.value);
      } else {
        toast.error('Error al cargar auditoría');
      }

      if (sessionData.status === 'fulfilled') {
        setSession(sessionData.value);
        // Mostrar modal si la sesión tiene progreso previo
        if (sessionData.value.tiene_progreso_previo) {
          setShowResumeModal(true);
        }
      }
    } finally {
      setLoading(false);
    }
  };

  const fetchAuditData = fetchReportData;

  const pollUntilDone = async () => {
    setIsReanalyzing(true);
    const maxAttempts = 60;
    let attempts = 0;
    const statusLabels: Record<string, string> = {
      cargando: 'Cargando PDF...',
      anonimizando: 'Anonimizando...',
      extrayendo: 'Extrayendo variables...',
      analizando: 'Analizando hallazgos...',
      listo: 'Completado',
      error: 'Error en el análisis',
    };
    while (attempts < maxAttempts) {
      await new Promise(r => setTimeout(r, 3000));
      attempts++;
      try {
        const sessionData = await patientsApi.getSession(id!);
        setSession(sessionData);
        setReanalyzingStatus(statusLabels[sessionData.status] ?? sessionData.status);
        if (sessionData.status === 'listo' || sessionData.status === 'error') {
          if (sessionData.status === 'listo') {
            await fetchReportData();
            toast.success('Re-análisis completado. Hallazgos actualizados.');
          } else {
            toast.error('Error durante el re-análisis. Revisa los logs del backend.');
          }
          break;
        }
      } catch {}
    }
    setIsReanalyzing(false);
    setReanalyzingStatus('');
  };

  const handleResetSession = async () => {
    if (!id) return;
    try {
      setResetting(true);
      const result: ResetResponse = await patientsApi.resetSession(id);
      setShowResumeModal(false);
      setResetting(false);
      if (result.relaunched) {
        toast.success('Re-análisis iniciado. Los resultados se actualizarán automáticamente.');
        pollUntilDone();
      } else {
        toast.info('Archivo PDF no encontrado en disco. Carga el PDF nuevamente para re-analizar.');
        navigate('/app');
      }
    } catch (err: any) {
      toast.error(err.message || 'Error al reiniciar la sesión');
      setResetting(false);
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
    <div className={showPdfViewer ? 'h-screen flex flex-col bg-gray-50 overflow-hidden' : 'min-h-screen bg-gray-50'}>

      {/* Modal: Sesión de auditoría previa detectada */}
      <Dialog open={showResumeModal} onOpenChange={setShowResumeModal}>
        <DialogContent className="sm:max-w-md" aria-describedby={undefined}>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <BookOpen className="h-5 w-5 text-blue-600" />
              Sesión de auditoría guardada
            </DialogTitle>
            <DialogDescription>
              Se encontró una auditoría previa para este paciente.
            </DialogDescription>
          </DialogHeader>

          {session && (
            <div className="space-y-4 py-2">
              {/* Barra de progreso */}
              <div>
                <div className="flex justify-between text-sm text-gray-600 mb-1">
                  <span>Páginas auditadas</span>
                  <span className="font-medium">
                    {session.ultima_pagina_auditada} / {session.total_paginas_conocidas}
                    {' '}({session.porcentaje_completado}%)
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2.5">
                  <div
                    className="bg-blue-600 h-2.5 rounded-full transition-all"
                    style={{ width: `${session.porcentaje_completado}%` }}
                  />
                </div>
              </div>

              {session.fecha_ultima_auditoria && (
                <p className="text-sm text-gray-500">
                  Última actividad:{' '}
                  <span className="font-medium text-gray-700">
                    {new Date(session.fecha_ultima_auditoria).toLocaleString('es-CO')}
                  </span>
                </p>
              )}

              <p className="text-sm text-gray-600">
                ¿Deseas continuar revisando los hallazgos existentes o reiniciar la auditoría desde cero?
              </p>
            </div>
          )}

          <DialogFooter className="flex gap-2 sm:flex-row flex-col">
            <Button
              variant="outline"
              onClick={handleResetSession}
              disabled={resetting}
              className="flex-1"
            >
              {resetting ? (
                <div className="animate-spin h-4 w-4 border-2 border-current border-t-transparent rounded-full mr-2" />
              ) : (
                <RotateCcw className="h-4 w-4 mr-2" />
              )}
              Reiniciar auditoría
            </Button>
            <Button
              onClick={() => setShowResumeModal(false)}
              className="flex-1"
            >
              <PlayCircle className="h-4 w-4 mr-2" />
              Continuar revisión
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Banner de re-análisis en progreso */}
      {isReanalyzing && (
        <div className="bg-blue-50 border-b border-blue-200 px-4 py-3 flex items-center gap-3">
          <div className="animate-spin h-4 w-4 border-2 border-blue-600 border-t-transparent rounded-full shrink-0" />
          <span className="text-sm text-blue-800 font-medium">
            Re-análisis en curso: {reanalyzingStatus || 'Procesando...'}
          </span>
          <span className="text-xs text-blue-600 ml-auto">Los hallazgos se actualizarán automáticamente al finalizar.</span>
        </div>
      )}

      {/* Header */}
      <AppNavbar
        title="Reporte de Auditoría"
        extraActions={
          <div className="flex gap-2">
            <Button
              variant={showPdfViewer ? 'default' : 'outline'}
              size="sm"
              onClick={() => setShowPdfViewer((v) => !v)}
            >
              {showPdfViewer ? (
                <EyeOff className="mr-1 h-3.5 w-3.5" />
              ) : (
                <Eye className="mr-1 h-3.5 w-3.5" />
              )}
              {showPdfViewer ? 'Ocultar PDF' : 'Ver historia clínica'}
            </Button>
            <Button variant="outline" size="sm" onClick={handleExportHtml} disabled={exporting !== null}>
              {exporting === 'html' ? (
                <div className="animate-spin h-3.5 w-3.5 border-2 border-current border-t-transparent rounded-full mr-1" />
              ) : (
                <Code className="mr-1 h-3.5 w-3.5" />
              )}
              HTML
            </Button>
            <Button variant="outline" size="sm" onClick={handleExportExcel} disabled={exporting !== null}>
              {exporting === 'excel' ? (
                <div className="animate-spin h-3.5 w-3.5 border-2 border-current border-t-transparent rounded-full mr-1" />
              ) : (
                <Sheet className="mr-1 h-3.5 w-3.5" />
              )}
              Excel
            </Button>
            <Button size="sm" onClick={handleExportPdf} disabled={exporting !== null}>
              {exporting === 'pdf' ? (
                <div className="animate-spin h-3.5 w-3.5 border-2 border-current border-t-transparent rounded-full mr-1" />
              ) : (
                <FileDown className="mr-1 h-3.5 w-3.5" />
              )}
              PDF
            </Button>
          </div>
        }
      />

      <div className={showPdfViewer ? 'flex flex-1 overflow-hidden' : ''}>
        <div className={showPdfViewer ? 'flex-1 overflow-y-auto' : ''}>
        <div className="max-w-7xl mx-auto px-4 py-8 space-y-6">

        {/* Banner de progreso de sesión */}
        {session && (
          <div className="flex items-center justify-between bg-blue-50 border border-blue-200 rounded-lg px-4 py-3">
            <div className="flex items-center gap-3">
              <BookOpen className="h-5 w-5 text-blue-600 shrink-0" />
              <div>
                <p className="text-sm font-medium text-blue-900">
                  Sesión de auditoría:{' '}
                  <span className="font-bold">
                    {session.ultima_pagina_auditada} de {session.total_paginas_conocidas} páginas
                    ({session.porcentaje_completado}%)
                  </span>
                </p>
                {session.fecha_ultima_auditoria && (
                  <p className="text-xs text-blue-600">
                    Última auditoría: {new Date(session.fecha_ultima_auditoria).toLocaleString('es-CO')}
                  </p>
                )}
              </div>
            </div>
            <div className="flex items-center gap-3 shrink-0">
              {/* Barra de progreso compacta */}
              <div className="w-32 bg-blue-200 rounded-full h-2 hidden sm:block">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all"
                  style={{ width: `${session.porcentaje_completado}%` }}
                />
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowResumeModal(true)}
                className="text-blue-700 border-blue-300 hover:bg-blue-100"
              >
                <RotateCcw className="h-3.5 w-3.5 mr-1.5" />
                Reiniciar
              </Button>
            </div>
          </div>
        )}

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
        </div>{/* end scroll wrapper */}

        {/* Visor de PDF integrado */}
        {showPdfViewer && audit && (
          <div className="w-[520px] shrink-0 border-l border-border h-full">
            <PDFViewer
              patientId={id!}
              patientLabel={audit.paciente.label}
              onClose={() => setShowPdfViewer(false)}
            />
          </div>
        )}
      </div>{/* end flex row */}
    </div>
  );
};

export default ReporteIndividualPage;
