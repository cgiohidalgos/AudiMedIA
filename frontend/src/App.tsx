import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthProvider } from "@/contexts/AuthContext";
import { ProcessingProvider } from "@/contexts/ProcessingContext";
import ProtectedRoute from "@/components/ProtectedRoute";
import LandingPage from "./pages/LandingPage";
import AuthPage from "./pages/AuthPage";
import AppPage from "./pages/AppPage";
import DashboardPage from "./pages/DashboardPage";
import ReporteIndividualPage from "./pages/ReporteIndividualPage";
import CuadroControlPage from "./pages/CuadroControlPage";
import ConfiguracionPage from "./pages/ConfiguracionPage";
import UsuariosPage from "./pages/UsuariosPage";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter
        future={{
          v7_startTransition: true,
          v7_relativeSplatPath: true
        }}
      >
        <AuthProvider>
          <ProcessingProvider>
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/auth" element={<AuthPage />} />
            <Route path="/app" element={
              <ProtectedRoute>
                <AppPage />
              </ProtectedRoute>
            } />
            <Route path="/dashboard" element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            } />
            <Route path="/control-board" element={
              <ProtectedRoute>
                <CuadroControlPage />
              </ProtectedRoute>
            } />
            <Route path="/patients/:id/report" element={
              <ProtectedRoute>
                <ReporteIndividualPage />
              </ProtectedRoute>
            } />
            <Route path="/configuracion" element={
              <ProtectedRoute>
                <ConfiguracionPage />
              </ProtectedRoute>
            } />
            <Route path="/usuarios" element={
              <ProtectedRoute>
                <UsuariosPage />
              </ProtectedRoute>
            } />
            <Route path="*" element={<NotFound />} />
          </Routes>
          </ProcessingProvider>
        </AuthProvider>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
