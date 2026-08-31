import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
export default function AuthCallback() {
  const navigate = useNavigate();
  const { checkAuth } = useAuth();
  const processed = useRef(false);

  useEffect(() => {
    if (processed.current) return;
    processed.current = true;

    const hash = window.location.hash;
    const match = hash.match(/session_id=([^&]+)/);
    if (!match) {
      navigate("/login/company", { replace: true });
      return;
    }
    const sessionId = match[1];
    (async () => {
      try {
        const { data } = await api.post("/auth/session", { session_id: sessionId });
        await checkAuth();
        window.history.replaceState({}, document.title, "/dashboard");
        if (data.must_change_password) navigate("/change-password", { replace: true });
        else navigate("/dashboard", { replace: true });
      } catch {
        navigate("/login/owner", { replace: true });
      }
    })();
  }, [navigate, checkAuth]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-white">
      <div className="text-center">
        <div className="w-12 h-12 border-4 border-[#F05D23] border-t-transparent rounded-full animate-spin mx-auto" />
        <p className="mt-4 text-sm text-zinc-500">Autenticando…</p>
      </div>
    </div>
  );
}
