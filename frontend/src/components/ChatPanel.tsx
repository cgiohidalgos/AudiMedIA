import { useState, useEffect, useRef } from 'react';
import { X, Send, Loader2, MessageSquare, Users, FileText, BookOpen } from 'lucide-react';
import { chatApi, patientsApi, type RagReference } from '@/lib/api';

interface ChatPanelProps {
  patientId: string;
  patientLabel: string;
  allPatientIds?: string[];
  onClose: () => void;
  /** Callback invocado al hacer click en una referencia de pÃ¡gina. Abre el visor en esa pÃ¡gina. */
  onViewPage?: (page: number) => void;
}

interface ChatMessageLocal {
  role: 'user' | 'assistant';
  content: string;
  referencias?: { pagina: number; fragmento: string }[];
  ragRefs?: RagReference[];
  model?: string;
}

const suggestions = [
  'Â¿Hay evoluciÃ³n de hoy?',
  'Â¿EstÃ¡ justificada la estancia?',
  'Â¿Faltan reportes de estudios?',
  'Â¿Hay medicamentos sin indicaciÃ³n?',
  'Â¿CuÃ¡l es el riesgo de glosa?',
];

type ChatMode = 'single' | 'multi' | 'rag';

const ChatPanel = ({ patientId, patientLabel, allPatientIds, onClose, onViewPage }: ChatPanelProps) => {
  const [messages, setMessages] = useState<ChatMessageLocal[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const [chatMode, setChatMode] = useState<ChatMode>('single');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Cargar session_id para el modo RAG
  useEffect(() => {
    patientsApi.getSession(patientId)
      .then(s => setSessionId(s.id))
      .catch(() => setSessionId(null));
  }, [patientId]);

  useEffect(() => {
    const loadHistory = async () => {
      try {
        setIsLoadingHistory(true);
        const history = await chatApi.history(patientId);
        if (history.length === 0) {
          setMessages([{
            role: 'assistant',
            content: `Chat activo para ${patientLabel}. Puede consultar cualquier aspecto de la historia clÃ­nica. Las respuestas incluirÃ¡n referencia a la pÃ¡gina del documento fuente.\n\nâš ï¸ Esta respuesta es generada por IA como apoyo al criterio del auditor y no reemplaza la revisiÃ³n clÃ­nica profesional.`,
          }]);
        } else {
          setMessages(history.map(m => ({
            role: m.role,
            content: m.content,
            referencias: m.referencias || [],
          })));
        }
      } catch (error) {
        console.error('Error cargando historial:', error);
        setMessages([{
          role: 'assistant',
          content: 'Error cargando el historial del chat. Por favor, intente nuevamente.',
        }]);
      } finally {
        setIsLoadingHistory(false);
      }
    };
    loadHistory();
  }, [patientId, patientLabel]);

  const sendMessage = async (text: string) => {
    if (!text.trim() || isLoading) return;

    setMessages(prev => [...prev, { role: 'user', content: text }]);
    setInput('');
    setIsLoading(true);

    try {
      if (chatMode === 'rag') {
        if (!sessionId) throw new Error('SesiÃ³n no encontrada. Extrae el texto del PDF primero.');
        // Construir historial para Cohere (Ãºltimos 8 intercambios)
        const history = messages
          .filter(m => m.role === 'user' || m.role === 'assistant')
          .slice(-8)
          .map(m => ({ role: m.role, content: m.content }));
        const response = await chatApi.askRag(sessionId, text, history);
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: response.answer,
          ragRefs: response.references,
          model: response.model_used,
        }]);
      } else if (chatMode === 'multi' && allPatientIds && allPatientIds.length > 1) {
        const response = await chatApi.askMulti(text, allPatientIds);
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: response.answer,
          referencias: response.referencias || [],
        }]);
      } else {
        const response = await chatApi.ask(patientId, text);
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: response.answer,
          referencias: response.referencias || [],
        }]);
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : 'Error al procesar su pregunta.';
      console.error('Error enviando mensaje:', error);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Lo siento, hubo un error: ${msg}`,
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const showMultiToggle = allPatientIds && allPatientIds.length > 1;

  return (
    <aside className="w-80 border-l border-border bg-card flex flex-col h-full shrink-0">
      {/* Header */}
      <div className="p-4 border-b border-border flex items-center justify-between gap-2">
        <h2 className="panel-header truncate">
          {chatMode === 'multi'
            ? `Todas las historias (${allPatientIds?.length})`
            : chatMode === 'rag'
            ? `RAG â€” ${patientLabel}`
            : `Chat â€” ${patientLabel}`}
        </h2>
        <button onClick={onClose} className="text-muted-foreground hover:text-foreground shrink-0">
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Mode toggle */}
      <div className="px-4 py-2 border-b border-border flex items-center gap-2">
        <span className="text-xs text-muted-foreground font-body shrink-0">Modo:</span>
        <div className="flex rounded-md overflow-hidden border border-border text-xs flex-1">
          <button
            onClick={() => setChatMode('single')}
            className={`flex-1 flex items-center justify-center gap-1 py-1 font-body transition-colors ${
              chatMode === 'single' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-secondary'
            }`}
            title="Chat con datos estructurados del paciente (OpenAI)"
          >
            <MessageSquare className="h-3 w-3" />
            Datos
          </button>
          {showMultiToggle && (
            <button
              onClick={() => setChatMode('multi')}
              className={`flex-1 flex items-center justify-center gap-1 py-1 font-body transition-colors ${
                chatMode === 'multi' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-secondary'
              }`}
              title="Chat sobre mÃºltiples pacientes"
            >
              <Users className="h-3 w-3" />
              Todos
            </button>
          )}
          <button
            onClick={() => setChatMode('rag')}
            className={`flex-1 flex items-center justify-center gap-1 py-1 font-body transition-colors ${
              chatMode === 'rag' ? 'bg-blue-600 text-white' : 'text-muted-foreground hover:bg-secondary'
            }`}
            title="RAG: busca en el texto original del PDF (Cohere Command R)"
          >
            <BookOpen className="h-3 w-3" />
            RAG
          </button>
        </div>
      </div>

      {/* Info banner mode RAG */}
      {chatMode === 'rag' && (
        <div className="px-4 py-2 bg-blue-50 border-b border-blue-200 text-[10px] text-blue-700 font-body">
          Buscando en el <strong>texto original del PDF</strong> con Cohere Command R + Rerank.
          {!sessionId && <span className="text-red-600"> âš ï¸ Extrae el texto primero.</span>}
        </div>
      )}

      {/* Suggestions */}
      <div className="px-4 py-2 border-b border-border flex gap-1.5 flex-wrap">
        {suggestions.map((s) => (
          <button
            key={s}
            onClick={() => sendMessage(s)}
            className="text-xs font-body border border-border rounded-full px-2.5 py-1 text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
          >
            {s}
          </button>
        ))}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {isLoadingHistory ? (
          <div className="flex items-center justify-center h-full">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          messages.map((m, i) => (
            <div key={i} className={`${m.role === 'user' ? 'ml-8' : 'mr-4'}`}>
              <div className={`rounded-md p-3 text-sm font-body whitespace-pre-wrap ${
                m.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-secondary text-foreground'
              }`}>
                {m.content}
              </div>
              {/* Referencias modo clÃ¡sico */}
              {m.role === 'assistant' && m.referencias && m.referencias.length > 0 && (
                <div className="mt-1.5 flex flex-wrap gap-1">
                  {[...new Set(m.referencias.map(r => r.pagina))].sort((a, b) => a - b).map(page => (
                    onViewPage ? (
                      <button
                        key={page}
                        onClick={() => onViewPage(page)}
                        className="text-xs bg-blue-100 text-blue-700 hover:bg-blue-200 rounded px-2 py-0.5 font-medium font-body flex items-center gap-1 transition-colors"
                      >
                        <FileText className="h-2.5 w-2.5" />
                        pÃ¡g. {page}
                      </button>
                    ) : (
                      <span key={page} className="text-xs bg-blue-100 text-blue-700 rounded px-2 py-0.5 font-medium font-body">
                        pÃ¡g. {page}
                      </span>
                    )
                  ))}
                </div>
              )}
              {/* Referencias modo RAG */}
              {m.role === 'assistant' && m.ragRefs && m.ragRefs.length > 0 && (
                <div className="mt-1.5 space-y-1">
                  <p className="text-[10px] text-muted-foreground font-body">
                    Fragmentos usados ({m.ragRefs.length}):
                  </p>
                  {m.ragRefs.map((r, ri) => (
                    <div key={ri} className="text-[10px] bg-blue-50 border border-blue-200 rounded px-2 py-1 font-body">
                      <div className="flex items-center justify-between mb-0.5">
                        {onViewPage ? (
                          <button
                            onClick={() => onViewPage(r.page_number)}
                            className="text-blue-700 hover:underline font-medium flex items-center gap-1"
                          >
                            <FileText className="h-2.5 w-2.5" />
                            pÃ¡g. {r.page_number}
                          </button>
                        ) : (
                          <span className="text-blue-700 font-medium">pÃ¡g. {r.page_number}</span>
                        )}
                        <span className="text-muted-foreground">score: {r.relevance_score.toFixed(2)}</span>
                      </div>
                      <p className="text-muted-foreground line-clamp-2">{r.text_snippet}</p>
                    </div>
                  ))}
                  {m.model && (
                    <p className="text-[9px] text-muted-foreground font-body text-right">modelo: {m.model}</p>
                  )}
                </div>
              )}
            </div>
          ))
        )}
        {isLoading && (
          <div className="mr-4">
            <div className="rounded-md p-3 text-sm font-body bg-secondary text-foreground flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>{chatMode === 'rag' ? 'Buscando en el documento...' : 'Generando respuesta...'}</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-3 border-t border-border flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !isLoading && sendMessage(input)}
          placeholder={
            chatMode === 'rag'
              ? 'Buscar en el PDF...'
              : chatMode === 'multi'
              ? 'Pregunta sobre todos los pacientes...'
              : 'Escriba su pregunta...'
          }
          disabled={isLoading || (chatMode === 'rag' && !sessionId)}
          className="flex-1 font-body text-sm bg-background border border-input rounded-md px-3 py-2 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring disabled:opacity-50 disabled:cursor-not-allowed"
        />
        <button
          onClick={() => sendMessage(input)}
          disabled={isLoading || !input.trim() || (chatMode === 'rag' && !sessionId)}
          className="bg-primary text-primary-foreground rounded-md p-2 hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
        </button>
      </div>
    </aside>
  );
};

export default ChatPanel;
