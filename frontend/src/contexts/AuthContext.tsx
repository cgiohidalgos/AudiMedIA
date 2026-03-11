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
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  role: null,
  loading: true,
  signIn: async () => {},
  signUp: async () => {},
  signOut: () => {},
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

  return (
    <AuthContext.Provider value={{
      user,
      role: user?.role ?? null,
      loading,
      signIn,
      signUp,
      signOut,
    }}>
      {children}
    </AuthContext.Provider>
  );
};
