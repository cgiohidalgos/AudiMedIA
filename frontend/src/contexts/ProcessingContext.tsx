/**
 * ProcessingContext — gestiona los análisis IA en segundo plano.
 *
 * • Almacena las sesiones activas en sessionStorage (sobrevive navegación).
 * • Hace polling a /progress cada 3s desde cualquier página.
 * • Cuando una sesión termina (listo / error) dispara un CustomEvent
 *   para que UploadScreen y AppPage reaccionen.
 */
import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { processingApi, type AiProgress } from '@/lib/api';
import { toast } from 'sonner';

export interface ActiveAnalysis {
  sessionId: string;
  fileId: string;
  fileName: string;
}

interface ProcessingContextValue {
  activeAnalyses: ActiveAnalysis[];
  progress: Record<string, AiProgress>;   // sessionId → progreso
  addAnalysis: (analysis: ActiveAnalysis) => void;
  removeAnalysis: (sessionId: string) => void;
}

const ProcessingContext = createContext<ProcessingContextValue>({
  activeAnalyses: [],
  progress: {},
  addAnalysis: () => {},
  removeAnalysis: () => {},
});

const STORAGE_KEY = 'audiomedia_active_analyses';
const POLL_MS = 3000;

export function ProcessingProvider({ children }: { children: React.ReactNode }) {
  const [activeAnalyses, setActiveAnalyses] = useState<ActiveAnalysis[]>(() => {
    try {
      const stored = sessionStorage.getItem(STORAGE_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  });
  const [progress, setProgress] = useState<Record<string, AiProgress>>({});
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Persistir en sessionStorage cuando cambia la lista
  useEffect(() => {
    try { sessionStorage.setItem(STORAGE_KEY, JSON.stringify(activeAnalyses)); } catch { /* */ }
  }, [activeAnalyses]);

  const addAnalysis = useCallback((analysis: ActiveAnalysis) => {
    setActiveAnalyses(prev =>
      prev.some(a => a.sessionId === analysis.sessionId) ? prev : [...prev, analysis]
    );
  }, []);

  const removeAnalysis = useCallback((sessionId: string) => {
    setActiveAnalyses(prev => prev.filter(a => a.sessionId !== sessionId));
    setProgress(prev => { const n = { ...prev }; delete n[sessionId]; return n; });
  }, []);

  // Polling: corre siempre que haya al menos un análisis activo
  useEffect(() => {
    if (activeAnalyses.length === 0) {
      if (intervalRef.current) { clearInterval(intervalRef.current); intervalRef.current = null; }
      return;
    }

    const poll = async () => {
      // Snapshot para evitar estado stale
      setActiveAnalyses(current => {
        current.forEach(async (analysis) => {
          try {
            const p = await processingApi.getProgress(analysis.sessionId);
            setProgress(prev => ({ ...prev, [analysis.sessionId]: p }));

            if (p.status === 'listo') {
              toast.success(`✅ Análisis completado: ${analysis.fileName}`);
              window.dispatchEvent(new CustomEvent('processingComplete', { detail: analysis }));
              removeAnalysis(analysis.sessionId);
            } else if (p.status === 'error') {
              toast.error(`❌ Error en análisis: ${analysis.fileName}`);
              window.dispatchEvent(new CustomEvent('processingError', { detail: analysis }));
              removeAnalysis(analysis.sessionId);
            }
          } catch { /* error de red transitorio — ignorar */ }
        });
        return current; // no mutamos el estado aquí
      });
    };

    poll();
    intervalRef.current = setInterval(poll, POLL_MS);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeAnalyses.length, removeAnalysis]);

  return (
    <ProcessingContext.Provider value={{ activeAnalyses, progress, addAnalysis, removeAnalysis }}>
      {children}
    </ProcessingContext.Provider>
  );
}

export function useProcessing() {
  return useContext(ProcessingContext);
}
