import { useState, useEffect } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import { usePDFViewer } from '@/hooks/usePDFViewer';
import { patientsApi } from '@/lib/api';
import { Button } from '@/components/ui/button';
import {
  ChevronLeft,
  ChevronRight,
  ZoomIn,
  ZoomOut,
  Download,
  X,
  Maximize2,
  Minimize2,
  Loader2,
  AlertTriangle,
  FileText,
  RotateCcw,
} from 'lucide-react';

// Configurar worker de PDF.js usando CDN para compatibilidad con Vite
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

interface PDFViewerProps {
  /** ID del paciente cuyo PDF se visualizará */
  patientId: string;
  /** Etiqueta del paciente (para descarga) */
  patientLabel: string;
  /** Página inicial a mostrar (1-based) */
  initialPage?: number;
  /** Callback al cerrar el visor */
  onClose: () => void;
  /** Clases CSS adicionales para el contenedor */
  className?: string;
}

const PDFViewer = ({
  patientId,
  patientLabel,
  initialPage = 1,
  onClose,
  className,
}: PDFViewerProps) => {
  const {
    fileUrl,
    isLoading,
    error,
    numPages,
    setNumPages,
    currentPage,
    scale,
    goToPage,
    goToPrev,
    goToNext,
    zoomIn,
    zoomOut,
    resetZoom,
  } = usePDFViewer(patientId, initialPage);

  const [pageInput, setPageInput] = useState(String(initialPage));
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [downloading, setDownloading] = useState(false);

  // Sincronizar el input de página con la página actual
  useEffect(() => {
    setPageInput(String(currentPage));
  }, [currentPage]);

  const handlePageInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      commitPageInput();
    }
  };

  const commitPageInput = () => {
    const page = parseInt(pageInput, 10);
    if (!isNaN(page) && page >= 1 && page <= numPages) {
      goToPage(page);
    } else {
      setPageInput(String(currentPage));
    }
  };

  const handleDownload = async () => {
    if (downloading) return;
    try {
      setDownloading(true);
      const blob = await patientsApi.downloadOriginalPdf(patientId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `historia_clinica_${patientLabel}.pdf`;
      document.body.appendChild(a);
      a.click();
      URL.revokeObjectURL(url);
      a.remove();
    } finally {
      setDownloading(false);
    }
  };

  const containerClass = isFullscreen
    ? 'fixed inset-0 z-50 flex flex-col bg-background'
    : `flex flex-col bg-card h-full ${className ?? ''}`;

  return (
    <div className={containerClass}>
      {/* ── Barra de herramientas ── */}
      <div className="flex items-center gap-1 px-3 py-2 border-b border-border bg-muted/30 shrink-0 overflow-x-auto">
        {/* Título */}
        <span className="text-xs font-medium text-foreground truncate mr-2 min-w-0">
          Historia — {patientLabel}
        </span>

        <div className="flex items-center gap-1 ml-auto shrink-0">
          {/* Navegación de páginas */}
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={goToPrev}
            disabled={currentPage <= 1 || isLoading}
            title="Página anterior"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
          </Button>

          <div className="flex items-center gap-1">
            <input
              type="text"
              value={pageInput}
              onChange={(e) => setPageInput(e.target.value)}
              onKeyDown={handlePageInputKeyDown}
              onBlur={commitPageInput}
              disabled={isLoading || numPages === 0}
              className="w-10 text-xs text-center border border-input rounded px-1 py-0.5 bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-ring disabled:opacity-50"
              aria-label="Número de página"
            />
            <span className="text-xs text-muted-foreground whitespace-nowrap">
              / {numPages || '—'}
            </span>
          </div>

          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={goToNext}
            disabled={currentPage >= numPages || isLoading}
            title="Página siguiente"
          >
            <ChevronRight className="h-3.5 w-3.5" />
          </Button>

          <div className="w-px h-4 bg-border mx-1" />

          {/* Zoom */}
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={zoomOut}
            disabled={scale <= 0.5}
            title="Alejar"
          >
            <ZoomOut className="h-3.5 w-3.5" />
          </Button>
          <button
            onClick={resetZoom}
            className="text-xs text-muted-foreground hover:text-foreground w-10 text-center"
            title="Restablecer zoom"
          >
            {Math.round(scale * 100)}%
          </button>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={zoomIn}
            disabled={scale >= 3.0}
            title="Acercar"
          >
            <ZoomIn className="h-3.5 w-3.5" />
          </Button>

          <div className="w-px h-4 bg-border mx-1" />

          {/* Descargar */}
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={handleDownload}
            disabled={downloading}
            title="Descargar PDF original"
          >
            {downloading ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Download className="h-3.5 w-3.5" />
            )}
          </Button>

          {/* Pantalla completa */}
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={() => setIsFullscreen((f) => !f)}
            title={isFullscreen ? 'Salir de pantalla completa' : 'Pantalla completa'}
          >
            {isFullscreen ? (
              <Minimize2 className="h-3.5 w-3.5" />
            ) : (
              <Maximize2 className="h-3.5 w-3.5" />
            )}
          </Button>

          {/* Cerrar */}
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={onClose}
            title="Cerrar visor"
          >
            <X className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      {/* ── Área del documento ── */}
      <div className="flex-1 overflow-auto flex items-start justify-center bg-muted/20 p-3">
        {/* Cargando blob */}
        {isLoading && (
          <div className="flex flex-col items-center justify-center py-16 gap-3 text-muted-foreground">
            <Loader2 className="h-8 w-8 animate-spin" />
            <span className="text-sm">Cargando historia clínica...</span>
          </div>
        )}

        {/* Error */}
        {error && !isLoading && (
          <div className="flex flex-col items-center justify-center py-16 gap-3 text-destructive">
            <AlertTriangle className="h-8 w-8" />
            <span className="text-sm text-center max-w-xs">{error}</span>
            <Button variant="outline" size="sm" onClick={onClose}>
              <X className="h-3.5 w-3.5 mr-1.5" />
              Cerrar
            </Button>
          </div>
        )}

        {/* PDF renderizado */}
        {fileUrl && !isLoading && (
          <Document
            file={fileUrl}
            onLoadSuccess={({ numPages: n }) => setNumPages(n)}
            onLoadError={() => {
              /* el hook ya maneja el error de red, este cubre errores de parseo */
            }}
            loading={
              <div className="flex flex-col items-center gap-2 py-8 text-muted-foreground">
                <Loader2 className="h-6 w-6 animate-spin" />
                <span className="text-xs">Renderizando página...</span>
              </div>
            }
            noData={
              <div className="flex flex-col items-center gap-2 py-8 text-muted-foreground">
                <FileText className="h-6 w-6" />
                <span className="text-xs">Sin datos PDF</span>
              </div>
            }
            error={
              <div className="flex flex-col items-center gap-2 py-8 text-destructive">
                <RotateCcw className="h-5 w-5" />
                <span className="text-xs text-center">Error al parsear el PDF</span>
              </div>
            }
          >
            <Page
              pageNumber={currentPage}
              scale={scale}
              renderTextLayer
              renderAnnotationLayer
              className="shadow-md"
            />
          </Document>
        )}
      </div>
    </div>
  );
};

export default PDFViewer;
