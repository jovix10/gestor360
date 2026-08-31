import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";

export default function Login() {
  const { loginJwt, register } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState("login"); // login | register
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      if (mode === "login") await loginJwt(email, password);
      else await register(name, email, password);
      navigate("/dashboard");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Falha na autenticação");
    } finally {
      setBusy(false);
    }
  };

  const googleLogin = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + "/dashboard";
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-white">
      {/* Left showcase */}
      <div className="hidden lg:flex relative overflow-hidden bg-[#09090B]">
        <div className="absolute inset-0 grain opacity-30" />
        <div
          className="absolute inset-0 bg-cover bg-center opacity-40"
          style={{ backgroundImage: "url('https://images.unsplash.com/photo-1775810985509-c002017e149f?crop=entropy&cs=srgb&fm=jpg&q=85&w=1600')" }}
        />
        <div className="absolute inset-0 bg-gradient-to-tr from-[#09090B] via-transparent to-transparent" />
        <div className="relative z-10 flex flex-col justify-between p-14 text-white w-full">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-md bg-[#F05D23] grid place-items-center font-display font-bold text-white text-lg">G</div>
            <span className="font-display text-xl font-semibold">Gestor360</span>
          </div>
          <div>
            <h1 className="font-display text-5xl xl:text-6xl font-bold leading-tight tracking-tight">
              Vendas mais rápidas.<br />
              <span className="text-[#F05D23]">Menos ruído.</span>
            </h1>
            <p className="mt-6 text-zinc-300 max-w-md">
              Cadastre clientes, produtos, monte orçamentos como uma planilha e emita PDFs profissionais em segundos.
            </p>
          </div>
          <div className="text-xs text-zinc-500">© 2026 Gestor360</div>
        </div>
      </div>

      {/* Right form */}
      <div className="flex items-center justify-center p-6 sm:p-10">
        <div className="w-full max-w-sm">
          <div className="lg:hidden flex items-center gap-3 mb-8">
            <div className="w-10 h-10 rounded-md bg-[#F05D23] grid place-items-center font-display font-bold text-white text-lg">G</div>
            <span className="font-display text-xl font-semibold">Gestor360</span>
          </div>
          <h2 className="font-display text-3xl font-semibold text-zinc-900">
            {mode === "login" ? "Bem-vindo de volta" : "Criar conta"}
          </h2>
          <p className="text-sm text-zinc-500 mt-1">
            {mode === "login" ? "Acesse sua conta para continuar." : "Comece a organizar sua operação hoje."}
          </p>

          <Button
            data-testid="google-login-btn"
            onClick={googleLogin}
            variant="outline"
            className="w-full mt-8 h-11 border-zinc-200 hover:border-zinc-900 hover:bg-white"
          >
            <svg viewBox="0 0 24 24" className="w-4 h-4 mr-2">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84C6.71 7.31 9.14 5.38 12 5.38z"/>
            </svg>
            Continuar com Google
          </Button>

          <div className="my-6 flex items-center gap-4">
            <div className="h-px flex-1 bg-zinc-200" />
            <span className="text-xs uppercase tracking-wider text-zinc-400">ou</span>
            <div className="h-px flex-1 bg-zinc-200" />
          </div>

          <form onSubmit={submit} className="space-y-4">
            {mode === "register" && (
              <div>
                <Label htmlFor="name">Nome</Label>
                <Input
                  data-testid="register-name-input"
                  id="name" value={name} onChange={(e) => setName(e.target.value)}
                  required className="mt-1 h-11" placeholder="Seu nome"
                />
              </div>
            )}
            <div>
              <Label htmlFor="email">Email</Label>
              <Input
                data-testid="login-email-input"
                id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                required className="mt-1 h-11" placeholder="voce@empresa.com"
              />
            </div>
            <div>
              <Label htmlFor="password">Senha</Label>
              <Input
                data-testid="login-password-input"
                id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                required className="mt-1 h-11" placeholder="••••••••"
              />
            </div>
            <Button
              data-testid="login-submit-btn"
              type="submit" disabled={busy}
              className="w-full h-11 bg-[#F05D23] hover:bg-[#D94E1B] text-white font-semibold"
            >
              {busy ? "Aguarde…" : mode === "login" ? "Entrar" : "Criar conta"}
            </Button>
          </form>

          <p className="mt-6 text-sm text-center text-zinc-500">
            {mode === "login" ? "Não tem conta?" : "Já tem conta?"}{" "}
            <button
              data-testid="toggle-auth-mode-btn"
              onClick={() => setMode(mode === "login" ? "register" : "login")}
              className="text-[#F05D23] font-semibold hover:underline"
            >
              {mode === "login" ? "Criar conta" : "Entrar"}
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}
