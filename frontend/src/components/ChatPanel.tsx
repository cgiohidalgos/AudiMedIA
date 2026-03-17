import { useState, useEffect, useRef } from 'react';
import { X, Send, Loader2, MessageSquare, Users, FileText, BookOpen, Download } from 'lucide-react';
import { chatApi, patientsApi, type RagReference } from '@/lib/api';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

interface ChatPanelProps {
  patientId: string;
  patientLabel: string;
  allPatientIds?: string[];
  onClose: () => void;
  /** Callback invocado al hacer click en una referencia de página. Abre el visor en esa página. */
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
  '¿Hay evolución de hoy?',
  '¿Está justificada la estancia?',
  '¿Faltan reportes de estudios?',
  '¿Hay medicamentos sin indicación?',
  '¿Cuál es el riesgo de glosa?',
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
      if (chatMode === 'rag') {
        if (!sessionId) throw new Error('Sesión no encontrada. Extrae el texto del PDF primero.');
        // Construir historial para Cohere (últimos 8 intercambios)
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

  const exportChat = (format: 'txt' | 'pdf') => {
    const chatMessages = messages.filter(m => m.role === 'user' || m.role === 'assistant');
    if (chatMessages.length === 0) return;
    const today = new Date().toLocaleDateString('es-CO', { day: '2-digit', month: '2-digit', year: 'numeric' });
    const title = chatMode === 'multi' ? `Multi-Historia (${allPatientIds?.length} pacs.)` : patientLabel;
    const modeLabel = chatMode === 'rag' ? 'RAG (PDF)' : chatMode === 'multi' ? 'Multi-historia' : 'Datos estructurados';

    if (format === 'txt') {
      const sep = '\u2500'.repeat(60);
      const lines = [
        'AudiMedIA \u2014 Log de Chat',
        `Paciente: ${title}`,
        `Fecha: ${today}`,
        `Modo: ${modeLabel}`,
        sep,
        '',
        ...chatMessages.map(m => {
          const role = m.role === 'user' ? 'AUDITOR' : 'IA';
          const refs = m.referencias?.length
            ? `\n  [Refs: p\u00e1gs. ${[...new Set(m.referencias.map(r => r.pagina))].sort((a, b) => a - b).join(', ')}]`
            : m.ragRefs?.length
            ? `\n  [Fragmentos PDF: ${m.ragRefs.map(r => `p\u00e1g. ${r.page_number}`).join(', ')}]`
            : '';
          return `[${role}]\n${m.content}${refs}\n`;
        }),
      ];
      const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `chat_${patientLabel.replace(/\s+/g, '_')}_${new Date().toISOString().split('T')[0]}.txt`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } else {
      const rows = chatMessages.map(m => {
        const role = m.role === 'user' ? 'Auditor' : 'IA';
        const bg = m.role === 'user' ? '#dbeafe' : '#f3f4f6';
        const refs = m.referencias?.length
          ? `<div style="margin-top:4px;font-size:10px;color:#2563eb">Refs: p\u00e1gs. ${[...new Set(m.referencias.map(r => r.pagina))].sort((a, b) => a - b).join(', ')}</div>`
          : m.ragRefs?.length
          ? `<div style="margin-top:4px;font-size:10px;color:#2563eb">Fragmentos: ${m.ragRefs.map(r => `p\u00e1g. ${r.page_number}`).join(', ')}</div>`
          : '';
        const safe = m.content.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        return `<div style="background:${bg};border-radius:8px;padding:10px 14px;margin-bottom:8px">
          <div style="font-size:10px;font-weight:bold;color:#6b7280;margin-bottom:4px;text-transform:uppercase">${role}</div>
          <div style="font-size:12px;white-space:pre-wrap">${safe}</div>${refs}</div>`;
      }).join('');
      const html = `<!DOCTYPE html><html><head><meta charset="utf-8"/><title>${title} \u2014 Chat Log</title>
<style>body{font-family:Arial,sans-serif;max-width:700px;margin:30px auto;color:#222}h1{font-size:16px;margin-bottom:4px}.sub{font-size:11px;color:#888;margin-bottom:16px}@media print{body{margin:10px}}</style></head>
<body><h1>AudiMedIA \u2014 Log de Chat</h1>
<p class="sub">Paciente: <b>${title}</b> &nbsp;&middot;&nbsp; ${today} &nbsp;&middot;&nbsp; Modo: ${modeLabel} &nbsp;&middot;&nbsp; ${chatMessages.length} mensajes</p>
<hr/>${rows}</body></html>`;
      const blob = new Blob([html], { type: 'text/html;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const win = window.open(url, '_blank');
      if (win) { win.onload = () => { win.print(); URL.revokeObjectURL(url); }; }
    }
  };

  return (
    <aside className="w-80 border-l border-border bg-card flex flex-col h-full shrink-0">
      {/* Header */}
      <div className="p-4 border-b border-border flex items-center justify-between gap-2">
        <h2 className="panel-header truncate">
          {chatMode === 'multi'
            ? `Todas las historias (${allPatientIds?.length})`
            : chatMode === 'rag'
            ? `RAG — ${patientLabel}`
            : `Chat — ${patientLabel}`}
        </h2>
        <div className="flex items-center gap-1 shrink-0">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                className="text-muted-foreground hover:text-foreground"
                title="Exportar log de chat"
                disabled={messages.filter(m => m.role === 'user' || m.role === 'assistant').length === 0}
              >
                <Download className="h-4 w-4" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => exportChat('txt')}>
                <FileText className="h-3.5 w-3.5 mr-2" />Exportar TXT
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => exportChat('pdf')}>
                <FileText className="h-3.5 w-3.5 mr-2" />Exportar PDF
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
            <X className="h-4 w-4" />
          </button>
        </div>
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
              title="Chat sobre múltiples pacientes"
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
          {!sessionId && <span className="text-red-600"> ⚠️ Extrae el texto primero.</span>}
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
              {/* Referencias modo clásico */}
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
                        pág. {page}
                      </button>
                    ) : (
                      <span key={page} className="text-xs bg-blue-100 text-blue-700 rounded px-2 py-0.5 font-medium font-body">
                        pág. {page}
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
                            pág. {r.page_number}
                          </button>
                        ) : (
                          <span className="text-blue-700 font-medium">pág. {r.page_number}</span>
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
