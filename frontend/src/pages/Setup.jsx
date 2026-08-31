import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Rocket } from "lucide-react";

export default function Setup() {
  const navigate = useNavigate();
  const { user, setupCompany } = useAuth();
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (user?.company && !user.company.pending_setup) navigate("/dashboard", { replace: true });
    if (user?.company?.name && !name) setName(user.company.name.replace(/ — Empresa$/, ""));
  }, [user, navigate, name]);

  const submit = async (e) => {
    e.preventDefault();
    if (password !== confirm) { toast.error("Senhas não conferem"); return; }
    setBusy(true);
    try {
      await setupCompany(code, password, name);
      toast.success("Empresa configurada! A partir de agora todos entram pela tela da empresa.");
      navigate("/dashboard", { replace: true });
    } catch (err) {
      toast.error(err.response?.data?.detail || "Falha ao configurar");
    } finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen bg-[#FCFCFC] py-10 px-4 sm:px-6">
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center gap-3 mb-8">
          <div className="w-11 h-11 rounded-md bg-[#F05D23] grid place-items-center text-white"><Rocket className="w-5 h-5" /></div>
          <div>
            <div className="text-xs uppercase tracking-widest text-[#F05D23] font-semibold">Configuração inicial</div>
            <h1 className="font-display text-2xl sm:text-3xl font-semibold tracking-tight">Ative sua empresa no Gestor360</h1>
          </div>
        </div>

        <div className="border border-zinc-200 rounded-lg bg-white p-6 sm:p-8">
          <p className="text-sm text-zinc-600">
            Antes de convidar sua equipe, defina um <b>código de empresa</b> (que todo mundo digita na tela de login) e uma <b>senha da empresa</b>. Você continua entrando com seu email/Google — sua equipe entra em duas etapas.
          </p>

          <form onSubmit={submit} className="mt-8 space-y-5">
            <div>
              <Label>Nome da empresa</Label>
              <Input data-testid="setup-name-input" required value={name} onChange={(e) => setName(e.target.value)} className="mt-1 h-11" placeholder="Ex.: Neto Materiais" />
            </div>
            <div>
              <Label>Código da empresa</Label>
              <Input data-testid="setup-code-input" required value={code} onChange={(e) => setCode(e.target.value)} className="mt-1 h-11 font-mono-num" placeholder="ex.: neto-materiais" />
              <p className="text-xs text-zinc-500 mt-1">Só letras minúsculas, números e hífen. Mínimo 3 caracteres.</p>
            </div>
            <div className="grid sm:grid-cols-2 gap-4">
              <div>
                <Label>Senha da empresa</Label>
                <Input data-testid="setup-password-input" type="password" required minLength={4} value={password} onChange={(e) => setPassword(e.target.value)} className="mt-1 h-11" />
              </div>
              <div>
                <Label>Confirmar senha</Label>
                <Input data-testid="setup-confirm-input" type="password" required minLength={4} value={confirm} onChange={(e) => setConfirm(e.target.value)} className="mt-1 h-11" />
              </div>
            </div>

            <div className="pt-4 flex justify-end">
              <Button data-testid="setup-submit-btn" type="submit" disabled={busy} className="h-11 px-6 bg-[#F05D23] hover:bg-[#D94E1B] text-white font-semibold">
                {busy ? "Salvando…" : "Ativar empresa"}
              </Button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
