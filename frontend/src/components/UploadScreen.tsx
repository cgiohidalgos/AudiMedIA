import { useState, useCallback, useRef } from 'react';
import { Upload, FileText, X, Loader2, CheckCircle2, AlertCircle, ScanText, BrainCircuit } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { UploadedFile, FileStatus } from '@/types/audit';
import { uploadApi, processingApi, type DocumentStatus } from '@/lib/api';
import { toast } from 'sonner';

// â”€â”€â”€ Labels y helpers visuales â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

const statusLabels: Record<FileStatus, string> = {
  idle: 'En cola',
  cargando: 'Subiendo...',
  subido: 'PDF guardado',
  extrayendo: 'Extrayendo texto...',
  extraido: 'Texto extraÃ­do',
  anonimizando: 'Anonimizando...',
  analizando: 'Analizando con IA...',
  listo: 'AnÃ¡lisis completo',
  error: 'Error',
};

const stepProgress: Record<DocumentStatus, number> = {
  cargando: 10,
  subido: 33,
  extrayendo: 45,
  extraido: 66,
  anonimizando: 55,
  analizando: 80,
  listo: 100,
  error: 100,
};

const POLL_MS = 2500;

interface UploadedFileWithSession extends UploadedFile {
  sessionId?: string;
}

interface UploadScreenProps {
  onStartAnalysis: (hadErrors: boolean) => void;
}

const UploadScreen = ({ onStartAnalysis }: UploadScreenProps) => {
  const [files, setFiles] = useState<UploadedFileWithSession[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const rawFilesRef = useRef<File[]>([]);

  // â”€â”€â”€ Agregar PDFs â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  const addFiles = useCallback((newFiles: FileList | null) => {
    if (!newFiles) return;
    const remaining = 5 - files.length;
    const toAdd = Array.from(newFiles).slice(0, remaining);
    rawFilesRef.current = [...rawFilesRef.current, ...toAdd];

    setFiles(prev => [
      ...prev,
      ...toAdd.map(f => ({
        id: crypto.randomUUID(),
        name: f.name,
        size: f.size,
        status: 'idle' as FileStatus,
        progress: 0,
      })),
    ]);
  }, [files.length]);

  const removeFile = (id: string) => {
    setFiles(prev => {
      const idx = prev.findIndex(f => f.id === id);
      if (idx !== -1) rawFilesRef.current.splice(idx, 1);
      return prev.filter(f => f.id !== id);
    });
  };

  // â”€â”€â”€ Helper: polling hasta estado estable â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  const pollUntilStable = async (
    sessionId: string,
    fileId: string,
    stableStates: DocumentStatus[],
  ) => {
    let attempts = 0;
    while (attempts < 120) {
      await new Promise(r => setTimeout(r, POLL_MS));
      attempts++;
      try {
        const s = await uploadApi.getStatus(sessionId);
        setFiles(prev => prev.map(f =>
          f.id === fileId
            ? { ...f, status: s.status as FileStatus, progress: stepProgress[s.status] ?? f.progress }
            : f,
        ));
        if (stableStates.includes(s.status as DocumentStatus) || s.status === 'error') {
          return s.status as DocumentStatus;
        }
      } catch {
        // ignorar errores de red transitorios
      }
    }
    return 'error' as DocumentStatus;
  };

  // â”€â”€â”€ Etapa 1: subir PDFs â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  const handleUpload = async () => {
    const rawFiles = rawFilesRef.current;
    if (!rawFiles.length) return;
    setUploading(true);

    setFiles(prev => prev.map(f => ({ ...f, status: 'cargando' as FileStatus, progress: 10 })));

    try {
      const responses = await uploadApi.uploadPdfs(rawFiles);

      setFiles(prev => prev.map((f, i) => ({
        ...f,
        sessionId: responses[i]?.session_id,
        status: (responses[i]?.status ?? 'error') as FileStatus,
        progress: stepProgress[responses[i]?.status as DocumentStatus] ?? 33,
      })));

      toast.success(`${responses.length} PDF${responses.length > 1 ? 's' : ''} guardado${responses.length > 1 ? 's' : ''}. Ahora extrae el texto.`);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Error al subir archivos';
      toast.error(msg);
      setFiles(prev => prev.map(f => ({ ...f, status: 'error' as FileStatus })));
    } finally {
      setUploading(false);
    }
  };

  // â”€â”€â”€ Etapa 2: extraer texto â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  const handleExtract = async (fileId: string, sessionId: string) => {
    setFiles(prev => prev.map(f =>
      f.id === fileId ? { ...f, status: 'extrayendo' as FileStatus, progress: 45 } : f,
    ));

    try {
      await processingApi.extract(sessionId);
      const finalStatus = await pollUntilStable(sessionId, fileId, ['extraido']);

      if (finalStatus === 'extraido') {
        toast.success('Texto extraÃ­do y guardado en chunks. Ahora analiza con IA.');
      } else {
        toast.error('Error al extraer el texto del PDF.');
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Error al extraer texto';
      toast.error(msg);
      setFiles(prev => prev.map(f =>
        f.id === fileId ? { ...f, status: 'error' as FileStatus } : f,
      ));
    }
  };

  // â”€â”€â”€ Etapa 3: analizar con IA â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  const handleProcess = async (fileId: string, sessionId: string) => {
    setFiles(prev => prev.map(f =>
      f.id === fileId ? { ...f, status: 'analizando' as FileStatus, progress: 80 } : f,
    ));

    try {
      await processingApi.process(sessionId);
      const finalStatus = await pollUntilStable(sessionId, fileId, ['listo']);

      if (finalStatus === 'listo') {
        toast.success('Â¡AnÃ¡lisis completado!');
        // Si todos los archivos con sessionId estÃ¡n listos o en error, navegar
        setFiles(prev => {
          const updated = prev.map(f =>
            f.id === fileId ? { ...f, status: 'listo' as FileStatus, progress: 100 } : f,
          );
          const allDone = updated
            .filter(f => f.sessionId)
            .every(f => f.status === 'listo' || f.status === 'error');
          if (allDone) {
            const hadErrors = updated.every(f => f.status === 'error');
            setTimeout(() => onStartAnalysis(hadErrors), 800);
          }
          return updated;
        });
      } else {
        toast.error('Error durante el anÃ¡lisis con IA.');
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Error en anÃ¡lisis IA';
      toast.error(msg);
      setFiles(prev => prev.map(f =>
        f.id === fileId ? { ...f, status: 'error' as FileStatus } : f,
      ));
    }
  };

  // â”€â”€â”€ Render â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  const canUpload = files.length > 0 && !uploading && files.every(f => f.status === 'idle');

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-background px-4">
      <div className="w-full max-w-2xl">
        <h1 className="font-display text-2xl font-bold text-foreground text-center mb-1">
          Audi Med IA
        </h1>
        <p className="text-sm text-muted-foreground text-center mb-8 font-body">
          Sistema de AuditorÃ­a MÃ©dica basada en Inteligencia Artificial
        </p>

        {/* Drop zone â€” solo visible si aÃºn no se ha subido nada */}
        {files.every(f => f.status === 'idle') && (
          <div
            className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors cursor-pointer ${
              isDragging ? 'border-foreground bg-accent' : 'border-border bg-card hover:border-muted-foreground'
            } ${files.length >= 5 ? 'opacity-50 pointer-events-none' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setIsDragging(false);
              addFiles(e.dataTransfer.files);
            }}
            onClick={() => {
              if (files.length < 5) {
                const input = document.createElement('input');
                input.type = 'file';
                input.accept = '.pdf';
                input.multiple = true;
                input.onchange = () => addFiles(input.files);
                input.click();
              }
            }}
          >
            <Upload className="mx-auto h-10 w-10 text-muted-foreground mb-3" />
            <p className="font-body text-sm text-foreground font-medium">
              Arrastre archivos PDF aquÃ­ o haga clic para seleccionar
            </p>
            <p className="font-body text-xs text-muted-foreground mt-1">
              MÃ¡ximo 5 archivos Â· PDF digital o escaneado
            </p>
          </div>
        )}

        {/* Lista de archivos con botones de etapa */}
        {files.length > 0 && (
          <div className="mt-6 space-y-3">
            {files.map((file) => (
              <div key={file.id} className="bg-card border border-border rounded-lg p-4">
                {/* Fila nombre + estado */}
                <div className="flex items-start gap-3">
                  <FileText className="h-5 w-5 text-muted-foreground shrink-0 mt-0.5" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-body text-sm font-medium text-foreground truncate">{file.name}</span>
                      {/* Ãcono de estado */}
                      {file.status === 'listo' && <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" />}
                      {file.status === 'error' && <AlertCircle className="h-4 w-4 text-destructive shrink-0" />}
                      {(file.status === 'extrayendo' || file.status === 'analizando' || file.status === 'cargando') && (
                        <Loader2 className="h-4 w-4 animate-spin text-muted-foreground shrink-0" />
                      )}
                      {file.status === 'idle' && !uploading && (
                        <button
                          onClick={() => removeFile(file.id)}
                          className="text-muted-foreground hover:text-foreground shrink-0"
                          aria-label="Eliminar"
                        >
                          <X className="h-4 w-4" />
                        </button>
                      )}
                    </div>

                    {/* Barra de progreso */}
                    <div className="flex items-center gap-2 mt-2">
                      <div className="flex-1 h-1.5 bg-secondary rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-500 ${
                            file.status === 'listo' ? 'bg-green-500' :
                            file.status === 'error' ? 'bg-destructive' : 'bg-foreground'
                          }`}
                          style={{ width: `${file.progress}%` }}
                        />
                      </div>
                      <span className="text-xs text-muted-foreground shrink-0">{statusLabels[file.status]}</span>
                    </div>

                    {/* Etapas visuales */}
                    <div className="flex items-center gap-1 mt-2 text-[10px] text-muted-foreground">
                      <span className={file.progress >= 33 ? 'text-foreground font-medium' : ''}>â‘  Subido</span>
                      <span className="mx-1">â†’</span>
                      <span className={file.progress >= 66 ? 'text-foreground font-medium' : ''}>â‘¡ Texto extraÃ­do</span>
                      <span className="mx-1">â†’</span>
                      <span className={file.progress >= 100 ? 'text-green-500 font-medium' : ''}>â‘¢ IA procesada</span>
                    </div>
                  </div>
                </div>

                {/* Botones de acciÃ³n segÃºn etapa */}
                {file.sessionId && (
                  <div className="mt-3 flex gap-2 justify-end">
                    {file.status === 'subido' && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleExtract(file.id, file.sessionId!)}
                        className="gap-1.5 font-body text-xs"
                      >
                        <ScanText className="h-3.5 w-3.5" />
                        Extraer texto
                      </Button>
                    )}
                    {file.status === 'extraido' && (
                      <Button
                        size="sm"
                        onClick={() => handleProcess(file.id, file.sessionId!)}
                        className="gap-1.5 font-body text-xs"
                      >
                        <BrainCircuit className="h-3.5 w-3.5" />
                        Analizar con IA
                      </Button>
                    )}
                    {file.status === 'error' && (
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => handleExtract(file.id, file.sessionId!)}
                        className="gap-1.5 font-body text-xs"
                      >
                        Reintentar extracciÃ³n
                      </Button>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* BotÃ³n principal: Subir PDFs (solo etapa 1) */}
        {canUpload && (
          <div className="mt-6 flex justify-center">
            <Button onClick={handleUpload} className="font-body px-8">
              Subir PDF{files.length > 1 ? 's' : ''}
            </Button>
          </div>
        )}

        {uploading && (
          <div className="mt-4 flex justify-center">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        )}
      </div>
    </div>
  );
};

export default UploadScreen;
