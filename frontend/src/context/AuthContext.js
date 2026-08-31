import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const checkAuth = useCallback(async () => {
    try {
      const { data } = await api.get("/auth/me");
      setUser(data);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (window.location.hash?.includes("session_id=")) {
      setLoading(false);
      return;
    }
    checkAuth();
  }, [checkAuth]);

  const ownerLogin = async (email, password) => {
    const { data } = await api.post("/auth/owner-login", { email, password });
    if (data.token) localStorage.setItem("g360_token", data.token);
    await checkAuth();
    return data;
  };

  const companyLogin = async (code, password) => {
    const { data } = await api.post("/auth/company-login", { code, password });
    return data; // { company, users }
  };

  const userLogin = async (username, password) => {
    const { data } = await api.post("/auth/user-login", { username, password });
    if (data.token) localStorage.setItem("g360_token", data.token);
    await checkAuth();
    return data;
  };

  const register = async (name, email, password) => {
    const { data } = await api.post("/auth/register", { name, email, password });
    if (data.token) localStorage.setItem("g360_token", data.token);
    await checkAuth();
    return data;
  };

  const changePassword = async (current_password, new_password) => {
    await api.post("/auth/change-password", { current_password, new_password });
    await checkAuth();
  };

  const setupCompany = async (code, password, name) => {
    await api.post("/auth/setup-company", { code, password, name });
    await checkAuth();
  };

  const logout = async () => {
    try { await api.post("/auth/logout"); } catch {}
    localStorage.removeItem("g360_token");
    setUser(null);
  };

  const role = user?.role || null;
  const is = (r) => role === r;
  const isOwner = role === "owner";
  const isGerente = role === "gerente";
  const isVendedor = role === "vendedor";

  return (
    <AuthContext.Provider value={{
      user, setUser, loading, role, is, isOwner, isGerente, isVendedor,
      ownerLogin, companyLogin, userLogin, register, changePassword, setupCompany, logout, checkAuth,
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
