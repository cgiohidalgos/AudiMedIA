import { useNavigate } from 'react-router-dom';
import { Shield, FileSearch, BarChart3, Clock, ArrowRight } from 'lucide-react';

const features = [
  {
    icon: FileSearch,
    title: 'Análisis automatizado',
    desc: 'Procesamiento simultáneo de hasta 5 historias clínicas con extracción de variables clínicas mediante IA.',
  },
  {
    icon: Shield,
    title: 'Detección de glosas',
    desc: 'Identificación de evoluciones faltantes, medicamentos sin indicación y procedimientos sin soporte documental.',
  },
  {
    icon: BarChart3,
    title: 'Métricas financieras',
    desc: 'Cuantificación del impacto económico: glosas evitadas, ahorro por estancia y ROI institucional.',
  },
  {
    icon: Clock,
    title: 'Auditoría incremental',
    desc: 'Continuidad entre turnos: el sistema recuerda lo auditado y procesa únicamente lo nuevo cada día.',
  },
];

const LandingPage = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-background">
      {/* Nav */}
      <nav className="border-b border-border bg-card">
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
          <h1 className="font-display text-lg font-bold text-foreground">Audi Med IA</h1>
          <button
            onClick={() => navigate('/auth')}
            className="font-body text-sm bg-primary text-primary-foreground px-4 py-2 rounded-md hover:opacity-90 transition-opacity"
          >
            Iniciar sesión
          </button>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-6xl mx-auto px-6 py-20">
        <div className="max-w-2xl">
          <p className="data-label mb-3">Sistema de auditoría médica concurrente</p>
          <h2 className="font-display text-4xl font-bold text-foreground leading-tight mb-4">
            Auditoría clínica con precisión de IA
          </h2>
          <p className="font-body text-lg text-muted-foreground mb-8 leading-relaxed">
            Reduzca pérdidas por glosas, detecte estancias prolongadas e inconsistencias clínicas. 
            Análisis automatizado conforme a la normativa colombiana vigente.
          </p>
          <div className="flex gap-3">
            <button
              onClick={() => navigate('/auth')}
              className="font-body text-sm bg-primary text-primary-foreground px-6 py-3 rounded-md hover:opacity-90 transition-opacity flex items-center gap-2"
            >
              Comenzar <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="border-y border-border bg-card">
        <div className="max-w-6xl mx-auto px-6 py-12 grid grid-cols-4 gap-8">
          {[
            { value: '5', label: 'Historias simultáneas' },
            { value: '< 3 min', label: 'Tiempo por historia' },
            { value: '78%', label: 'Pendientes resueltos' },
            { value: 'CIE-10', label: 'Validación automática' },
          ].map((s) => (
            <div key={s.label} className="text-center">
              <p className="font-display text-2xl font-bold text-foreground">{s.value}</p>
              <p className="font-body text-sm text-muted-foreground mt-1">{s.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="max-w-6xl mx-auto px-6 py-16">
        <h3 className="font-display text-xl font-bold text-foreground mb-8">Capacidades del sistema</h3>
        <div className="grid grid-cols-2 gap-6">
          {features.map((f) => (
            <div key={f.title} className="border border-border rounded-md p-6 bg-card">
              <f.icon className="h-6 w-6 text-muted-foreground mb-3" />
              <h4 className="font-display text-sm font-semibold text-foreground mb-2">{f.title}</h4>
              <p className="font-body text-sm text-muted-foreground leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Normative */}
      <section className="border-t border-border bg-card">
        <div className="max-w-6xl mx-auto px-6 py-12">
          <h3 className="font-display text-sm font-semibold text-foreground mb-4">Marco normativo aplicado</h3>
          <div className="flex flex-wrap gap-3">
            {['Ley 1438/2011', 'Decreto 780/2016', 'Res. 1995/1999', 'CIE-10 (OMS)', 'CUPS', 'GPC MinSalud'].map((n) => (
              <span key={n} className="font-body text-xs border border-border rounded-full px-3 py-1.5 text-muted-foreground">
                {n}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border">
        <div className="max-w-6xl mx-auto px-6 py-6 flex justify-between items-center">
          <p className="font-body text-xs text-muted-foreground">© 2026 Audi Med IA. Todos los derechos reservados.</p>
          <p className="font-body text-xs text-muted-foreground">Sistema de auditoría médica basada en inteligencia artificial</p>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
