import { useState, useEffect } from 'react';
import { X, Send, Loader2 } from 'lucide-react';
import { chatApi } from '@/lib/api';

interface ChatPanelProps {
  patientId: string;
  patientLabel: string;
  onClose: () => void;
}

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

const suggestions = [
  '¿Hay evolución de hoy?',
  '¿Está justificada la estancia?',
  '¿Faltan reportes de estudios?',
];

const ChatPanel = ({ patientId, patientLabel, onClose }: ChatPanelProps) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);

  // Cargar historial al montar el componente
  useEffect(() => {
    const loadHistory = async () => {
      try {
        setIsLoadingHistory(true);
        const history = await chatApi.history(patientId);
        if (history.length === 0) {
          // Mensaje de bienvenida si no hay historial
          setMessages([{
            role: 'assistant',
            content: `Chat activo para ${patientLabel}. Puede consultar cualquier aspecto de la historia clínica. Las respuestas incluirán referencia a la página del documento fuente.\n\nEsta respuesta es generada por IA como apoyo al criterio del auditor y no reemplaza la revisión clínica profesional.`
          }]);
        } else {
          setMessages(history);
        }
      } catch (error) {
        console.error('Error cargando historial:', error);
        setMessages([{
          role: 'assistant',
          content: 'Error cargando el historial del chat. Por favor, intente nuevamente.'
        }]);
      } finally {
        setIsLoadingHistory(false);
      }
    };
    loadHistory();
  }, [patientId, patientLabel]);

  const sendMessage = async (text: string) => {
    if (!text.trim() || isLoading) return;

    const userMsg: ChatMessage = { role: 'user', content: text };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await chatApi.ask(patientId, text);
      const assistantMsg: ChatMessage = {
        role: 'assistant',
        content: response.answer,
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (error) {
      console.error('Error enviando mensaje:', error);
      const errorMsg: ChatMessage = {
        role: 'assistant',
        content: 'Lo siento, hubo un error al procesar su pregunta. Por favor, intente nuevamente.',
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <aside className="w-80 border-l border-border bg-card flex flex-col h-full shrink-0">
      <div className="p-4 border-b border-border flex items-center justify-between">
        <h2 className="panel-header">Chat — {patientLabel}</h2>
        <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
          <X className="h-4 w-4" />
        </button>
      </div>

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
      </div>

      {/* Input */}
      <div className="p-3 border-t border-border flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !isLoading && sendMessage(input)}
          placeholder="Escriba su pregunta..."
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
