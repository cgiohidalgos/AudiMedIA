import { useState, useCallback } from 'react';
import { Upload, FileText, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { UploadedFile, FileStatus } from '@/types/audit';

const statusLabels: Record<FileStatus, string> = {
  idle: 'Listo para procesar',
  cargando: 'Cargando...',
  anonimizando: 'Anonimizando...',
  extrayendo: 'Extrayendo variables...',
  analizando: 'Analizando...',
  listo: 'Análisis completo',
  error: 'Error en procesamiento',
};

const historyLabels = ['Historia A', 'Historia B', 'Historia C', 'Historia D', 'Historia E'];

interface UploadScreenProps {
  onStartAnalysis: () => void;
}

const UploadScreen = ({ onStartAnalysis }: UploadScreenProps) => {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [processing, setProcessing] = useState(false);

  const addFiles = useCallback((newFiles: FileList | null) => {
    if (!newFiles) return;
    const remaining = 5 - files.length;
    const toAdd = Array.from(newFiles).slice(0, remaining);

    const uploadFiles: UploadedFile[] = toAdd.map((f, i) => ({
      id: crypto.randomUUID(),
      name: f.name,
      size: f.size,
      status: 'idle' as FileStatus,
      progress: 0,
      label: historyLabels[files.length + i],
    }));

    setFiles(prev => [...prev, ...uploadFiles]);
  }, [files.length]);

  const removeFile = (id: string) => {
    setFiles(prev => {
      const updated = prev.filter(f => f.id !== id);
      return updated.map((f, i) => ({ ...f, label: historyLabels[i] }));
    });
  };

  const simulateProcessing = async () => {
    setProcessing(true);
    const steps: FileStatus[] = ['cargando', 'anonimizando', 'extrayendo', 'analizando', 'listo'];

    for (let fi = 0; fi < files.length; fi++) {
      for (let si = 0; si < steps.length; si++) {
        await new Promise(r => setTimeout(r, 400));
        setFiles(prev => prev.map((f, i) =>
          i === fi ? { ...f, status: steps[si], progress: ((si + 1) / steps.length) * 100 } : f
        ));
      }
    }

    setTimeout(() => onStartAnalysis(), 600);
  };

  const allReady = files.length > 0 && !processing;

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-background px-4">
      <div className="w-full max-w-2xl">
        <h1 className="font-display text-2xl font-bold text-foreground text-center mb-1">
          Audi Med IA
        </h1>
        <p className="text-sm text-muted-foreground text-center mb-8 font-body">
          Sistema de Auditoría Médica basada en Inteligencia Artificial
        </p>

        {/* Drop zone */}
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
            Arrastre archivos PDF aquí o haga clic para seleccionar
          </p>
          <p className="font-body text-xs text-muted-foreground mt-1">
            Máximo 5 archivos · PDF digital o escaneado
          </p>
        </div>

        {/* File list */}
        {files.length > 0 && (
          <div className="mt-6 space-y-2">
            {files.map((file) => (
              <div key={file.id} className="bg-card border border-border rounded-md p-3 flex items-center gap-3">
                <FileText className="h-5 w-5 text-muted-foreground shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-body text-sm font-medium text-foreground truncate">{file.name}</span>
                    <span className="data-label shrink-0">{file.label}</span>
                  </div>
                  <div className="flex items-center gap-2 mt-1">
                    <div className="flex-1 h-1.5 bg-secondary rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-300 ${
                          file.status === 'listo' ? 'bg-success' : file.status === 'error' ? 'bg-destructive' : 'bg-foreground'
                        }`}
                        style={{ width: `${file.progress}%` }}
                      />
                    </div>
                    <span className="progress-step shrink-0">{statusLabels[file.status]}</span>
                  </div>
                </div>
                {!processing && (
                  <button
                    onClick={(e) => { e.stopPropagation(); removeFile(file.id); }}
                    className="text-muted-foreground hover:text-foreground shrink-0"
                    aria-label="Eliminar archivo"
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Action */}
        <div className="mt-6 flex justify-center">
          <Button
            disabled={!allReady}
            onClick={simulateProcessing}
            className="font-body px-8"
          >
            Iniciar análisis
          </Button>
        </div>
      </div>
    </div>
  );
};

export default UploadScreen;
