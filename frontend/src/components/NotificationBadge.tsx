import { useState, useEffect, useCallback } from 'react';
import { Bell, CheckCheck, Trash2, ExternalLink } from 'lucide-react';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { Button } from '@/components/ui/button';
import { notificationsApi, type AppNotification } from '@/lib/api';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';

const POLL_INTERVAL_MS = 30_000; // poll unread count every 30 s

function timeAgo(isoDate: string): string {
  const diff = Date.now() - new Date(isoDate).getTime();
  const m = Math.floor(diff / 60_000);
  if (m < 1) return 'ahora mismo';
  if (m < 60) return `hace ${m} min`;
  const h = Math.floor(m / 60);
  if (h < 24) return `hace ${h} h`;
  const d = Math.floor(h / 24);
  return `hace ${d} día${d !== 1 ? 's' : ''}`;
}

const tipoBadge: Record<string, string> = {
  pendientes: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  glosa_alta: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  info: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
};

export default function NotificationBadge() {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [unread, setUnread] = useState(0);
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [loading, setLoading] = useState(false);

  // poll unread count in background
  const fetchCount = useCallback(async () => {
    try {
      const { no_leidas } = await notificationsApi.count();
      setUnread(no_leidas);
    } catch {
      // silently ignore polling errors
    }
  }, []);

  useEffect(() => {
    fetchCount();
    const id = setInterval(fetchCount, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [fetchCount]);

  // load full list when panel opens
  useEffect(() => {
    if (!open) return;
    setLoading(true);
    notificationsApi
      .list()
      .then(data => {
        setNotifications(data);
        setUnread(data.filter(n => !n.leida).length);
      })
      .catch(() => toast.error('No se pudieron cargar las notificaciones'))
      .finally(() => setLoading(false));
  }, [open]);

  const handleMarkRead = async (notif: AppNotification) => {
    if (notif.leida) return;
    try {
      const updated = await notificationsApi.markRead(notif.id);
      setNotifications(prev => prev.map(n => (n.id === updated.id ? updated : n)));
      setUnread(prev => Math.max(0, prev - 1));
    } catch {
      toast.error('Error al marcar como leída');
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await notificationsApi.markAllRead();
      setNotifications(prev => prev.map(n => ({ ...n, leida: true })));
      setUnread(0);
    } catch {
      toast.error('Error al marcar todas como leídas');
    }
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await notificationsApi.delete(id);
      setNotifications(prev => {
        const updated = prev.filter(n => n.id !== id);
        setUnread(updated.filter(n => !n.leida).length);
        return updated;
      });
    } catch {
      toast.error('Error al eliminar notificación');
    }
  };

  const handleNavigate = (notif: AppNotification) => {
    handleMarkRead(notif);
    if (notif.patient_id) {
      setOpen(false);
      navigate(`/reporte/${notif.patient_id}`);
    }
  };

  const unreadList = notifications.filter(n => !n.leida);
  const readList = notifications.filter(n => n.leida);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          className="relative p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
          aria-label="Notificaciones"
        >
          <Bell className="h-4 w-4" />
          {unread > 0 && (
            <span className="absolute -top-0.5 -right-0.5 flex items-center justify-center min-w-[14px] h-[14px] px-[3px] rounded-full bg-red-500 text-[9px] font-bold text-white leading-none">
              {unread > 99 ? '99+' : unread}
            </span>
          )}
        </button>
      </PopoverTrigger>

      <PopoverContent
        align="end"
        sideOffset={8}
        className="w-[22rem] p-0 overflow-hidden rounded-xl border border-border shadow-xl"
      >
        {/* Header */}
        <div className="flex items-center gap-2 px-4 py-3 border-b border-border bg-muted/40">
          <Bell className="h-4 w-4 text-muted-foreground shrink-0" />
          <span className="text-sm font-semibold text-foreground flex-1">Notificaciones</span>
          {unread > 0 && (
            <span className="text-xs text-muted-foreground">{unread} sin leer</span>
          )}
          {unread > 0 && (
            <button
              onClick={handleMarkAllRead}
              className="ml-1 p-1 rounded hover:bg-secondary transition-colors"
              title="Marcar todas como leídas"
            >
              <CheckCheck className="h-3.5 w-3.5 text-muted-foreground hover:text-foreground" />
            </button>
          )}
        </div>

        {/* Body */}
        <div className="max-h-[22rem] overflow-y-auto divide-y divide-border">
          {loading && (
            <div className="py-8 text-center text-xs text-muted-foreground">Cargando...</div>
          )}

          {!loading && notifications.length === 0 && (
            <div className="py-10 text-center text-xs text-muted-foreground">
              <Bell className="h-8 w-8 mx-auto mb-2 opacity-20" />
              <p>Sin notificaciones</p>
            </div>
          )}

          {!loading && unreadList.length > 0 && (
            <>
              <p className="px-3 py-1.5 text-[10px] font-semibold text-muted-foreground/60 uppercase tracking-widest bg-muted/20">
                Sin leer
              </p>
              {unreadList.map(n => (
                <NotifRow
                  key={n.id}
                  notif={n}
                  onNavigate={handleNavigate}
                  onDelete={handleDelete}
                />
              ))}
            </>
          )}

          {!loading && readList.length > 0 && (
            <>
              <p className="px-3 py-1.5 text-[10px] font-semibold text-muted-foreground/60 uppercase tracking-widest bg-muted/20">
                Leídas
              </p>
              {readList.map(n => (
                <NotifRow
                  key={n.id}
                  notif={n}
                  onNavigate={handleNavigate}
                  onDelete={handleDelete}
                />
              ))}
            </>
          )}
        </div>
      </PopoverContent>
    </Popover>
  );
}

interface NotifRowProps {
  notif: AppNotification;
  onNavigate: (n: AppNotification) => void;
  onDelete: (id: string, e: React.MouseEvent) => void;
}

function NotifRow({ notif, onNavigate, onDelete }: NotifRowProps) {
  const badgeClass =
    tipoBadge[notif.tipo] ??
    'bg-secondary text-muted-foreground';

  return (
    <div
      onClick={() => onNavigate(notif)}
      className={`group flex items-start gap-3 px-4 py-3 cursor-pointer transition-colors hover:bg-secondary/50 ${
        !notif.leida ? 'bg-primary/5' : ''
      }`}
    >
      {/* unread dot */}
      <span
        className={`mt-1.5 h-2 w-2 rounded-full shrink-0 ${
          !notif.leida ? 'bg-primary' : 'bg-transparent'
        }`}
      />

      <div className="flex-1 min-w-0">
        <div className="flex items-start gap-1.5 justify-between">
          <p className="text-xs font-medium text-foreground truncate flex-1">
            {notif.titulo}
          </p>
          <button
            onClick={e => onDelete(notif.id, e)}
            className="p-0.5 rounded opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
            title="Eliminar"
          >
            <Trash2 className="h-3 w-3 text-muted-foreground hover:text-destructive" />
          </button>
        </div>
        <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{notif.mensaje}</p>
        <div className="flex items-center gap-2 mt-1.5">
          <span
            className={`inline-block px-1.5 py-0.5 rounded text-[9px] font-semibold uppercase tracking-wide ${badgeClass}`}
          >
            {notif.tipo}
          </span>
          <span className="text-[10px] text-muted-foreground/60">{timeAgo(notif.created_at)}</span>
          {notif.patient_id && (
            <ExternalLink className="h-3 w-3 text-muted-foreground/40 ml-auto shrink-0" />
          )}
        </div>
      </div>
    </div>
  );
}
