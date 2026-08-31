import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Building2 } from "lucide-react";

export default function CompanyLogin() {
  const navigate = useNavigate();
  const { companyLogin } = useAuth();
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [companyName, setCompanyName] = useState("");

  const onCodeBlur = async (e) => {
    const v = e.target.value.trim();
    if (!v) { setCompanyName(""); return; }
    try {
      const { data } = await api.get(`/auth/lookup-company?code=${encodeURIComponent(v)}`);
      if (data.found) setCompanyName(data.name);
      else setCompanyName("");
    } catch { setCompanyName(""); }
  };

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const data = await companyLogin(code, password);
      navigate("/login/user", { state: data });
    } catch (err) {
      toast.error(err.response?.data?.detail || "Falha ao entrar");
    } finally { setBusy(false); }
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
            <div className="text-xs uppercase tracking-widest text-[#F05D23] font-semibold">Etapa 1 de 2</div>
            <h1 className="mt-3 font-display text-5xl xl:text-6xl font-bold leading-tight tracking-tight">
              Entre na<br /><span className="text-[#F05D23]">sua empresa.</span>
            </h1>
            <p className="mt-6 text-zinc-300 max-w-md">Cada empresa tem seu código único. Um só espaço, vários usuários, cada um com sua função.</p>
          </div>
          <div className="text-xs text-zinc-500">© 2026 Gestor360</div>
        </div>
      </div>

      <div className="flex items-center justify-center p-6 sm:p-10">
        <div className="w-full max-w-sm">
          <div className="lg:hidden flex items-center gap-3 mb-8">
            <div className="w-10 h-10 rounded-md bg-[#F05D23] grid place-items-center font-display font-bold text-white text-lg">G</div>
            <span className="font-display text-xl font-semibold">Gestor360</span>
          </div>
          <div className="flex items-center gap-2 text-xs uppercase tracking-widest font-semibold text-zinc-400">
            <span className="w-6 h-6 rounded-full bg-[#F05D23] text-white grid place-items-center text-xs">1</span>
            Empresa
            <span className="text-zinc-300">→</span>
            <span className="w-6 h-6 rounded-full bg-zinc-200 text-zinc-500 grid place-items-center text-xs">2</span>
            Usuário
          </div>
          <h2 className="mt-6 font-display text-3xl font-semibold text-zinc-900">Acessar empresa</h2>
          <p className="text-sm text-zinc-500 mt-1">Digite o código e a senha da sua empresa.</p>

          <form onSubmit={submit} className="space-y-4 mt-8">
            <div>
              <Label htmlFor="code">Código da empresa</Label>
              <Input data-testid="company-code-input" id="code" required value={code} onChange={(e) => setCode(e.target.value)} onBlur={onCodeBlur} className="mt-1 h-11" placeholder="ex.: neto-materiais" />
              {companyName && (
                <div className="mt-2 text-xs text-zinc-500 inline-flex items-center gap-1">
                  <Building2 className="w-3 h-3" /> {companyName}
                </div>
              )}
            </div>
            <div>
              <Label htmlFor="password">Senha da empresa</Label>
              <Input data-testid="company-password-input" id="password" type="password" required value={password} onChange={(e) => setPassword(e.target.value)} className="mt-1 h-11" placeholder="••••••••" />
            </div>
            <Button data-testid="company-login-submit-btn" type="submit" disabled={busy} className="w-full h-11 bg-[#F05D23] hover:bg-[#D94E1B] text-white font-semibold">
              {busy ? "Aguarde…" : "Continuar"}
            </Button>
          </form>

          <div className="mt-6 pt-6 border-t border-zinc-100 space-y-2 text-sm text-center">
            <p className="text-zinc-500">
              É o dono da empresa? <Link to="/login/owner" className="text-[#F05D23] font-semibold hover:underline">Entrar como dono</Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
