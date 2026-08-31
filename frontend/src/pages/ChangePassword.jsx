import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { KeyRound } from "lucide-react";

export default function ChangePassword() {
  const navigate = useNavigate();
  const { user, changePassword } = useAuth();
  const [current, setCurrent] = useState("");
  const [pw, setPw] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (pw !== confirm) { toast.error("Senhas não conferem"); return; }
    if (pw.length < 4) { toast.error("Senha muito curta"); return; }
    setBusy(true);
    try {
      await changePassword(current, pw);
      toast.success("Senha atualizada!");
      navigate("/dashboard", { replace: true });
    } catch (err) {
      toast.error(err.response?.data?.detail || "Falha ao trocar senha");
    } finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen bg-[#FCFCFC] grid place-items-center px-4">
      <div className="w-full max-w-md border border-zinc-200 rounded-lg bg-white p-6 sm:p-8">
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-md bg-[#F05D23] grid place-items-center text-white"><KeyRound className="w-5 h-5" /></div>
          <div>
            <h1 className="font-display text-xl font-semibold">Definir nova senha</h1>
            <p className="text-sm text-zinc-500">{user?.must_change_password ? "Primeira entrada — troque a senha temporária." : "Atualize sua senha."}</p>
          </div>
        </div>

        <form onSubmit={submit} className="mt-6 space-y-4">
          <div>
            <Label>Senha atual</Label>
            <Input data-testid="cp-current-input" type="password" required value={current} onChange={(e) => setCurrent(e.target.value)} className="mt-1 h-11" />
          </div>
          <div>
            <Label>Nova senha</Label>
            <Input data-testid="cp-new-input" type="password" minLength={4} required value={pw} onChange={(e) => setPw(e.target.value)} className="mt-1 h-11" />
          </div>
          <div>
            <Label>Confirmar nova senha</Label>
            <Input data-testid="cp-confirm-input" type="password" minLength={4} required value={confirm} onChange={(e) => setConfirm(e.target.value)} className="mt-1 h-11" />
          </div>
          <Button data-testid="cp-submit-btn" type="submit" disabled={busy} className="w-full h-11 bg-[#F05D23] hover:bg-[#D94E1B] text-white font-semibold">
            {busy ? "Aguarde…" : "Salvar senha"}
          </Button>
        </form>
      </div>
    </div>
  );
}
