import { useState, useEffect, type ReactNode } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { usePermissions } from '@/components/RoleGuard';
import { useProcessing } from '@/contexts/ProcessingContext';
import NotificationBadge from '@/components/NotificationBadge';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { Progress } from '@/components/ui/progress';
import {
  Menu,
  LayoutDashboard,
  Upload,
  ClipboardList,
  BarChart3,
  LogOut,
  User,
  ChevronRight,
  BrainCircuit,
  Loader2,
  FileText,
  CheckCircle2,
  Settings,
  Users,
  Stethoscope,
  X,
} from 'lucide-react';
import { processingApi } from '@/lib/api';
import { toast } from 'sonner';

export type AppView = 'upload' | 'results' | 'control';

interface AppNavbarProps {
  /** Vista actual dentro de AppPage (solo para AppPage) */
  currentView?: AppView;
  /** Callback para cambiar de vista dentro de AppPage */
  onViewChange?: (view: AppView) => void;
  /** Título de la página (si no se pasa, se detecta por la ruta) */
  title?: string;
  /** Acciones extra en el lado derecho del navbar */
  extraActions?: ReactNode;
}

export default function AppNavbar({ currentView, onViewChange, title, extraActions }: AppNavbarProps) {
  const { user, role, signOut } = useAuth();
  const permissions = usePermissions();
  const navigate = useNavigate();
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const { activeAnalyses, progress, removeAnalysis } = useProcessing();

  // Cuando termina un análisis → ir automáticamente a "Ver análisis"
  useEffect(() => {
    const onComplete = () => navigate('/app', { state: { view: 'results' } });
    window.addEventListener('processingComplete', onComplete);
    return () => window.removeEventListener('processingComplete', onComplete);
  }, [navigate]);

  const roleLabel: Record<string, string> = {
    admin: 'Administrador',
    auditor: 'Auditor',
    coordinador: 'Coordinador',
    equipo_medico: 'Equipo Médico',
  };

  const currentPath = location.pathname;

  const pageTitle = title ?? ({
    '/app': 'Audi Med IA',
    '/control-board': 'Cuadro de Control',
    '/dashboard': 'Dashboard Financiero',
  } as Record<string, string>)[currentPath] ?? 'Audi Med IA';

  const viewLabel: Record<AppView, string> = {
    upload: 'Subir historia',
    results: 'Análisis',
    control: 'Control de sesión',
  };

  const handleNav = (path: string, view?: AppView) => {
    setOpen(false);
    if (view && onViewChange && currentPath === '/app') {
      // Estamos dentro de AppPage → cambio de vista directo
      onViewChange(view);
    } else if (view === 'upload' && path === '/app') {
      // Venimos de otra página → ir a /app con estado
      navigate(path, { state: { view: 'upload' } });
    } else {
      navigate(path);
    }
  };

  interface NavItem {
    label: string;
    icon: ReactNode;
    action: () => void;
    active: boolean;
    visible: boolean;
    description?: string;
  }

  const navItems: NavItem[] = [
    {
      label: 'Ver análisis',
      icon: <LayoutDashboard className="h-4 w-4" />,
      description: 'Historias clínicas procesadas',
      action: () => handleNav('/app', 'results'),
      active: currentPath === '/app' && currentView === 'results',
      visible: true,
    },
    {
      label: 'Subir historia',
      icon: <Upload className="h-4 w-4" />,
      description: 'Cargar nuevas historias clínicas',
      action: () => handleNav('/app', 'upload'),
      active: currentPath === '/app' && currentView === 'upload',
      visible: permissions.canUpload,
    },
    {
      label: 'Cuadro de Control',
      icon: <ClipboardList className="h-4 w-4" />,
      description: 'Tabla consolidada de auditoría',
      action: () => handleNav('/control-board'),
      active: currentPath === '/control-board',
      visible: true,
    },
    {
      label: 'Dashboard Financiero',
      icon: <BarChart3 className="h-4 w-4" />,
      description: 'Métricas de glosas y ahorro',
      action: () => handleNav('/dashboard'),
      active: currentPath === '/dashboard',
      visible: permissions.canViewDashboard,
    },
    {
      label: 'Configuración',
      icon: <Settings className="h-4 w-4" />,
      description: 'Tarifas, EPS y servicios',
      action: () => handleNav('/configuracion'),
      active: currentPath === '/configuracion',
      visible: permissions.canConfigureSystem || permissions.canViewDashboard,
    },
    {
      label: 'Usuarios',
      icon: <Users className="h-4 w-4" />,
      description: 'Administrar cuentas de usuario',
      action: () => handleNav('/usuarios'),
      active: currentPath === '/usuarios',
      visible: permissions.canManageUsers,
    },
    {
      label: 'Mis Pacientes',
      icon: <Stethoscope className="h-4 w-4" />,
      description: 'Resúmenes y alertas de auditoría',
      action: () => handleNav('/mis-pacientes'),
      active: currentPath === '/mis-pacientes',
      visible: permissions.canViewOwnPatients,
    },
  ];

  return (
    <header className="h-12 border-b border-border bg-card flex items-center px-4 justify-between shrink-0">
      {/* Izquierda: hamburger + título */}
      <div className="flex items-center gap-3">
        <Sheet open={open} onOpenChange={setOpen}>
          <SheetTrigger asChild>
            <button
              className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
              aria-label="Menú de navegación"
            >
              <Menu className="h-4 w-4" />
            </button>
          </SheetTrigger>

          <SheetContent side="left" className="w-72 p-0 flex flex-col">
            {/* Header del panel */}
            <SheetHeader className="px-4 py-4 border-b border-border shrink-0">
              <SheetTitle className="font-display text-sm font-bold text-left text-foreground">
                Audi Med IA
              </SheetTitle>
              <div className="flex items-center gap-2 mt-0.5">
                <User className="h-3 w-3 text-muted-foreground shrink-0" />
                <span className="text-xs text-muted-foreground truncate">{user?.email}</span>
              </div>
              <span className="text-xs text-muted-foreground/50 block -mt-0.5">
                {roleLabel[role ?? ''] ?? 'Usuario'}
              </span>
            </SheetHeader>

            {/* Navegación */}
            <nav className="flex-1 px-2 py-3 overflow-y-auto">
              <p className="px-3 py-1 text-[10px] font-semibold text-muted-foreground/50 uppercase tracking-widest mb-1">
                Navegación
              </p>
              {navItems.filter(i => i.visible).map(item => (
                <button
                  key={item.label}
                  onClick={item.action}
                  className={`flex items-start gap-3 px-3 py-2.5 rounded-md w-full text-left transition-colors mb-0.5 ${
                    item.active
                      ? 'bg-primary/10 text-primary'
                      : 'text-foreground hover:bg-secondary'
                  }`}
                >
                  <span className={`mt-0.5 shrink-0 ${item.active ? 'text-primary' : 'text-muted-foreground'}`}>
                    {item.icon}
                  </span>
                  <span className="flex-1 min-w-0">
                    <span className={`block text-sm ${item.active ? 'font-medium' : ''}`}>{item.label}</span>
                    {item.description && (
                      <span className="block text-xs text-muted-foreground/60 mt-0.5">{item.description}</span>
                    )}
                  </span>
                  {item.active && <ChevronRight className="h-3.5 w-3.5 mt-0.5 shrink-0" />}
                </button>
              ))}
            </nav>

            {/* Footer: cerrar sesión */}
            <div className="shrink-0 border-t border-border px-2 py-3">
              <button
                onClick={() => { setOpen(false); signOut(); }}
                className="flex items-center gap-3 px-3 py-2.5 rounded-md text-sm w-full text-left text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
              >
                <LogOut className="h-4 w-4 shrink-0" />
                <span>Cerrar sesión</span>
              </button>
            </div>
          </SheetContent>
        </Sheet>

        {/* Título + breadcrumb */}
        <div className="flex items-center gap-2">
          <span className="font-display text-sm font-bold text-foreground">{pageTitle}</span>
          {currentView && currentView !== 'results' && (
            <>
              <span className="text-muted-foreground/30 text-sm">›</span>
              <span className="text-xs text-muted-foreground font-body">{viewLabel[currentView]}</span>
            </>
          )}
        </div>
      </div>

      {/* Derecha: notificaciones + indicador de análisis en segundo plano + acciones extra */}
      <div className="flex items-center gap-2">
        <NotificationBadge />
        {activeAnalyses.length > 0 && (
          <Popover>
            <PopoverTrigger asChild>
              <button className="group flex items-center gap-2 px-3 py-1.5 rounded-full border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300 text-xs font-medium shadow-sm hover:bg-blue-100 dark:hover:bg-blue-900/50 hover:border-blue-300 dark:hover:border-blue-700 transition-all duration-150 cursor-pointer">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500" />
                </span>
                <BrainCircuit className="h-3.5 w-3.5 shrink-0" />
                {activeAnalyses.length === 1 ? (
                  <span>
                    {(() => {
                      const p = progress[activeAnalyses[0].sessionId];
                      return p && p.ai_chunks_total > 0
                        ? `${p.ai_chunks_done} / ${p.ai_chunks_total} lotes`
                        : 'Analizando...';
                    })()}
                  </span>
                ) : (
                  <span>{activeAnalyses.length} análisis activos</span>
                )}
                <Loader2 className="h-3 w-3 animate-spin shrink-0 opacity-70" />
              </button>
            </PopoverTrigger>

            <PopoverContent
              align="end"
              sideOffset={8}
              className="w-80 p-0 overflow-hidden rounded-xl border border-border shadow-xl"
            >
              {/* Header del panel */}
              <div className="flex items-center gap-2 px-4 py-3 border-b border-border bg-muted/40">
                <BrainCircuit className="h-4 w-4 text-blue-500 shrink-0" />
                <span className="text-sm font-semibold text-foreground">Análisis en proceso</span>
                <span className="ml-auto text-xs text-muted-foreground">
                  {activeAnalyses.length} en cola
                </span>
              </div>

              {/* Lista de análisis */}
              <div className="divide-y divide-border max-h-72 overflow-y-auto">
                {activeAnalyses.map((analysis, idx) => {
                  const p = progress[analysis.sessionId];
                  const done = p?.ai_chunks_done ?? 0;
                  const total = p?.ai_chunks_total ?? 0;
                  const pct = total > 0 ? Math.round((done / total) * 100) : 0;
                  const isFirst = idx === 0;

                  return (
                    <div key={analysis.sessionId} className="px-4 py-3 space-y-2">
                      {/* Fila superior: icono + nombre + badge + cancelar */}
                      <div className="flex items-center gap-2">
                        <FileText className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                        <span className="text-xs font-medium text-foreground truncate flex-1">
                          {analysis.fileName}
                        </span>
                        {isFirst ? (
                          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400 text-[10px] font-semibold uppercase tracking-wide shrink-0">
                            <Loader2 className="h-2.5 w-2.5 animate-spin" />
                            Activo
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-muted text-muted-foreground text-[10px] font-semibold uppercase tracking-wide shrink-0">
                            En cola
                          </span>
                        )}
                        <button
                          onClick={async () => {
                            try {
                              await processingApi.cancel(analysis.sessionId);
                            } catch { /* ignorar si ya terminó */ }
                            removeAnalysis(analysis.sessionId);
                            toast.info(`Análisis cancelado: ${analysis.fileName}`);
                          }}
                          className="ml-1 p-0.5 rounded hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-colors shrink-0"
                          title="Cancelar análisis"
                        >
                          <X className="h-3.5 w-3.5" />
                        </button>
                      </div>

                      {/* Barra de progreso */}
                      {isFirst && (
                        <>
                          <Progress value={pct} className="h-1.5" />
                          <div className="flex items-center justify-between">
                            <span className="text-[11px] text-muted-foreground">
                              {total > 0
                                ? `Lote ${done} de ${total}`
                                : 'Iniciando análisis...'}
                            </span>
                            {total > 0 && (
                              <span className="text-[11px] font-medium text-blue-600 dark:text-blue-400">
                                {pct}%
                              </span>
                            )}
                          </div>
                        </>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Footer */}
              <div className="px-4 py-2.5 bg-muted/30 border-t border-border flex items-center gap-1.5">
                <CheckCircle2 className="h-3 w-3 text-muted-foreground/50 shrink-0" />
                <span className="text-[11px] text-muted-foreground/70">
                  Puedes navegar con libertad. Te avisaremos al terminar.
                </span>
              </div>
            </PopoverContent>
          </Popover>
        )}
        {extraActions}
      </div>
    </header>
  );
}
