import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { UserCircle2 } from "lucide-react";

const ROLE_BADGE = {
  owner: { label: "Dono", bg: "bg-[#F05D23]/10", fg: "text-[#F05D23]" },
  gerente: { label: "Gerente", bg: "bg-zinc-900/10", fg: "text-zinc-900" },
  vendedor: { label: "Vendedor", bg: "bg-zinc-100", fg: "text-zinc-700" },
};

export default function UserLogin() {
  const navigate = useNavigate();
  const location = useLocation();
  const { userLogin } = useAuth();
  const preload = location.state || {};
  const [company] = useState(preload.company || null);
  const [users] = useState(preload.users || []);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    // If user reloads and lost state, force back to step 1
    if (!company) navigate("/login/company", { replace: true });
  }, [company, navigate]);

  if (!company) return null;

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const data = await userLogin(username, password);
      if (data.must_change_password) navigate("/change-password", { replace: true });
      else navigate("/dashboard", { replace: true });
    } catch (err) {
      toast.error(err.response?.data?.detail || "Falha ao entrar");
    } finally { setBusy(false); }
  };

  const pickUser = (u) => {
    setUsername(u.username);
    document.getElementById("password")?.focus();
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-white">
      <div className="hidden lg:flex relative overflow-hidden bg-[#09090B]">
        <div className="absolute inset-0 grain opacity-30" />
        <div className="absolute inset-0 bg-cover bg-center opacity-40" style={{ backgroundImage: "url('https://images.unsplash.com/photo-1775810985509-c002017e149f?crop=entropy&cs=srgb&fm=jpg&q=85&w=1600')" }} />
        <div className="absolute inset-0 bg-gradient-to-tr from-[#09090B] via-transparent to-transparent" />
        <div className="relative z-10 flex flex-col justify-between p-14 text-white w-full">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-md bg-[#F05D23] grid place-items-center font-display font-bold text-white text-lg">G</div>
            <span className="font-display text-xl font-semibold">Gestor360</span>
          </div>
          <div>
            <div className="text-xs uppercase tracking-widest text-[#F05D23] font-semibold">Etapa 2 de 2</div>
            <h1 className="mt-3 font-display text-5xl xl:text-6xl font-bold leading-tight tracking-tight">
              Quem está<br /><span className="text-[#F05D23]">chegando?</span>
            </h1>
            <p className="mt-6 text-zinc-300 max-w-md">Selecione o seu usuário. Cada pessoa entra com o próprio nome e vê apenas o que precisa.</p>
          </div>
          <div className="text-xs text-zinc-500">© 2026 Gestor360</div>
        </div>
      </div>

      <div className="flex items-center justify-center p-6 sm:p-10">
        <div className="w-full max-w-md">
          <div className="flex items-center gap-2 text-xs uppercase tracking-widest font-semibold text-zinc-400">
            <span className="w-6 h-6 rounded-full bg-zinc-900 text-white grid place-items-center text-xs">✓</span>
            {company.name}
            <span className="text-zinc-300">→</span>
            <span className="w-6 h-6 rounded-full bg-[#F05D23] text-white grid place-items-center text-xs">2</span>
            Usuário
          </div>
          <h2 className="mt-6 font-display text-3xl font-semibold text-zinc-900">Selecionar usuário</h2>
          <p className="text-sm text-zinc-500 mt-1">Clique no seu perfil e digite sua senha.</p>

          {users.length > 0 && (
            <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-2" data-testid="users-list">
              {users.map(u => {
                const badge = ROLE_BADGE[u.role] || ROLE_BADGE.vendedor;
                const active = username === u.username;
                return (
                  <button
                    key={u.user_id}
                    type="button"
                    data-testid={`user-pick-${u.username}`}
                    onClick={() => pickUser(u)}
                    className={`p-3 rounded-lg border flex items-center gap-3 text-left transition-colors ${active ? "border-[#F05D23] bg-[#FDF0EC]" : "border-zinc-200 hover:border-zinc-900 bg-white"}`}
                  >
                    {u.picture ? <img src={u.picture} alt="" className="w-9 h-9 rounded-full object-cover" /> : <div className="w-9 h-9 rounded-full bg-zinc-900 text-white grid place-items-center text-sm font-semibold shrink-0">{u.name?.charAt(0).toUpperCase()}</div>}
                    <div className="min-w-0 flex-1">
                      <div className="font-medium text-sm truncate">{u.name}</div>
                      <div className="text-xs text-zinc-500 truncate">@{u.username}</div>
                    </div>
                    <span className={`text-[9px] uppercase tracking-widest font-semibold px-1.5 py-0.5 rounded ${badge.bg} ${badge.fg} shrink-0`}>{badge.label}</span>
                  </button>
                );
              })}
            </div>
          )}

          <form onSubmit={submit} className="space-y-4 mt-6">
            <div>
              <Label htmlFor="username">Usuário</Label>
              <Input data-testid="user-username-input" id="username" required value={username} onChange={(e) => setUsername(e.target.value)} className="mt-1 h-11" placeholder="ex.: joao" />
            </div>
            <div>
              <Label htmlFor="password">Senha</Label>
              <Input data-testid="user-password-input" id="password" type="password" required value={password} onChange={(e) => setPassword(e.target.value)} className="mt-1 h-11" placeholder="••••••••" />
            </div>
            <Button data-testid="user-login-submit-btn" type="submit" disabled={busy} className="w-full h-11 bg-[#F05D23] hover:bg-[#D94E1B] text-white font-semibold">
              {busy ? "Entrando…" : "Entrar"}
            </Button>
          </form>

          <div className="mt-6 text-center">
            <Link to="/login/company" className="text-sm text-zinc-500 hover:text-[#F05D23]" data-testid="back-to-company-btn">← Trocar de empresa</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
