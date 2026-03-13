import { useState, useEffect, useRef } from 'react';
import { X, Send, Loader2, MessageSquare, Users } from 'lucide-react';
import { chatApi } from '@/lib/api';

interface ChatPanelProps {
  patientId: string;
  patientLabel: string;
  allPatientIds?: string[];
  onClose: () => void;
}

interface ChatMessageLocal {
  role: 'user' | 'assistant';
  content: string;
  referencias?: { pagina: number; fragmento: string }[];
}

const suggestions = [
  '¿Hay evolución de hoy?',
  '¿Está justificada la estancia?',
  '¿Faltan reportes de estudios?',
  '¿Hay medicamentos sin indicación?',
  '¿Cuál es el riesgo de glosa?',
];

const ChatPanel = ({ patientId, patientLabel, allPatientIds, onClose }: ChatPanelProps) => {
  const [messages, setMessages] = useState<ChatMessageLocal[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const [chatMode, setChatMode] = useState<'single' | 'multi'>('single');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    const loadHistory = async () => {
      try {
        setIsLoadingHistory(true);
        const history = await chatApi.history(patientId);
        if (history.length === 0) {
          setMessages([{
            role: 'assistant',
            content: `Chat activo para ${patientLabel}. Puede consultar cualquier aspecto de la historia clínica. Las respuestas incluirán referencia a la página del documento fuente.\n\n⚠️ Esta respuesta es generada por IA como apoyo al criterio del auditor y no reemplaza la revisión clínica profesional.`,
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
      if (chatMode === 'multi' && allPatientIds && allPatientIds.length > 1) {
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
      console.error('Error enviando mensaje:', error);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Lo siento, hubo un error al procesar su pregunta. Por favor, intente nuevamente.',
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
            : `Chat — ${patientLabel}`}
        </h2>
        <button onClick={onClose} className="text-muted-foreground hover:text-foreground shrink-0">
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Mode toggle */}
      {showMultiToggle && (
        <div className="px-4 py-2 border-b border-border flex items-center gap-2">
          <span className="text-xs text-muted-foreground font-body shrink-0">Modo:</span>
          <div className="flex rounded-md overflow-hidden border border-border text-xs flex-1">
            <button
              onClick={() => setChatMode('single')}
              className={`flex-1 flex items-center justify-center gap-1 py-1 font-body transition-colors ${
                chatMode === 'single'
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-secondary'
              }`}
            >
              <MessageSquare className="h-3 w-3" />
              Esta historia
            </button>
            <button
              onClick={() => setChatMode('multi')}
              className={`flex-1 flex items-center justify-center gap-1 py-1 font-body transition-colors ${
                chatMode === 'multi'
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-secondary'
              }`}
            >
              <Users className="h-3 w-3" />
              Todas ({allPatientIds?.length})
            </button>
          </div>
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
              {m.role === 'assistant' && m.referencias && m.referencias.length > 0 && (
                <div className="mt-1.5 flex flex-wrap gap-1">
                  {[...new Set(m.referencias.map(r => r.pagina))].sort((a, b) => a - b).map(page => (
                    <span
                      key={page}
                      className="text-xs bg-blue-100 text-blue-700 rounded px-2 py-0.5 font-medium font-body"
                      title={`Referencia a página ${page}`}
                    >
                      pág. {page}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))
        )}
        {isLoading && (
          <div className="mr-4">
            <div className="rounded-md p-3 text-sm font-body bg-secondary text-foreground flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>Generando respuesta...</span>
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
          placeholder={chatMode === 'multi' ? 'Pregunta sobre todos los pacientes...' : 'Escriba su pregunta...'}
          disabled={isLoading}
          className="flex-1 font-body text-sm bg-background border border-input rounded-md px-3 py-2 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring disabled:opacity-50 disabled:cursor-not-allowed"
        />
        <button
          onClick={() => sendMessage(input)}
          disabled={isLoading || !input.trim()}
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
