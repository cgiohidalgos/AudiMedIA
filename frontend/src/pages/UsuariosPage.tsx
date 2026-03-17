import { useState, useEffect, useMemo } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import AppNavbar from '@/components/AppNavbar';
import UserModal from '@/components/UserModal';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  Plus,
  Search,
  MoreHorizontal,
  Pencil,
  Trash2,
  KeyRound,
  UserCheck,
  UserX,
  Users,
} from 'lucide-react';
import { toast } from 'sonner';
import { usersApi, type ApiUser, type AppRole } from '@/lib/api';

// ─── helpers ─────────────────────────────────────────────────────────────────

const ROLE_LABELS: Record<AppRole, string> = {
  admin: 'Administrador',
  auditor: 'Auditor',
  coordinador: 'Coordinador',
  equipo_medico: 'Equipo Médico',
};

const ROLE_COLORS: Record<AppRole, string> = {
  admin: 'bg-violet-500/15 text-violet-600 border-violet-200',
  auditor: 'bg-blue-500/15 text-blue-600 border-blue-200',
  coordinador: 'bg-emerald-500/15 text-emerald-600 border-emerald-200',
  equipo_medico: 'bg-amber-500/15 text-amber-600 border-amber-200',
};

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('es-CO', {
    day: '2-digit',
    month: '2-digit',
    year: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

type ModalMode = 'create' | 'edit' | 'reset-password';

// ─── Page ─────────────────────────────────────────────────────────────────────

const UsuariosPage = () => {
  const { role, user: currentUser } = useAuth();
  const navigate = useNavigate();

  const [users, setUsers] = useState<ApiUser[]>([]);
  const [loading, setLoading] = useState(true);

  // Filters
  const [search, setSearch] = useState('');
  const [filterRole, setFilterRole] = useState<AppRole | 'all'>('all');
  const [filterStatus, setFilterStatus] = useState<'all' | 'active' | 'inactive'>('all');

  // Modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState<ModalMode>('create');
  const [selectedUser, setSelectedUser] = useState<ApiUser | null>(null);

  // Delete confirmation
  const [deleteUser, setDeleteUser] = useState<ApiUser | null>(null);
  const [deleting, setDeleting] = useState(false);

  // Redirect non-admins
  useEffect(() => {
    if (role && role !== 'admin') {
      navigate('/app', { replace: true });
    }
  }, [role, navigate]);

  const load = async () => {
    try {
      const data = await usersApi.list();
      setUsers(data);
    } catch {
      toast.error('No se pudieron cargar los usuarios');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  // Filtered list
  const filtered = useMemo(() => {
    return users.filter(u => {
      const matchSearch =
        !search ||
        u.full_name.toLowerCase().includes(search.toLowerCase()) ||
        u.email.toLowerCase().includes(search.toLowerCase());
      const matchRole = filterRole === 'all' || u.role === filterRole;
      const matchStatus =
        filterStatus === 'all' ||
        (filterStatus === 'active' && u.is_active) ||
        (filterStatus === 'inactive' && !u.is_active);
      return matchSearch && matchRole && matchStatus;
    });
  }, [users, search, filterRole, filterStatus]);

  // Actions
  const openCreate = () => {
    setSelectedUser(null);
    setModalMode('create');
    setModalOpen(true);
  };

  const openEdit = (u: ApiUser) => {
    setSelectedUser(u);
    setModalMode('edit');
    setModalOpen(true);
  };

  const openResetPassword = (u: ApiUser) => {
    setSelectedUser(u);
    setModalMode('reset-password');
    setModalOpen(true);
  };

  const handleToggleActive = async (u: ApiUser) => {
    try {
      await usersApi.update(u.id, { is_active: !u.is_active });
      toast.success(u.is_active ? 'Usuario desactivado' : 'Usuario activado');
      load();
    } catch {
      toast.error('Error al actualizar el estado del usuario');
    }
  };

  const handleDelete = async () => {
    if (!deleteUser) return;
    setDeleting(true);
    try {
      await usersApi.delete(deleteUser.id);
      toast.success('Usuario eliminado');
      setDeleteUser(null);
      load();
    } catch (err: any) {
      toast.error(err?.message ?? 'Error al eliminar el usuario');
    } finally {
      setDeleting(false);
    }
  };

  const stats = useMemo(() => ({
    total: users.length,
    active: users.filter(u => u.is_active).length,
    inactive: users.filter(u => !u.is_active).length,
  }), [users]);

  return (
    <div className="flex flex-col h-screen bg-background">
      <AppNavbar title="Gestión de Usuarios" />

      <div className="flex-1 overflow-y-auto">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">

          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-xl font-semibold text-foreground">Gestión de Usuarios</h1>
              <p className="text-sm text-muted-foreground mt-1">
                {stats.total} usuarios · {stats.active} activos · {stats.inactive} inactivos
              </p>
            </div>
            <Button onClick={openCreate}>
              <Plus className="h-4 w-4 mr-2" />
              Nuevo usuario
            </Button>
          </div>

          {/* Stats cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
            {(Object.keys(ROLE_LABELS) as AppRole[]).map(r => {
              const count = users.filter(u => u.role === r).length;
              return (
                <Card key={r} className="border">
                  <CardContent className="p-4">
                    <p className="text-xs text-muted-foreground mb-1">{ROLE_LABELS[r]}</p>
                    <p className="text-2xl font-bold">{count}</p>
                  </CardContent>
                </Card>
              );
            })}
          </div>

          {/* Filters */}
          <div className="flex flex-col sm:flex-row gap-3 mb-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                className="pl-9"
                placeholder="Buscar por nombre o email…"
                value={search}
                onChange={e => setSearch(e.target.value)}
              />
            </div>
            <Select value={filterRole} onValueChange={v => setFilterRole(v as AppRole | 'all')}>
              <SelectTrigger className="w-full sm:w-44">
                <SelectValue placeholder="Todos los roles" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos los roles</SelectItem>
                {(Object.keys(ROLE_LABELS) as AppRole[]).map(r => (
                  <SelectItem key={r} value={r}>{ROLE_LABELS[r]}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={filterStatus} onValueChange={v => setFilterStatus(v as 'all' | 'active' | 'inactive')}>
              <SelectTrigger className="w-full sm:w-36">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos</SelectItem>
                <SelectItem value="active">Activos</SelectItem>
                <SelectItem value="inactive">Inactivos</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Table */}
          <Card>
            <CardContent className="p-0">
              {loading ? (
                <div className="py-16 text-center text-sm text-muted-foreground">
                  Cargando usuarios…
                </div>
              ) : filtered.length === 0 ? (
                <div className="py-16 text-center text-sm text-muted-foreground flex flex-col items-center gap-2">
                  <Users className="h-8 w-8 opacity-30" />
                  <span>No se encontraron usuarios</span>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Nombre</TableHead>
                      <TableHead>Email</TableHead>
                      <TableHead>Rol</TableHead>
                      <TableHead>Estado</TableHead>
                      <TableHead>Último acceso</TableHead>
                      <TableHead className="text-right">Acciones</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filtered.map(u => (
                      <TableRow key={u.id} className={!u.is_active ? 'opacity-60' : ''}>
                        <TableCell className="font-medium">
                          {u.full_name}
                          {u.id === currentUser?.id && (
                            <span className="ml-2 text-xs text-muted-foreground">(tú)</span>
                          )}
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">{u.email}</TableCell>
                        <TableCell>
                          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${ROLE_COLORS[u.role]}`}>
                            {ROLE_LABELS[u.role]}
                          </span>
                        </TableCell>
                        <TableCell>
                          <Badge variant={u.is_active ? 'default' : 'secondary'}>
                            {u.is_active ? 'Activo' : 'Inactivo'}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {formatDate(u.updated_at)}
                        </TableCell>
                        <TableCell className="text-right">
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="icon" className="h-7 w-7">
                                <MoreHorizontal className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuItem onClick={() => openEdit(u)}>
                                <Pencil className="h-3.5 w-3.5 mr-2" />
                                Editar
                              </DropdownMenuItem>
                              <DropdownMenuItem onClick={() => openResetPassword(u)}>
                                <KeyRound className="h-3.5 w-3.5 mr-2" />
                                Resetear contraseña
                              </DropdownMenuItem>
                              <DropdownMenuSeparator />
                              <DropdownMenuItem
                                onClick={() => handleToggleActive(u)}
                                disabled={u.id === currentUser?.id}
                              >
                                {u.is_active ? (
                                  <><UserX className="h-3.5 w-3.5 mr-2" />Desactivar</>
                                ) : (
                                  <><UserCheck className="h-3.5 w-3.5 mr-2" />Activar</>
                                )}
                              </DropdownMenuItem>
                              <DropdownMenuItem
                                className="text-destructive focus:text-destructive"
                                onClick={() => setDeleteUser(u)}
                                disabled={u.id === currentUser?.id}
                              >
                                <Trash2 className="h-3.5 w-3.5 mr-2" />
                                Eliminar
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>

          {filtered.length > 0 && (
            <p className="text-xs text-muted-foreground mt-3 text-right">
              Mostrando {filtered.length} de {users.length} usuarios
            </p>
          )}
        </div>
      </div>

      {/* Create / Edit / Reset-password modal */}
      <UserModal
        mode={modalMode}
        user={selectedUser}
        open={modalOpen}
        onOpenChange={setModalOpen}
        onSuccess={load}
      />

      {/* Delete confirmation */}
      <Dialog open={!!deleteUser} onOpenChange={open => !open && setDeleteUser(null)}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>¿Eliminar usuario?</DialogTitle>
            <DialogDescription>
              Se eliminará permanentemente la cuenta de{' '}
              <strong>{deleteUser?.full_name}</strong>. Esta acción no puede deshacerse.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteUser(null)}>
              Cancelar
            </Button>
            <Button variant="destructive" onClick={handleDelete} disabled={deleting}>
              {deleting ? 'Eliminando…' : 'Eliminar'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default UsuariosPage;
