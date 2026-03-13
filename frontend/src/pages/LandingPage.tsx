import { useNavigate } from 'react-router-dom';
import { 
  Shield, FileSearch, BarChart3, Clock, ArrowRight, 
  AlertCircle, TrendingUp, CheckCircle, Upload, 
  Brain, FileText, DollarSign, Mail, Phone, MapPin,
  Target, Zap, Users, Award
} from 'lucide-react';

const LandingPage = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-background">
      {/* Nav */}
      <nav className="border-b border-border bg-card sticky top-0 z-50 backdrop-blur-sm bg-card/95">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <img src="/logo.png" alt="AudiMedIA logo" className="h-8 w-8 object-contain" />
            <h1 className="font-display text-xl font-bold text-foreground">AudiMedIA</h1>
          </div>
          <button
            onClick={() => navigate('/auth')}
            className="font-body text-sm bg-primary text-primary-foreground px-5 py-2.5 rounded-md hover:opacity-90 transition-opacity"
          >
            Iniciar sesión
          </button>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="max-w-6xl mx-auto px-6 py-24">
        <div className="text-center max-w-3xl mx-auto">
          <div className="inline-block mb-4">
            <span className="data-label px-4 py-1.5 bg-primary/10 text-primary rounded-full">
              Auditoría Médica Concurrente con IA
            </span>
          </div>
          <h1 className="font-display text-5xl md:text-6xl font-bold text-foreground leading-tight mb-6">
            Transforme su auditoría médica con inteligencia artificial
          </h1>
          <p className="font-body text-xl text-muted-foreground mb-10 leading-relaxed">
            Reduzca hasta un <strong className="text-foreground">80% las glosas</strong>, detecte estancias prolongadas 
            y mejore la calidad documental en tiempo real. Análisis automatizado para instituciones de salud en Colombia.
          </p>
          <div className="flex gap-4 justify-center flex-wrap">
            <button
              onClick={() => navigate('/auth')}
              className="font-body text-base bg-primary text-primary-foreground px-8 py-4 rounded-lg hover:opacity-90 transition-opacity flex items-center gap-2 shadow-lg"
            >
              Solicitar demostración <ArrowRight className="h-5 w-5" />
            </button>
            <button
              onClick={() => document.getElementById('como-funciona')?.scrollIntoView({ behavior: 'smooth' })}
              className="font-body text-base border-2 border-border px-8 py-4 rounded-lg hover:bg-accent transition-colors"
            >
              Ver cómo funciona
            </button>
          </div>
        </div>
      </section>

      {/* Métricas Destacadas */}
      <section className="border-y border-border bg-card">
        <div className="max-w-6xl mx-auto px-6 py-16">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {[
              { value: '80%', label: 'Reducción de glosas', icon: TrendingUp },
              { value: '< 3 min', label: 'Análisis por historia', icon: Clock },
              { value: '24/7', label: 'Auditoría continua', icon: Shield },
              { value: '5+', label: 'Historias simultáneas', icon: FileText },
            ].map((stat) => (
              <div key={stat.label} className="text-center">
                <stat.icon className="h-8 w-8 text-primary mx-auto mb-3" />
                <p className="font-display text-3xl font-bold text-foreground mb-1">{stat.value}</p>
                <p className="font-body text-sm text-muted-foreground">{stat.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* El Problema */}
      <section className="max-w-6xl mx-auto px-6 py-20">
        <div className="text-center mb-12">
          <h2 className="font-display text-4xl font-bold text-foreground mb-4">
            El desafío de la auditoría médica tradicional
          </h2>
          <p className="font-body text-lg text-muted-foreground max-w-2xl mx-auto">
            Las instituciones de salud en Colombia enfrentan pérdidas millonarias por glosas y problemas documentales
          </p>
        </div>
        
        <div className="grid md:grid-cols-3 gap-6">
          {[
            {
              icon: AlertCircle,
              title: 'Glosas en aumento',
              description: 'Las EPS rechazan pagos por falta de documentación completa, evoluciones faltantes o codificación incorrecta.',
              impact: 'Hasta $500M anuales en pérdidas',
              color: 'text-red-500'
            },
            {
              icon: Clock,
              title: 'Estancias prolongadas',
              description: 'Pacientes permanecen más días de lo necesario sin detección oportuna, generando costos evitables.',
              impact: 'Promedio 2-3 días extras por paciente',
              color: 'text-orange-500'
            },
            {
              icon: FileText,
              title: 'Errores documentales',
              description: 'Auditoría manual tardía detecta problemas cuando ya está facturado, sin posibilidad de corrección.',
              impact: '60% de glosas evitables',
              color: 'text-yellow-500'
            }
          ].map((problem) => (
            <div key={problem.title} className="border border-border rounded-lg p-6 bg-card hover:shadow-lg transition-shadow">
              <problem.icon className={`h-12 w-12 ${problem.color} mb-4`} />
              <h3 className="font-display text-xl font-semibold text-foreground mb-3">{problem.title}</h3>
              <p className="font-body text-sm text-muted-foreground mb-4 leading-relaxed">{problem.description}</p>
              <div className="pt-4 border-t border-border">
                <p className="font-body text-xs font-semibold text-destructive">{problem.impact}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* La Solución */}
      <section className="bg-primary/5 border-y border-border py-20">
        <div className="max-w-6xl mx-auto px-6">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div>
              <div className="inline-block mb-4">
                <span className="data-label px-4 py-1.5 bg-primary text-primary-foreground rounded-full">
                  La Solución
                </span>
              </div>
              <h2 className="font-display text-4xl font-bold text-foreground mb-6">
                Auditoría concurrente automatizada con IA
              </h2>
              <p className="font-body text-lg text-muted-foreground mb-6 leading-relaxed">
                AudiMedIA analiza historias clínicas <strong className="text-foreground">mientras el paciente aún está hospitalizado</strong>, 
                detectando problemas en tiempo real para corregirlos antes de la facturación.
              </p>
              <ul className="space-y-4">
                {[
                  'Extracción inteligente de datos clínicos con GPT-4',
                  'Detección automática de glosas potenciales',
                  'Validación de pertinencia CIE-10 y CUPS',
                  'Alertas tempranas al equipo médico',
                  'Dashboard financiero en tiempo real'
                ].map((item) => (
                  <li key={item} className="flex items-start gap-3">
                    <CheckCircle className="h-6 w-6 text-green-500 flex-shrink-0 mt-0.5" />
                    <span className="font-body text-muted-foreground">{item}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="bg-card border border-border rounded-xl p-8 shadow-xl">
              <div className="space-y-6">
                <div className="flex items-center gap-4">
                  <div className="bg-primary/10 p-3 rounded-lg">
                    <Upload className="h-6 w-6 text-primary" />
                  </div>
                  <div>
                    <p className="font-display text-sm font-semibold text-foreground">Carga la historia clínica</p>
                    <p className="font-body text-xs text-muted-foreground">PDF con anonimización automática</p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="bg-primary/10 p-3 rounded-lg">
                    <Brain className="h-6 w-6 text-primary" />
                  </div>
                  <div>
                    <p className="font-display text-sm font-semibold text-foreground">IA analiza en menos de 3 minutos</p>
                    <p className="font-body text-xs text-muted-foreground">Extracción + validación + detección</p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="bg-primary/10 p-3 rounded-lg">
                    <AlertCircle className="h-6 w-6 text-primary" />
                  </div>
                  <div>
                    <p className="font-display text-sm font-semibold text-foreground">Recibe alertas inmediatas</p>
                    <p className="font-body text-xs text-muted-foreground">Pendientes clasificados por riesgo</p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="bg-primary/10 p-3 rounded-lg">
                    <DollarSign className="h-6 w-6 text-primary" />
                  </div>
                  <div>
                    <p className="font-display text-sm font-semibold text-foreground">Evita glosas antes de facturar</p>
                    <p className="font-body text-xs text-muted-foreground">Ahorro cuantificable mensual</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Beneficios */}
      <section className="max-w-6xl mx-auto px-6 py-20">
        <div className="text-center mb-12">
          <h2 className="font-display text-4xl font-bold text-foreground mb-4">
            Beneficios medibles para su institución
          </h2>
          <p className="font-body text-lg text-muted-foreground max-w-2xl mx-auto">
            Resultados comprobables que impactan directamente su sostenibilidad financiera
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-8">
          {[
            {
              icon: DollarSign,
              title: 'Reducción de glosas',
              metric: 'Hasta 80% menos glosas',
              benefits: [
                'Detección temprana de evoluciones faltantes',
                'Validación automática de indicaciones',
                'Verificación de soportes documentales',
                'Alertas antes de facturación'
              ],
              color: 'bg-green-500/10 text-green-600'
            },
            {
              icon: FileSearch,
              title: 'Mejora documental',
              metric: '95% de completitud',
              benefits: [
                'Identificación de gaps en tiempo real',
                'Guías de documentación completa',
                'Trazabilidad de correcciones',
                'Cumplimiento normativo automatizado'
              ],
              color: 'bg-blue-500/10 text-blue-600'
            },
            {
              icon: TrendingUp,
              title: 'Ahorro operacional',
              metric: '$200M+ anuales',
              benefits: [
                'Reducción de estancias prolongadas',
                'Optimización de recursos hospitalarios',
                'Menor carga administrativa',
                'ROI positivo desde mes 3'
              ],
              color: 'bg-purple-500/10 text-purple-600'
            }
          ].map((benefit) => (
            <div key={benefit.title} className="border border-border rounded-xl p-6 bg-card hover:shadow-xl transition-shadow">
              <div className={`${benefit.color} w-14 h-14 rounded-lg flex items-center justify-center mb-4`}>
                <benefit.icon className="h-7 w-7" />
              </div>
              <h3 className="font-display text-xl font-bold text-foreground mb-2">{benefit.title}</h3>
              <p className="font-body text-2xl font-bold text-primary mb-4">{benefit.metric}</p>
              <ul className="space-y-2">
                {benefit.benefits.map((item) => (
                  <li key={item} className="flex items-start gap-2">
                    <CheckCircle className="h-4 w-4 text-green-500 flex-shrink-0 mt-1" />
                    <span className="font-body text-sm text-muted-foreground">{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>

      {/* Cómo Funciona */}
      <section id="como-funciona" className="bg-accent/30 border-y border-border py-20">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="font-display text-4xl font-bold text-foreground mb-4">
              Cómo funciona AudiMedIA
            </h2>
            <p className="font-body text-lg text-muted-foreground max-w-2xl mx-auto">
              Un proceso sencillo y automatizado en 4 pasos
            </p>
          </div>

          <div className="grid md:grid-cols-4 gap-8">
            {[
              {
                step: '1',
                icon: Upload,
                title: 'Carga',
                description: 'Sube la historia clínica en PDF. El sistema anonimiza automáticamente los datos sensibles.',
                time: '30 seg'
              },
              {
                step: '2',
                icon: Brain,
                title: 'Análisis IA',
                description: 'GPT-4 extrae variables clínicas, valida CIE-10/CUPS y detecta inconsistencias.',
                time: '< 3 min'
              },
              {
                step: '3',
                icon: Target,
                title: 'Detección',
                description: 'Identifica glosas potenciales, estancias prolongadas y documentación faltante.',
                time: 'Instantáneo'
              },
              {
                step: '4',
                icon: BarChart3,
                title: 'Reportes',
                description: 'Dashboard con hallazgos priorizados, métricas financieras y recomendaciones.',
                time: 'Tiempo real'
              }
            ].map((step, index) => (
              <div key={step.step} className="relative">
                {index < 3 && (
                  <div className="hidden md:block absolute top-12 left-full w-full h-0.5 bg-border -translate-x-1/2 z-0" />
                )}
                <div className="relative z-10 bg-card border-2 border-border rounded-xl p-6 hover:shadow-lg transition-all hover:-translate-y-1">
                  <div className="bg-primary text-primary-foreground w-12 h-12 rounded-full flex items-center justify-center font-display text-xl font-bold mb-4">
                    {step.step}
                  </div>
                  <step.icon className="h-10 w-10 text-primary mb-4" />
                  <h3 className="font-display text-lg font-bold text-foreground mb-2">{step.title}</h3>
                  <p className="font-body text-sm text-muted-foreground mb-3 leading-relaxed">{step.description}</p>
                  <div className="pt-3 border-t border-border">
                    <span className="font-body text-xs font-semibold text-primary">{step.time}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Características del Sistema */}
      <section className="max-w-6xl mx-auto px-6 py-20">
        <div className="text-center mb-12">
          <h2 className="font-display text-4xl font-bold text-foreground mb-4">
            Capacidades del sistema
          </h2>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {[
            {
              icon: FileSearch,
              title: 'Análisis automatizado',
              description: 'Procesamiento simultáneo de hasta 5 historias clínicas con extracción de variables mediante IA.',
            },
            {
              icon: Shield,
              title: 'Detección de glosas',
              description: 'Identificación de evoluciones faltantes, medicamentos sin indicación y procedimientos sin soporte.',
            },
            {
              icon: BarChart3,
              title: 'Métricas financieras',
              description: 'Cuantificación del impacto económico: glosas evitadas, ahorro por estancia y ROI institucional.',
            },
            {
              icon: Clock,
              title: 'Auditoría incremental',
              description: 'El sistema recuerda lo auditado y procesa únicamente páginas nuevas cada día.',
            },
            {
              icon: Target,
              title: 'Validación CIE-10',
              description: 'Verificación automática de pertinencia diagnóstica según estándares internacionales.',
            },
            {
              icon: Zap,
              title: 'Alertas en tiempo real',
              description: 'Notificaciones inmediatas al equipo médico sobre pendientes de alto riesgo.',
            },
            {
              icon: Users,
              title: 'Control por roles',
              description: 'Permisos diferenciados para admin, auditores, coordinadores y equipo médico.',
            },
            {
              icon: FileText,
              title: 'Chat con historia',
              description: 'Pregunta cualquier dato de la historia clínica y recibe respuestas con referencias.',
            },
            {
              icon: Award,
              title: 'Cumplimiento normativo',
              description: 'Alineado con legislación colombiana: Ley 1438/2011, Decreto 780/2016, Res. 1995/1999.',
            }
          ].map((feature) => (
            <div key={feature.title} className="border border-border rounded-lg p-6 bg-card hover:border-primary/50 transition-colors">
              <feature.icon className="h-8 w-8 text-primary mb-4" />
              <h3 className="font-display text-base font-semibold text-foreground mb-2">{feature.title}</h3>
              <p className="font-body text-sm text-muted-foreground leading-relaxed">{feature.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA Final */}
      <section className="bg-primary text-primary-foreground py-20">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <h2 className="font-display text-4xl md:text-5xl font-bold mb-6">
            Comience a reducir glosas hoy mismo
          </h2>
          <p className="font-body text-xl opacity-90 mb-8 leading-relaxed">
            Únase a las instituciones que están transformando su auditoría médica con inteligencia artificial. 
            Sin compromiso, sin instalación compleja.
          </p>
          <div className="flex gap-4 justify-center flex-wrap">
            <button
              onClick={() => navigate('/auth')}
              className="font-body text-base bg-white text-primary px-8 py-4 rounded-lg hover:bg-gray-100 transition-colors flex items-center gap-2 shadow-lg font-semibold"
            >
              Solicitar demostración gratuita <ArrowRight className="h-5 w-5" />
            </button>
            <button
              onClick={() => window.location.href = 'mailto:contacto@audiomedia.co'}
              className="font-body text-base border-2 border-white/30 px-8 py-4 rounded-lg hover:bg-white/10 transition-colors"
            >
              Hablar con un asesor
            </button>
          </div>
          <p className="font-body text-sm opacity-75 mt-6">
            ✓ Sin tarjeta de crédito requerida  •  ✓ Implementación en 24 horas  •  ✓ Soporte técnico incluido
          </p>
        </div>
      </section>

      {/* Marco Normativo */}
      <section className="border-t border-border bg-card">
        <div className="max-w-6xl mx-auto px-6 py-12">
          <h3 className="font-display text-sm font-semibold text-foreground mb-4 text-center">
            Marco normativo colombiano aplicado
          </h3>
          <div className="flex flex-wrap justify-center gap-3">
            {[
              'Ley 1438/2011',
              'Decreto 780/2016',
              'Resolución 1995/1999',
              'CIE-10 (OMS)',
              'CUPS',
              'GPC MinSalud',
              'Ley 1712/2014 (Transparencia)',
              'Ley Estatutaria 1581/2012 (Datos)'
            ].map((norm) => (
              <span
                key={norm}
                className="font-body text-xs border border-border rounded-full px-4 py-2 text-muted-foreground bg-background hover:bg-accent transition-colors"
              >
                {norm}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* Footer Completo */}
      <footer className="border-t border-border bg-card">
        <div className="max-w-6xl mx-auto px-6 py-12">
          <div className="grid md:grid-cols-4 gap-8 mb-8">
            {/* Columna 1 - Marca */}
            <div>
              <div className="flex items-center gap-2 mb-4">
                <Shield className="h-6 w-6 text-primary" />
                <h3 className="font-display text-lg font-bold text-foreground">AudiMedIA</h3>
              </div>
              <p className="font-body text-sm text-muted-foreground leading-relaxed mb-4">
                Sistema de auditoría médica concurrente con inteligencia artificial para instituciones de salud en Colombia.
              </p>
              <div className="flex gap-3">
                {/* Aquí podrías agregar iconos de redes sociales si los tienes */}
              </div>
            </div>

            {/* Columna 2 - Producto */}
            <div>
              <h4 className="font-display text-sm font-semibold text-foreground mb-4">Producto</h4>
              <ul className="space-y-2">
                {[
                  { label: 'Características', action: () => document.getElementById('como-funciona')?.scrollIntoView({ behavior: 'smooth' }) },
                  { label: 'Beneficios', action: () => window.scrollTo({ top: 0, behavior: 'smooth' }) },
                  { label: 'Casos de uso', action: () => window.scrollTo({ top: 0, behavior: 'smooth' }) },
                  { label: 'Precios', action: () => navigate('/auth') }
                ].map((item) => (
                  <li key={item.label}>
                    <button
                      onClick={item.action}
                      className="font-body text-sm text-muted-foreground hover:text-foreground transition-colors"
                    >
                      {item.label}
                    </button>
                  </li>
                ))}
              </ul>
            </div>

            {/* Columna 3 - Recursos */}
            <div>
              <h4 className="font-display text-sm font-semibold text-foreground mb-4">Recursos</h4>
              <ul className="space-y-2">
                {[
                  'Documentación',
                  'Centro de ayuda',
                  'Blog',
                  'Normativa'
                ].map((item) => (
                  <li key={item}>
                    <button
                      onClick={() => navigate('/auth')}
                      className="font-body text-sm text-muted-foreground hover:text-foreground transition-colors"
                    >
                      {item}
                    </button>
                  </li>
                ))}
              </ul>
            </div>

            {/* Columna 4 - Contacto */}
            <div>
              <h4 className="font-display text-sm font-semibold text-foreground mb-4">Contacto</h4>
              <ul className="space-y-3">
                <li className="flex items-start gap-2">
                  <Mail className="h-4 w-4 text-muted-foreground mt-0.5 flex-shrink-0" />
                  <a
                    href="mailto:contacto@audiomedia.co"
                    className="font-body text-sm text-muted-foreground hover:text-foreground transition-colors"
                  >
                    contacto@audiomedia.co
                  </a>
                </li>
                <li className="flex items-start gap-2">
                  <Phone className="h-4 w-4 text-muted-foreground mt-0.5 flex-shrink-0" />
                  <a
                    href="tel:+5716012345"
                    className="font-body text-sm text-muted-foreground hover:text-foreground transition-colors"
                  >
                    +57 (601) 234 5678
                  </a>
                </li>
                <li className="flex items-start gap-2">
                  <MapPin className="h-4 w-4 text-muted-foreground mt-0.5 flex-shrink-0" />
                  <span className="font-body text-sm text-muted-foreground">
                    Bogotá, Colombia
                  </span>
                </li>
              </ul>
            </div>
          </div>

          {/* Línea divisoria */}
          <div className="border-t border-border pt-8">
            <div className="flex flex-col md:flex-row justify-between items-center gap-4">
              <p className="font-body text-xs text-muted-foreground text-center md:text-left">
                © 2026 NeoMedic S.A.S. Todos los derechos reservados.
              </p>
              <div className="flex gap-6">
                <button
                  onClick={() => navigate('/auth')}
                  className="font-body text-xs text-muted-foreground hover:text-foreground transition-colors"
                >
                  Política de privacidad
                </button>
                <button
                  onClick={() => navigate('/auth')}
                  className="font-body text-xs text-muted-foreground hover:text-foreground transition-colors"
                >
                  Términos de servicio
                </button>
                <button
                  onClick={() => navigate('/auth')}
                  className="font-body text-xs text-muted-foreground hover:text-foreground transition-colors"
                >
                  Tratamiento de datos
                </button>
              </div>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
