import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const checkAuth = useCallback(async () => {
    try {
      const { data } = await api.get("/auth/me");
      setUser(data);
    } catch (err) {
      if (err?.response?.status !== 401) {
        console.warn("[AuthContext] checkAuth failed:", err);
      }
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const ownerLogin = useCallback(async (email, password) => {
    const { data } = await api.post("/auth/owner-login", { email, password });
    if (data.token) localStorage.setItem("g360_token", data.token);
    await checkAuth();
    return data;
  }, [checkAuth]);

  const companyLogin = useCallback(async (code, password) => {
    const { data } = await api.post("/auth/company-login", { code, password });
    return data; // { company, users }
  }, []);

  const userLogin = useCallback(async (username, password) => {
    const { data } = await api.post("/auth/user-login", { username, password });
    if (data.token) localStorage.setItem("g360_token", data.token);
    await checkAuth();
    return data;
  }, [checkAuth]);

  const register = useCallback(async (name, email, password) => {
    const { data } = await api.post("/auth/register", { name, email, password });
    if (data.token) localStorage.setItem("g360_token", data.token);
    await checkAuth();
    return data;
  }, [checkAuth]);

  const changePassword = useCallback(async (current_password, new_password) => {
    await api.post("/auth/change-password", { current_password, new_password });
    await checkAuth();
  }, [checkAuth]);

  const setupCompany = useCallback(async (code, password, name) => {
    await api.post("/auth/setup-company", { code, password, name });
    await checkAuth();
  }, [checkAuth]);

  const logout = useCallback(async () => {
    try {
      await api.post("/auth/logout");
    } catch (err) {
      console.warn("[AuthContext] logout endpoint failed (proceeding with local cleanup):", err);
    }
    localStorage.removeItem("g360_token");
    setUser(null);
  }, []);

  const role = user?.role || null;
  const isOwner = role === "owner";
  const isGerente = role === "gerente";
  const isVendedor = role === "vendedor";

  const value = useMemo(() => ({
    user, setUser, loading, role,
    is: (r) => role === r,
    isOwner, isGerente, isVendedor,
    ownerLogin, companyLogin, userLogin, register, changePassword, setupCompany, logout, checkAuth,
  }), [user, loading, role, isOwner, isGerente, isVendedor, ownerLogin, companyLogin, userLogin, register, changePassword, setupCompany, logout, checkAuth]);

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
