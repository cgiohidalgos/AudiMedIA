import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { authApi, saveToken, getToken, clearToken, type ApiUser } from '@/lib/api';

type AppRole = ApiUser['role'];

interface AuthContextType {
  user: ApiUser | null;
  role: AppRole | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string, fullName: string) => Promise<void>;
  signOut: () => void;
  hasRole: (roles: AppRole | AppRole[]) => boolean;
  isAdmin: boolean;
  isAuditor: boolean;
  isCoordinador: boolean;
  isEquipoMedico: boolean;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  role: null,
  loading: true,
  signIn: async () => {},
  signUp: async () => {},
  signOut: () => {},
  hasRole: () => false,
  isAdmin: false,
  isAuditor: false,
  isCoordinador: false,
  isEquipoMedico: false,
});

export const useAuth = () => useContext(AuthContext);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<ApiUser | null>(null);
  const [loading, setLoading] = useState(true);

  // Al montar, verificar si hay token guardado y obtener el perfil
  useEffect(() => {
    const token = getToken();
    if (!token) {
      setLoading(false);
      return;
    }
    authApi.me()
      .then(setUser)
      .catch(() => clearToken())
      .finally(() => setLoading(false));
  }, []);

  const signIn = async (email: string, password: string) => {
    const data = await authApi.login(email, password);
    saveToken(data.access_token);
    setUser(data.user);
  };

  const signUp = async (email: string, password: string, fullName: string) => {
    await authApi.register(email, password, fullName);
    // El registro no inicia sesión automáticamente
  };

  const signOut = () => {
    clearToken();
    setUser(null);
  };

  const hasRole = (roles: AppRole | AppRole[]) => {
    if (!user?.role) return false;
    const roleArray = Array.isArray(roles) ? roles : [roles];
    return roleArray.includes(user.role);
  };

  const isAdmin = user?.role === 'admin';
  const isAuditor = user?.role === 'auditor';
  const isCoordinador = user?.role === 'coordinador';
  const isEquipoMedico = user?.role === 'equipo_medico';

  return (
    <AuthContext.Provider value={{
      user,
      role: user?.role ?? null,
      loading,
      signIn,
      signUp,
      signOut,
      hasRole,
      isAdmin,
      isAuditor,
      isCoordinador,
      isEquipoMedico,
    }}>
      {children}
    </AuthContext.Provider>
  );
};
