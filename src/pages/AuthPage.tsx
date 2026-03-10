import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '@/integrations/supabase/client';
import { toast } from 'sonner';
import { z } from 'zod';

const loginSchema = z.object({
  email: z.string().trim().email('Correo electrónico inválido'),
  password: z.string().min(6, 'La contraseña debe tener al menos 6 caracteres'),
});

const registerSchema = loginSchema.extend({
  fullName: z.string().trim().min(1, 'Nombre requerido').max(100),
});

const AuthPage = () => {
  const navigate = useNavigate();
  const [isLogin, setIsLogin] = useState(true);
  const [loading, setLoading] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrors({});
    setLoading(true);

    try {
      if (isLogin) {
        const parsed = loginSchema.parse({ email, password });
        const { error } = await supabase.auth.signInWithPassword({
          email: parsed.email,
          password: parsed.password,
        });
        if (error) {
          toast.error(error.message === 'Invalid login credentials' 
            ? 'Credenciales inválidas' 
            : error.message);
          setLoading(false);
          return;
        }
        toast.success('Sesión iniciada');
        navigate('/app');
      } else {
        const parsed = registerSchema.parse({ email, password, fullName });
        const { error } = await supabase.auth.signUp({
          email: parsed.email,
          password: parsed.password,
          options: {
            data: { full_name: parsed.fullName },
            emailRedirectTo: window.location.origin,
          },
        });
        if (error) {
          toast.error(error.message);
          setLoading(false);
          return;
        }
        toast.success('Cuenta creada. Revise su correo para confirmar.');
      }
    } catch (err) {
      if (err instanceof z.ZodError) {
        const fieldErrors: Record<string, string> = {};
        err.errors.forEach(e => { fieldErrors[e.path[0] as string] = e.message; });
        setErrors(fieldErrors);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="font-display text-2xl font-bold text-foreground">Audi Med IA</h1>
          <p className="font-body text-sm text-muted-foreground mt-1">
            {isLogin ? 'Inicie sesión en su cuenta' : 'Cree una cuenta nueva'}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {!isLogin && (
            <div>
              <label className="data-label block mb-1.5">Nombre completo</label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full font-body text-sm bg-card border border-input rounded-md px-3 py-2.5 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                placeholder="Dr. Juan Pérez"
              />
              {errors.fullName && <p className="font-body text-xs text-destructive mt-1">{errors.fullName}</p>}
            </div>
          )}

          <div>
            <label className="data-label block mb-1.5">Correo electrónico</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full font-body text-sm bg-card border border-input rounded-md px-3 py-2.5 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
              placeholder="auditor@hospital.co"
            />
            {errors.email && <p className="font-body text-xs text-destructive mt-1">{errors.email}</p>}
          </div>

          <div>
            <label className="data-label block mb-1.5">Contraseña</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full font-body text-sm bg-card border border-input rounded-md px-3 py-2.5 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
              placeholder="••••••••"
            />
            {errors.password && <p className="font-body text-xs text-destructive mt-1">{errors.password}</p>}
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full font-body text-sm bg-primary text-primary-foreground rounded-md py-2.5 hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {loading ? 'Procesando...' : isLogin ? 'Iniciar sesión' : 'Crear cuenta'}
          </button>
        </form>

        <div className="mt-6 text-center">
          <button
            onClick={() => { setIsLogin(!isLogin); setErrors({}); }}
            className="font-body text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            {isLogin ? '¿No tiene cuenta? Regístrese' : '¿Ya tiene cuenta? Inicie sesión'}
          </button>
        </div>

        <div className="mt-8 border-t border-border pt-6">
          <p className="font-body text-xs text-muted-foreground text-center mb-3">Roles disponibles en el sistema</p>
          <div className="flex justify-center gap-2">
            {['Admin', 'Auditor', 'Usuario'].map(r => (
              <span key={r} className="font-body text-xs border border-border rounded-full px-3 py-1 text-muted-foreground">
                {r}
              </span>
            ))}
          </div>
          <p className="font-body text-xs text-muted-foreground text-center mt-2">
            El rol se asigna por un administrador después del registro.
          </p>
        </div>

        <div className="mt-4 text-center">
          <button
            onClick={() => navigate('/')}
            className="font-body text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            ← Volver al inicio
          </button>
        </div>
      </div>
    </div>
  );
};

export default AuthPage;
