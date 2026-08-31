import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider } from "@/context/AuthContext";
import ProtectedRoute from "@/components/ProtectedRoute";
import Layout from "@/components/Layout";
import CompanyLogin from "@/pages/CompanyLogin";
import UserLogin from "@/pages/UserLogin";
import OwnerLogin from "@/pages/OwnerLogin";
import Setup from "@/pages/Setup";
import ChangePassword from "@/pages/ChangePassword";
import AuthCallback from "@/pages/AuthCallback";
import Dashboard from "@/pages/Dashboard";
import Clients from "@/pages/Clients";
import Products from "@/pages/Products";
import QuoteBuilder from "@/pages/QuoteBuilder";
import Documents from "@/pages/Documents";
import Finances from "@/pages/Finances";
import Team from "@/pages/Team";
import Settings from "@/pages/Settings";

function AppRouter() {
  const location = useLocation();
  if (location.hash?.includes("session_id=")) {
    return <AuthCallback />;
  }
  return (
    <Routes>
      <Route path="/login" element={<Navigate to="/login/company" replace />} />
      <Route path="/login/company" element={<CompanyLogin />} />
      <Route path="/login/user" element={<UserLogin />} />
      <Route path="/login/owner" element={<OwnerLogin />} />
      <Route path="/setup" element={<ProtectedRoute allowPendingSetup><Setup /></ProtectedRoute>} />
      <Route path="/change-password" element={<ProtectedRoute allowMustChangePassword><ChangePassword /></ProtectedRoute>} />
      <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/clientes" element={<Clients />} />
        <Route path="/produtos" element={<Products />} />
        <Route path="/orcamento" element={<QuoteBuilder />} />
        <Route path="/documentos" element={<Documents />} />
        <Route path="/financas" element={<ProtectedRoute allowedRoles={["owner", "gerente"]}><Finances /></ProtectedRoute>} />
        <Route path="/equipe" element={<ProtectedRoute allowedRoles={["owner"]}><Team /></ProtectedRoute>} />
        <Route path="/configuracoes" element={<ProtectedRoute allowedRoles={["owner", "gerente"]}><Settings /></ProtectedRoute>} />
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <div className="App">
      <AuthProvider>
        <BrowserRouter>
          <AppRouter />
          <Toaster position="top-right" richColors />
        </BrowserRouter>
      </AuthProvider>
    </div>
  );
}

export default App;
