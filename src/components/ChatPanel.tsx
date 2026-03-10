import { useState } from 'react';
import { X, Send } from 'lucide-react';

interface ChatPanelProps {
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

const ChatPanel = ({ patientLabel, onClose }: ChatPanelProps) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: 'assistant', content: `Chat activo para ${patientLabel}. Puede consultar cualquier aspecto de la historia clínica. Las respuestas incluirán referencia a la página del documento fuente.\n\nEsta respuesta es generada por IA como apoyo al criterio del auditor y no reemplaza la revisión clínica profesional.` },
  ]);
  const [input, setInput] = useState('');

  const sendMessage = (text: string) => {
    if (!text.trim()) return;
    const userMsg: ChatMessage = { role: 'user', content: text };
    const mockResponse: ChatMessage = {
      role: 'assistant',
      content: `Con base en la ${patientLabel}, se encontró información relevante. La evolución médica del día 06/03 documenta mejoría clínica parcial (página 18). Se recomienda verificar con el equipo tratante.\n\nEsta respuesta es generada por IA como apoyo al criterio del auditor y no reemplaza la revisión clínica profesional.`,
    };
    setMessages(prev => [...prev, userMsg, mockResponse]);
    setInput('');
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
        {messages.map((m, i) => (
          <div key={i} className={`${m.role === 'user' ? 'ml-8' : 'mr-4'}`}>
            <div className={`rounded-md p-3 text-sm font-body ${
              m.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-secondary text-foreground'
            }`}>
              {m.content}
            </div>
          </div>
        ))}
      </div>

      {/* Input */}
      <div className="p-3 border-t border-border flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && sendMessage(input)}
          placeholder="Escriba su pregunta..."
          className="flex-1 font-body text-sm bg-background border border-input rounded-md px-3 py-2 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
        />
        <button
          onClick={() => sendMessage(input)}
          className="bg-primary text-primary-foreground rounded-md p-2 hover:opacity-90 transition-opacity"
        >
          <Send className="h-4 w-4" />
        </button>
      </div>
    </aside>
  );
};

export default ChatPanel;
