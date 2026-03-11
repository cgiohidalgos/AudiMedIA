import { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { type ApiUser } from '@/lib/api';

type AppRole = ApiUser['role'];

interface RoleGuardProps {
  roles: AppRole[];
  children: ReactNode;
  fallback?: ReactNode;
  redirectTo?: string;
}

/**
 * RoleGuard - Componente para proteger contenido por roles
 * 
 * @param roles - Array de roles permitidos
 * @param children - Contenido a mostrar si el usuario tiene el rol
 * @param fallback - Contenido alternativo si no tiene el rol (opcional)
 * @param redirectTo - Ruta a la que redirigir si no tiene el rol (opcional)
 * 
 * @example
 * ```tsx
 * <RoleGuard roles={['admin']}>
 *   <AdminPanel />
 * </RoleGuard>
 * ```
 * 
 * @example Con fallback
 * ```tsx
 * <RoleGuard 
 *   roles={['admin', 'coordinador']} 
 *   fallback={<p>No tienes permisos</p>}
 * >
 *   <Dashboard />
 * </RoleGuard>
 * ```
 */
export const RoleGuard = ({ roles, children, fallback, redirectTo }: RoleGuardProps) => {
  const { hasRole, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!hasRole(roles)) {
    if (redirectTo) {
      return <Navigate to={redirectTo} replace />;
    }
    return <>{fallback || null}</>;
  }

  return <>{children}</>;
};

/**
 * Hook para verificar permisos en componentes
 * 
 * @example
 * ```tsx
 * const { canUpload, canManageUsers } = usePermissions();
 * 
 * return (
 *   <div>
 *     {canUpload && <UploadButton />}
 *     {canManageUsers && <UserManagement />}
 *   </div>
 * );
 * ```
 */
export const usePermissions = () => {
  const { hasRole, isAdmin, isAuditor, isCoordinador, isEquipoMedico } = useAuth();

  return {
    // Admin - Todos los permisos
    canManageUsers: isAdmin,
    canConfigureSystem: isAdmin,
    canConfigureTarifas: isAdmin,
    canManageServices: isAdmin,
    canViewAllReports: isAdmin,

    // Auditor - Auditoría y análisis
    canUpload: hasRole(['admin', 'auditor']),
    canAnalyzeHistorias: hasRole(['admin', 'auditor']),
    canMarkAsResolved: hasRole(['admin', 'auditor']),
    canExportReports: hasRole(['admin', 'auditor']),
    canUseChat: hasRole(['admin', 'auditor', 'coordinador']),

    // Coordinador - Dashboard y métricas
    canViewDashboard: hasRole(['admin', 'coordinador']),
    canViewFinancialMetrics: hasRole(['admin', 'coordinador']),
    canViewTrends: hasRole(['admin', 'coordinador']),
    canDownloadExecutiveReports: hasRole(['admin', 'coordinador']),

    // Equipo Médico - Vista limitada
    canViewOwnPatients: hasRole(['admin', 'equipo_medico']),
    canReceiveAlerts: hasRole(['admin', 'equipo_medico']),

    // General - Todos los usuarios autenticados
    canViewPatients: hasRole(['admin', 'auditor', 'coordinador', 'equipo_medico']),

    // Shortcuts por rol
    isAdmin,
    isAuditor,
    isCoordinador,
    isEquipoMedico,
  };
};

export default RoleGuard;
