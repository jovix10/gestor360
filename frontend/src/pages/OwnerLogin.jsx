import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";

export default function OwnerLogin() {
  const navigate = useNavigate();
  const { ownerLogin, register } = useAuth();
  const [mode, setMode] = useState("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const data = mode === "login" ? await ownerLogin(email, password) : await register(name, email, password);
      if (data.must_change_password) navigate("/change-password", { replace: true });
      else navigate("/dashboard", { replace: true });
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
            <div className="text-xs uppercase tracking-widest text-[#F05D23] font-semibold">Acesso do dono</div>
            <h1 className="mt-3 font-display text-5xl xl:text-6xl font-bold leading-tight tracking-tight">
              Entrar<br /><span className="text-[#F05D23]">direto.</span>
            </h1>
            <p className="mt-6 text-zinc-300 max-w-md">Como dono, você entra com seu email e senha, sem precisar do código da empresa.</p>
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
          <h2 className="font-display text-3xl font-semibold text-zinc-900">
            {mode === "login" ? "Acesso do dono" : "Nova empresa"}
          </h2>
          <p className="text-sm text-zinc-500 mt-1">
            {mode === "login" ? "Entre para configurar sua empresa." : "Crie sua empresa em segundos."}
          </p>

          <form onSubmit={submit} className="space-y-4 mt-8">
            {mode === "register" && (
              <div>
                <Label htmlFor="name">Seu nome</Label>
                <Input data-testid="register-name-input" id="name" value={name} onChange={(e) => setName(e.target.value)} required className="mt-1 h-11" />
              </div>
            )}
            <div>
              <Label htmlFor="email">Email</Label>
              <Input data-testid="owner-email-input" id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required className="mt-1 h-11" />
            </div>
            <div>
              <Label htmlFor="password">Senha</Label>
              <Input data-testid="owner-password-input" id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required className="mt-1 h-11" />
            </div>
            <Button data-testid="owner-login-submit-btn" type="submit" disabled={busy} className="w-full h-11 bg-[#F05D23] hover:bg-[#D94E1B] text-white font-semibold">
              {busy ? "Aguarde…" : mode === "login" ? "Entrar" : "Criar empresa"}
            </Button>
          </form>

          <p className="mt-6 text-sm text-center text-zinc-500">
            {mode === "login" ? "Não tem empresa?" : "Já tem empresa?"}{" "}
            <button data-testid="toggle-auth-mode-btn" onClick={() => setMode(mode === "login" ? "register" : "login")} className="text-[#F05D23] font-semibold hover:underline">
              {mode === "login" ? "Criar agora" : "Entrar"}
            </button>
          </p>
          <div className="mt-3 text-center">
            <Link to="/login/company" className="text-sm text-zinc-500 hover:text-[#F05D23]">← Entrar pela empresa</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
