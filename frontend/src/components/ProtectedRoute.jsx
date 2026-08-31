import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";

export default function ProtectedRoute({ children, allowedRoles, allowPendingSetup, allowMustChangePassword }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="min-h-screen grid place-items-center bg-white">
        <div className="w-10 h-10 border-4 border-[#F05D23] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }
  if (!user) return <Navigate to="/login/company" replace state={{ from: location }} />;

  if (user.must_change_password && !allowMustChangePassword) {
    return <Navigate to="/change-password" replace />;
  }
  if (user.company?.pending_setup && !allowPendingSetup && user.role === "owner") {
    return <Navigate to="/setup" replace />;
  }
  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <Navigate to="/dashboard" replace />;
  }
  return children;
}
