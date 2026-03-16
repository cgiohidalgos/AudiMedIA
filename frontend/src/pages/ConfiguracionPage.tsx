import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { usePermissions } from '@/components/RoleGuard';
import { useNavigate } from 'react-router-dom';
import AppNavbar from '@/components/AppNavbar';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Settings,
  FileText,
  Building2,
  Cpu,
  Save,
  Plus,
  Pencil,
  Trash2,
  Check,
  X,
  ShieldCheck,
} from 'lucide-react';
import { toast } from 'sonner';
import {
  configApi,
  type TarifaConfig,
  type TarifaConfigUpdate,
  type EPSContrato,
  type EPSContratoPayload,
  type ServicioHospitalario,
  type ServicioPayload,
  type SistemaParams,
} from '@/lib/api';

// ─── helpers ─────────────────────────────────────────────────────────────────

function formatCOP(value: number) {
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    maximumFractionDigits: 0,
  }).format(value);
}

function formatDate(iso: string) {
  return new Date(iso + 'T00:00:00').toLocaleDateString('es-CO', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
}

function isVigente(hasta: string) {
  return new Date(hasta) >= new Date();
}

// ─── tabs ─────────────────────────────────────────────────────────────────────

// Tab 1: Tarifas
interface TarifasTabProps {
  isAdmin: boolean;
}

function TarifasTab({ isAdmin }: TarifasTabProps) {
  const [tarifa, setTarifa] = useState<TarifaConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState<TarifaConfigUpdate>({});

  const load = useCallback(async () => {
    try {
      const data = await configApi.getTarifas();
      setTarifa(data);
      setForm({
        institucion_nombre: data.institucion_nombre,
        tarifa_dia_hospitalizacion: data.tarifa_dia_hospitalizacion,
        tarifa_dia_uci: data.tarifa_dia_uci,
        tarifa_dia_intermedio: data.tarifa_dia_intermedio,
        porcentaje_glosas_historico: data.porcentaje_glosas_historico,
        glosa_evolucion_porcentaje: data.glosa_evolucion_porcentaje,
        valor_promedio_glosa: data.valor_promedio_glosa,
      });
    } catch {
      toast.error('No se pudieron cargar las tarifas');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const updated = await configApi.updateTarifas(form);
      setTarifa(updated);
      toast.success('Tarifas actualizadas correctamente');
    } catch {
      toast.error('Error al guardar las tarifas');
    } finally {
      setSaving(false);
    }
  };

  const num = (v: number | undefined) => v ?? 0;

  if (loading) {
    return <div className="py-12 text-center text-sm text-muted-foreground">Cargando…</div>;
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Institución</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="max-w-sm space-y-2">
            <Label htmlFor="inst-nombre">Nombre de la institución</Label>
            <Input
              id="inst-nombre"
              value={form.institucion_nombre ?? ''}
              onChange={e => setForm(f => ({ ...f, institucion_nombre: e.target.value }))}
              disabled={!isAdmin}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Tarifas por día de hospitalización</CardTitle>
          <CardDescription>Valores en pesos colombianos (COP)</CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 sm:grid-cols-3 gap-6">
          {([
            { key: 'tarifa_dia_hospitalizacion', label: 'Cama hospitalización general' },
            { key: 'tarifa_dia_intermedio', label: 'Cama cuidado intermedio' },
            { key: 'tarifa_dia_uci', label: 'Cama UCI' },
          ] as { key: keyof TarifaConfigUpdate; label: string }[]).map(({ key, label }) => (
            <div key={key} className="space-y-2">
              <Label htmlFor={key}>{label}</Label>
              <Input
                id={key}
                type="number"
                min={0}
                step={1000}
                value={num(form[key] as number)}
                onChange={e => setForm(f => ({ ...f, [key]: parseFloat(e.target.value) || 0 }))}
                disabled={!isAdmin}
              />
              <p className="text-xs text-muted-foreground">
                {formatCOP(num(form[key] as number))}
              </p>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Parámetros de glosas</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 sm:grid-cols-3 gap-6">
          <div className="space-y-2">
            <Label htmlFor="pct-historico">% histórico glosas aceptadas</Label>
            <Input
              id="pct-historico"
              type="number"
              min={0}
              max={100}
              step={0.1}
              value={num(form.porcentaje_glosas_historico)}
              onChange={e => setForm(f => ({ ...f, porcentaje_glosas_historico: parseFloat(e.target.value) || 0 }))}
              disabled={!isAdmin}
            />
            <p className="text-xs text-muted-foreground">{num(form.porcentaje_glosas_historico)}%</p>
          </div>
          <div className="space-y-2">
            <Label htmlFor="pct-evolucion">% glosa evolución faltante</Label>
            <Input
              id="pct-evolucion"
              type="number"
              min={0}
              max={100}
              step={0.1}
              value={num(form.glosa_evolucion_porcentaje)}
              onChange={e => setForm(f => ({ ...f, glosa_evolucion_porcentaje: parseFloat(e.target.value) || 0 }))}
              disabled={!isAdmin}
            />
            <p className="text-xs text-muted-foreground">{num(form.glosa_evolucion_porcentaje)}%</p>
          </div>
          <div className="space-y-2">
            <Label htmlFor="valor-glosa">Valor promedio por glosa evitada</Label>
            <Input
              id="valor-glosa"
              type="number"
              min={0}
              step={1000}
              value={num(form.valor_promedio_glosa)}
              onChange={e => setForm(f => ({ ...f, valor_promedio_glosa: parseFloat(e.target.value) || 0 }))}
              disabled={!isAdmin}
            />
            <p className="text-xs text-muted-foreground">{formatCOP(num(form.valor_promedio_glosa))}</p>
          </div>
        </CardContent>
      </Card>

      {isAdmin && (
        <div className="flex justify-end">
          <Button onClick={handleSave} disabled={saving}>
            <Save className="h-4 w-4 mr-2" />
            {saving ? 'Guardando…' : 'Guardar configuración'}
          </Button>
        </div>
      )}

      {tarifa && (
        <p className="text-xs text-muted-foreground text-right">
          Última actualización: {new Date(tarifa.updated_at).toLocaleString('es-CO')}
        </p>
      )}
    </div>
  );
}

// Tab 2: EPS Contratos
interface EPSFormState {
  nombre_eps: string;
  tarifa_especial: string;
  vigencia_desde: string;
  vigencia_hasta: string;
  notas: string;
  activo: boolean;
}

const emptyEPS: EPSFormState = {
  nombre_eps: '',
  tarifa_especial: '',
  vigencia_desde: '',
  vigencia_hasta: '',
  notas: '',
  activo: true,
};

function EPSTab({ isAdmin }: { isAdmin: boolean }) {
  const [contratos, setContratos] = useState<EPSContrato[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<EPSContrato | null>(null);
  const [form, setForm] = useState<EPSFormState>(emptyEPS);
  const [saving, setSaving] = useState(false);
  const [deleteId, setDeleteId] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await configApi.listEPS();
      setContratos(data);
    } catch {
      toast.error('No se pudieron cargar los contratos EPS');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const openCreate = () => {
    setEditing(null);
    setForm(emptyEPS);
    setDialogOpen(true);
  };

  const openEdit = (c: EPSContrato) => {
    setEditing(c);
    setForm({
      nombre_eps: c.nombre_eps,
      tarifa_especial: c.tarifa_especial != null ? String(c.tarifa_especial) : '',
      vigencia_desde: c.vigencia_desde,
      vigencia_hasta: c.vigencia_hasta,
      notas: c.notas ?? '',
      activo: c.activo,
    });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    if (!form.nombre_eps || !form.vigencia_desde || !form.vigencia_hasta) {
      toast.error('Nombre, vigencia desde y vigencia hasta son requeridos');
      return;
    }
    setSaving(true);
    const payload: EPSContratoPayload = {
      nombre_eps: form.nombre_eps,
      tarifa_especial: form.tarifa_especial ? parseFloat(form.tarifa_especial) : null,
      vigencia_desde: form.vigencia_desde,
      vigencia_hasta: form.vigencia_hasta,
      notas: form.notas || null,
      activo: form.activo,
    };
    try {
      if (editing) {
        await configApi.updateEPS(editing.id, payload);
        toast.success('Contrato actualizado');
      } else {
        await configApi.createEPS(payload);
        toast.success('Contrato creado');
      }
      setDialogOpen(false);
      load();
    } catch {
      toast.error('Error al guardar el contrato');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await configApi.deleteEPS(id);
      toast.success('Contrato eliminado');
      setDeleteId(null);
      load();
    } catch {
      toast.error('Error al eliminar el contrato');
    }
  };

  return (
    <div className="space-y-4">
      {isAdmin && (
        <div className="flex justify-end">
          <Button size="sm" onClick={openCreate}>
            <Plus className="h-4 w-4 mr-2" />
            Agregar contrato
          </Button>
        </div>
      )}

      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="py-12 text-center text-sm text-muted-foreground">Cargando…</div>
          ) : contratos.length === 0 ? (
            <div className="py-12 text-center text-sm text-muted-foreground">
              No hay contratos registrados
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>EPS</TableHead>
                  <TableHead>Tarifa especial</TableHead>
                  <TableHead>Vigencia</TableHead>
                  <TableHead>Estado</TableHead>
                  {isAdmin && <TableHead className="text-right">Acciones</TableHead>}
                </TableRow>
              </TableHeader>
              <TableBody>
                {contratos.map((c) => (
                  <TableRow key={c.id}>
                    <TableCell className="font-medium">{c.nombre_eps}</TableCell>
                    <TableCell>
                      {c.tarifa_especial != null ? formatCOP(c.tarifa_especial) : '—'}
                    </TableCell>
                    <TableCell className="text-sm">
                      {formatDate(c.vigencia_desde)} → {formatDate(c.vigencia_hasta)}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={isVigente(c.vigencia_hasta) && c.activo ? 'default' : 'secondary'}
                      >
                        {isVigente(c.vigencia_hasta) && c.activo ? 'Vigente' : 'Vencido'}
                      </Badge>
                    </TableCell>
                    {isAdmin && (
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7"
                            onClick={() => openEdit(c)}
                          >
                            <Pencil className="h-3.5 w-3.5" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7 text-destructive hover:text-destructive"
                            onClick={() => setDeleteId(c.id)}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Create / Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{editing ? 'Editar contrato EPS' : 'Nuevo contrato EPS'}</DialogTitle>
            <DialogDescription>
              Complete los datos del contrato con la EPS.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <Label>Nombre de la EPS *</Label>
              <Input
                value={form.nombre_eps}
                onChange={e => setForm(f => ({ ...f, nombre_eps: e.target.value }))}
                placeholder="Ej: Sura, Compensar…"
              />
            </div>
            <div className="space-y-1.5">
              <Label>Tarifa especial (COP)</Label>
              <Input
                type="number"
                min={0}
                step={1000}
                value={form.tarifa_especial}
                onChange={e => setForm(f => ({ ...f, tarifa_especial: e.target.value }))}
                placeholder="Dejar vacío si usa tarifa estándar"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label>Vigencia desde *</Label>
                <Input
                  type="date"
                  value={form.vigencia_desde}
                  onChange={e => setForm(f => ({ ...f, vigencia_desde: e.target.value }))}
                />
              </div>
              <div className="space-y-1.5">
                <Label>Vigencia hasta *</Label>
                <Input
                  type="date"
                  value={form.vigencia_hasta}
                  onChange={e => setForm(f => ({ ...f, vigencia_hasta: e.target.value }))}
                />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label>Notas</Label>
              <Input
                value={form.notas}
                onChange={e => setForm(f => ({ ...f, notas: e.target.value }))}
                placeholder="Observaciones opcionales"
              />
            </div>
            <div className="flex items-center gap-3">
              <Switch
                checked={form.activo}
                onCheckedChange={v => setForm(f => ({ ...f, activo: v }))}
              />
              <Label>Contrato activo</Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancelar
            </Button>
            <Button onClick={handleSave} disabled={saving}>
              {saving ? 'Guardando…' : editing ? 'Guardar cambios' : 'Crear contrato'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete confirmation Dialog */}
      <Dialog open={!!deleteId} onOpenChange={(open) => !open && setDeleteId(null)}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>¿Eliminar contrato?</DialogTitle>
            <DialogDescription>
              Esta acción es irreversible. El contrato se eliminará permanentemente.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteId(null)}>
              Cancelar
            </Button>
            <Button
              variant="destructive"
              onClick={() => deleteId && handleDelete(deleteId)}
            >
              Eliminar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// Tab 3: Servicios Hospitalarios
interface ServicioFormState {
  nombre: string;
  medico_jefe: string;
  correo_notificaciones: string;
  activo: boolean;
}

const emptyServicio: ServicioFormState = {
  nombre: '',
  medico_jefe: '',
  correo_notificaciones: '',
  activo: true,
};

function ServiciosTab({ isAdmin }: { isAdmin: boolean }) {
  const [servicios, setServicios] = useState<ServicioHospitalario[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<ServicioHospitalario | null>(null);
  const [form, setForm] = useState<ServicioFormState>(emptyServicio);
  const [saving, setSaving] = useState(false);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [togglingId, setTogglingId] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await configApi.listServicios();
      setServicios(data);
    } catch {
      toast.error('No se pudieron cargar los servicios');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const openCreate = () => {
    setEditing(null);
    setForm(emptyServicio);
    setDialogOpen(true);
  };

  const openEdit = (s: ServicioHospitalario) => {
    setEditing(s);
    setForm({
      nombre: s.nombre,
      medico_jefe: s.medico_jefe ?? '',
      correo_notificaciones: s.correo_notificaciones ?? '',
      activo: s.activo,
    });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    if (!form.nombre) {
      toast.error('El nombre del servicio es requerido');
      return;
    }
    setSaving(true);
    const payload: ServicioPayload = {
      nombre: form.nombre,
      medico_jefe: form.medico_jefe || null,
      correo_notificaciones: form.correo_notificaciones || null,
      activo: form.activo,
    };
    try {
      if (editing) {
        await configApi.updateServicio(editing.id, payload);
        toast.success('Servicio actualizado');
      } else {
        await configApi.createServicio(payload);
        toast.success('Servicio creado');
      }
      setDialogOpen(false);
      load();
    } catch {
      toast.error('Error al guardar el servicio');
    } finally {
      setSaving(false);
    }
  };

  const handleToggleActivo = async (s: ServicioHospitalario) => {
    setTogglingId(s.id);
    try {
      await configApi.updateServicio(s.id, { activo: !s.activo });
      load();
    } catch {
      toast.error('Error al actualizar el servicio');
    } finally {
      setTogglingId(null);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await configApi.deleteServicio(id);
      toast.success('Servicio eliminado');
      setDeleteId(null);
      load();
    } catch {
      toast.error('Error al eliminar el servicio');
    }
  };

  return (
    <div className="space-y-4">
      {isAdmin && (
        <div className="flex justify-end">
          <Button size="sm" onClick={openCreate}>
            <Plus className="h-4 w-4 mr-2" />
            Agregar servicio
          </Button>
        </div>
      )}

      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="py-12 text-center text-sm text-muted-foreground">Cargando…</div>
          ) : servicios.length === 0 ? (
            <div className="py-12 text-center text-sm text-muted-foreground">
              No hay servicios registrados
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Servicio</TableHead>
                  <TableHead>Médico jefe</TableHead>
                  <TableHead>Correo notificaciones</TableHead>
                  <TableHead>Activo</TableHead>
                  {isAdmin && <TableHead className="text-right">Acciones</TableHead>}
                </TableRow>
              </TableHeader>
              <TableBody>
                {servicios.map((s) => (
                  <TableRow key={s.id}>
                    <TableCell className="font-medium">{s.nombre}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {s.medico_jefe ?? '—'}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {s.correo_notificaciones ?? '—'}
                    </TableCell>
                    <TableCell>
                      {isAdmin ? (
                        <Switch
                          checked={s.activo}
                          onCheckedChange={() => handleToggleActivo(s)}
                          disabled={togglingId === s.id}
                        />
                      ) : (
                        s.activo ? (
                          <Check className="h-4 w-4 text-emerald-500" />
                        ) : (
                          <X className="h-4 w-4 text-muted-foreground" />
                        )
                      )}
                    </TableCell>
                    {isAdmin && (
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7"
                            onClick={() => openEdit(s)}
                          >
                            <Pencil className="h-3.5 w-3.5" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7 text-destructive hover:text-destructive"
                            onClick={() => setDeleteId(s.id)}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Create / Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>
              {editing ? 'Editar servicio' : 'Nuevo servicio hospitalario'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <Label>Nombre del servicio *</Label>
              <Input
                value={form.nombre}
                onChange={e => setForm(f => ({ ...f, nombre: e.target.value }))}
                placeholder="Ej: Medicina Interna, Cirugía…"
              />
            </div>
            <div className="space-y-1.5">
              <Label>Médico jefe</Label>
              <Input
                value={form.medico_jefe}
                onChange={e => setForm(f => ({ ...f, medico_jefe: e.target.value }))}
                placeholder="Nombre del médico jefe"
              />
            </div>
            <div className="space-y-1.5">
              <Label>Correo de notificaciones</Label>
              <Input
                type="email"
                value={form.correo_notificaciones}
                onChange={e => setForm(f => ({ ...f, correo_notificaciones: e.target.value }))}
                placeholder="correo@hospital.com"
              />
            </div>
            <div className="flex items-center gap-3">
              <Switch
                checked={form.activo}
                onCheckedChange={v => setForm(f => ({ ...f, activo: v }))}
              />
              <Label>Servicio activo</Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancelar
            </Button>
            <Button onClick={handleSave} disabled={saving}>
              {saving ? 'Guardando…' : editing ? 'Guardar cambios' : 'Crear servicio'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Dialog */}
      <Dialog open={!!deleteId} onOpenChange={(open) => !open && setDeleteId(null)}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>¿Eliminar servicio?</DialogTitle>
            <DialogDescription>
              Esta acción es irreversible.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteId(null)}>
              Cancelar
            </Button>
            <Button
              variant="destructive"
              onClick={() => deleteId && handleDelete(deleteId)}
            >
              Eliminar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// Tab 4: Parámetros del Sistema
function SistemaTab() {
  const [params, setParams] = useState<SistemaParams | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    configApi.getSistema()
      .then(setParams)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="py-12 text-center text-sm text-muted-foreground">Cargando…</div>;
  }

  if (error || !params) {
    return (
      <div className="py-12 text-center text-sm text-muted-foreground">
        No se pudieron cargar los parámetros del sistema.
      </div>
    );
  }

  const items = [
    { label: 'Modelo LLM', value: params.llm_model, mono: true },
    { label: 'Máx. tokens LLM', value: String(params.llm_max_tokens), mono: false },
    { label: 'API Key OpenAI', value: params.openai_key_preview, mono: true },
    { label: 'OpenAI configurado', value: params.openai_key_configured ? 'Sí' : 'No', mono: false },
    { label: 'Máx. PDFs simultáneos', value: String(params.max_pdfs_simultaneos), mono: false },
    { label: 'Retención de datos (días)', value: String(params.retencion_datos_dias), mono: false },
    {
      label: 'Anonimización activa',
      value: params.anonimizacion_activa ? 'Activa' : 'Inactiva',
      mono: false,
    },
  ];

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-muted-foreground" />
            <CardTitle className="text-base">Parámetros del sistema</CardTitle>
          </div>
          <CardDescription>
            Estos valores son de sólo lectura. Modifícalos en las variables de entorno del servidor.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <dl className="divide-y divide-border">
            {items.map(({ label, value, mono }) => (
              <div key={label} className="flex items-center justify-between py-3 gap-4">
                <dt className="text-sm text-muted-foreground min-w-0">{label}</dt>
                <dd className={`text-sm font-medium text-right min-w-0 ${mono ? 'font-mono' : ''}`}>
                  {value}
                </dd>
              </div>
            ))}
          </dl>
        </CardContent>
      </Card>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

const ConfiguracionPage = () => {
  const { role } = useAuth();
  const permissions = usePermissions();
  const navigate = useNavigate();

  // Solo admin y coordinador pueden ver esta página
  useEffect(() => {
    if (role && !['admin', 'coordinador'].includes(role)) {
      navigate('/app', { replace: true });
    }
  }, [role, navigate]);

  const isAdmin = permissions.canConfigureSystem;

  return (
    <div className="flex flex-col h-screen bg-background">
      <AppNavbar title="Configuración del Sistema" />

      <div className="flex-1 overflow-y-auto">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
          <div className="mb-6">
            <h1 className="text-xl font-semibold text-foreground">Configuración del Sistema</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Gestione tarifas, contratos EPS y servicios hospitalarios.
              {!isAdmin && ' (Vista de solo lectura — se requiere rol Administrador para editar)'}
            </p>
          </div>

          <Tabs defaultValue="tarifas">
            <TabsList className="mb-6 h-10">
              <TabsTrigger value="tarifas" className="gap-2 text-xs sm:text-sm">
                <FileText className="h-3.5 w-3.5" />
                Tarifas
              </TabsTrigger>
              <TabsTrigger value="eps" className="gap-2 text-xs sm:text-sm">
                <Building2 className="h-3.5 w-3.5" />
                Contratos EPS
              </TabsTrigger>
              <TabsTrigger value="servicios" className="gap-2 text-xs sm:text-sm">
                <Settings className="h-3.5 w-3.5" />
                Servicios
              </TabsTrigger>
              <TabsTrigger value="sistema" className="gap-2 text-xs sm:text-sm">
                <Cpu className="h-3.5 w-3.5" />
                Parámetros
              </TabsTrigger>
            </TabsList>

            <TabsContent value="tarifas">
              <TarifasTab isAdmin={isAdmin} />
            </TabsContent>

            <TabsContent value="eps">
              <EPSTab isAdmin={isAdmin} />
            </TabsContent>

            <TabsContent value="servicios">
              <ServiciosTab isAdmin={isAdmin} />
            </TabsContent>

            <TabsContent value="sistema">
              <SistemaTab />
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
};

export default ConfiguracionPage;
