import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { toast } from 'sonner';
import { usersApi, type ApiUser, type AppRole, type UserCreatePayload } from '@/lib/api';

type Mode = 'create' | 'edit' | 'reset-password';

interface UserModalProps {
  mode: Mode;
  user?: ApiUser | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

const ROLE_LABELS: Record<AppRole, string> = {
  admin: 'Administrador',
  auditor: 'Auditor',
  coordinador: 'Coordinador',
  equipo_medico: 'Equipo Médico',
};

export default function UserModal({ mode, user, open, onOpenChange, onSuccess }: UserModalProps) {
  const [form, setForm] = useState({
    full_name: '',
    email: '',
    role: 'auditor' as AppRole,
    password: '',
    confirmPassword: '',
    is_active: true,
  });
  const [saving, setSaving] = useState(false);

  // Populate form when editing
  useEffect(() => {
    if (mode === 'edit' && user) {
      setForm(f => ({
        ...f,
        full_name: user.full_name,
        email: user.email,
        role: user.role,
        is_active: user.is_active,
        password: '',
        confirmPassword: '',
      }));
    } else if (mode === 'create') {
      setForm({ full_name: '', email: '', role: 'auditor', password: '', confirmPassword: '', is_active: true });
    } else if (mode === 'reset-password') {
      setForm(f => ({ ...f, password: '', confirmPassword: '' }));
    }
  }, [mode, user, open]);

  const handleSubmit = async () => {
    if (mode === 'create') {
      if (!form.full_name.trim() || !form.email.trim()) {
        toast.error('Nombre y email son requeridos');
        return;
      }
      if (form.password.length < 8) {
        toast.error('La contraseña debe tener mínimo 8 caracteres');
        return;
      }
      if (form.password !== form.confirmPassword) {
        toast.error('Las contraseñas no coinciden');
        return;
      }
      setSaving(true);
      try {
        const payload: UserCreatePayload = {
          email: form.email,
          full_name: form.full_name,
          role: form.role,
          password: form.password,
        };
        await usersApi.create(payload);
        toast.success('Usuario creado correctamente');
        onOpenChange(false);
        onSuccess();
      } catch (err: any) {
        toast.error(err?.message ?? 'Error al crear el usuario');
      } finally {
        setSaving(false);
      }
    } else if (mode === 'edit' && user) {
      if (!form.full_name.trim()) {
        toast.error('El nombre es requerido');
        return;
      }
      setSaving(true);
      try {
        await usersApi.update(user.id, {
          full_name: form.full_name,
          role: form.role,
          is_active: form.is_active,
        });
        toast.success('Usuario actualizado');
        onOpenChange(false);
        onSuccess();
      } catch (err: any) {
        toast.error(err?.message ?? 'Error al actualizar el usuario');
      } finally {
        setSaving(false);
      }
    } else if (mode === 'reset-password' && user) {
      if (form.password.length < 8) {
        toast.error('La contraseña debe tener mínimo 8 caracteres');
        return;
      }
      if (form.password !== form.confirmPassword) {
        toast.error('Las contraseñas no coinciden');
        return;
      }
      setSaving(true);
      try {
        await usersApi.resetPassword(user.id, form.password);
        toast.success('Contraseña actualizada');
        onOpenChange(false);
        onSuccess();
      } catch (err: any) {
        toast.error(err?.message ?? 'Error al resetear la contraseña');
      } finally {
        setSaving(false);
      }
    }
  };

  const title = {
    create: 'Nuevo usuario',
    edit: 'Editar usuario',
    'reset-password': 'Resetear contraseña',
  }[mode];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          {mode === 'reset-password' && user && (
            <DialogDescription>
              Nueva contraseña para <strong>{user.full_name}</strong>
            </DialogDescription>
          )}
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Campos de creación / edición */}
          {(mode === 'create' || mode === 'edit') && (
            <>
              <div className="space-y-1.5">
                <Label>Nombre completo *</Label>
                <Input
                  value={form.full_name}
                  onChange={e => setForm(f => ({ ...f, full_name: e.target.value }))}
                  placeholder="Juan Pérez"
                />
              </div>

              <div className="space-y-1.5">
                <Label>Email *</Label>
                <Input
                  type="email"
                  value={form.email}
                  onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                  placeholder="usuario@hospital.com"
                  disabled={mode === 'edit'}
                />
                {mode === 'edit' && (
                  <p className="text-xs text-muted-foreground">El email no puede modificarse</p>
                )}
              </div>

              <div className="space-y-1.5">
                <Label>Rol</Label>
                <Select
                  value={form.role}
                  onValueChange={v => setForm(f => ({ ...f, role: v as AppRole }))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {(Object.keys(ROLE_LABELS) as AppRole[]).map(r => (
                      <SelectItem key={r} value={r}>{ROLE_LABELS[r]}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {mode === 'edit' && (
                <div className="flex items-center gap-3">
                  <Switch
                    checked={form.is_active}
                    onCheckedChange={v => setForm(f => ({ ...f, is_active: v }))}
                  />
                  <Label>Usuario activo</Label>
                </div>
              )}
            </>
          )}

          {/* Contraseña (create + reset-password) */}
          {(mode === 'create' || mode === 'reset-password') && (
            <>
              <div className="space-y-1.5">
                <Label>{mode === 'create' ? 'Contraseña *' : 'Nueva contraseña *'}</Label>
                <Input
                  type="password"
                  value={form.password}
                  onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                  placeholder="Mínimo 8 caracteres"
                />
              </div>
              <div className="space-y-1.5">
                <Label>Confirmar contraseña *</Label>
                <Input
                  type="password"
                  value={form.confirmPassword}
                  onChange={e => setForm(f => ({ ...f, confirmPassword: e.target.value }))}
                  placeholder="Repite la contraseña"
                />
              </div>
            </>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <Button onClick={handleSubmit} disabled={saving}>
            {saving ? 'Guardando…' : mode === 'create' ? 'Crear usuario' : 'Guardar cambios'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
