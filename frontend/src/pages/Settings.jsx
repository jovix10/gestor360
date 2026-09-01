import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { toast } from "sonner";
import { Building2, Upload, KeyRound, Shield } from "lucide-react";

const empty = { name: "", cnpj: "", ie: "", address: "", phone: "", email: "", logo_data_url: "", stock_enabled: false };

export default function Settings() {
  const { user, isOwner, checkAuth } = useAuth();
  const [form, setForm] = useState(empty);
  const [saving, setSaving] = useState(false);
  // credentials tab
  const [curPw, setCurPw] = useState("");
  const [newCode, setNewCode] = useState("");
  const [newPw, setNewPw] = useState("");
  const [newPwConfirm, setNewPwConfirm] = useState("");
  const [credSaving, setCredSaving] = useState(false);

  useEffect(() => {
    api.get("/company").then(r => setForm({ ...empty, ...r.data }));
  }, []);

  const upload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 800 * 1024) { toast.error("Logo até 800KB"); return; }
    const reader = new FileReader();
    reader.onload = () => setForm({ ...form, logo_data_url: reader.result });
    reader.readAsDataURL(file);
  };

  const save = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api.put("/company", form);
      await checkAuth();
      toast.success("Empresa salva");
    } catch (err) { toast.error(err.response?.data?.detail || "Erro"); }
    finally { setSaving(false); }
  };

  const saveCredentials = async (e) => {
    e.preventDefault();
    if (!newCode && !newPw) { toast.error("Informe um novo código ou nova senha"); return; }
    if (newPw && newPw !== newPwConfirm) { toast.error("Senhas não conferem"); return; }
    setCredSaving(true);
    try {
      const { data } = await api.post("/company/change-credentials", {
        current_password: curPw,
        new_code: newCode || undefined,
        new_password: newPw || undefined,
      });
      toast.success(`Acesso atualizado! Código: ${data.code}`);
      setCurPw(""); setNewCode(""); setNewPw(""); setNewPwConfirm("");
      await checkAuth();
    } catch (err) { toast.error(err.response?.data?.detail || "Erro ao atualizar"); }
    finally { setCredSaving(false); }
  };

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Empresa</h1>
        <p className="text-sm text-zinc-500 mt-1">
          Dados que aparecem no PDF e configuração de acesso da empresa.
        </p>
        {user?.company?.code && (
          <div className="mt-3 inline-flex items-center gap-2 bg-zinc-50 border border-zinc-200 rounded-md px-3 py-1.5">
            <Building2 className="w-3.5 h-3.5 text-zinc-500" />
            <span className="text-xs text-zinc-500">Código atual:</span>
            <span className="font-mono-num text-sm font-semibold">{user.company.code}</span>
          </div>
        )}
      </div>

      <Tabs defaultValue="dados">
        <TabsList>
          <TabsTrigger data-testid="tab-empresa-dados" value="dados">Dados</TabsTrigger>
          {isOwner && <TabsTrigger data-testid="tab-empresa-acesso" value="acesso">Acesso</TabsTrigger>}
        </TabsList>

        <TabsContent value="dados" className="mt-6">
          <form onSubmit={save} className="border border-zinc-200 rounded-lg bg-white p-6 space-y-5">
            <div className="grid md:grid-cols-3 gap-6">
              <div className="md:col-span-1 flex flex-col items-center gap-3">
                <div className="w-32 h-32 rounded-lg bg-zinc-50 border border-dashed border-zinc-300 grid place-items-center overflow-hidden">
                  {form.logo_data_url ? (
                    <img src={form.logo_data_url} alt="logo" className="w-full h-full object-contain" />
                  ) : (
                    <Building2 className="w-8 h-8 text-zinc-300" />
                  )}
                </div>
                <label className="cursor-pointer inline-flex items-center gap-2 text-sm text-[#F05D23] font-semibold hover:underline">
                  <Upload className="w-4 h-4" />
                  <span>Trocar logo</span>
                  <input data-testid="logo-input" type="file" accept="image/*" onChange={upload} className="hidden" />
                </label>
                {form.logo_data_url && (
                  <button type="button" onClick={() => setForm({ ...form, logo_data_url: "" })} className="text-xs text-zinc-500 hover:text-red-600">
                    Remover
                  </button>
                )}
              </div>

              <div className="md:col-span-2 space-y-4">
                <div>
                  <Label>Razão social / Nome fantasia *</Label>
                  <Input data-testid="company-name-input" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="mt-1" />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div><Label>CNPJ</Label><Input data-testid="company-cnpj-input" value={form.cnpj} onChange={(e) => setForm({ ...form, cnpj: e.target.value })} className="mt-1" /></div>
                  <div><Label>Inscrição Estadual</Label><Input data-testid="company-ie-input" value={form.ie || ""} onChange={(e) => setForm({ ...form, ie: e.target.value })} className="mt-1" placeholder="Isento se não houver" /></div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div><Label>Telefone</Label><Input data-testid="company-phone-input" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} className="mt-1" /></div>
                  <div><Label>Email</Label><Input data-testid="company-email-input" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className="mt-1" /></div>
                </div>
                <div><Label>Endereço</Label><Input data-testid="company-address-input" value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} className="mt-1" /></div>
              </div>
            </div>

            <div className="border-t border-zinc-100 pt-5 flex items-center justify-between">
              <div>
                <div className="font-semibold">Controle de estoque</div>
                <p className="text-sm text-zinc-500">Ative se sua empresa controla quantidade em estoque. Vendas baixam o estoque automaticamente.</p>
              </div>
              <Switch data-testid="stock-toggle" checked={form.stock_enabled} onCheckedChange={(v) => setForm({ ...form, stock_enabled: v })} />
            </div>

            <div className="flex justify-end">
              <Button data-testid="save-company-btn" type="submit" disabled={saving} className="bg-[#F05D23] hover:bg-[#D94E1B] h-11 px-6">
                {saving ? "Salvando…" : "Salvar"}
              </Button>
            </div>
          </form>
        </TabsContent>

        {isOwner && (
          <TabsContent value="acesso" className="mt-6">
            <form onSubmit={saveCredentials} className="border border-zinc-200 rounded-lg bg-white p-6 space-y-5">
              <div className="flex items-start gap-3 p-3 bg-[#FDF0EC] border border-[#F05D23]/20 rounded-md">
                <Shield className="w-5 h-5 text-[#F05D23] shrink-0 mt-0.5" />
                <div className="text-sm text-zinc-700">
                  <b>Cuidado:</b> ao mudar o código ou a senha da empresa, todos os usuários da equipe precisarão do novo código para entrar. Você não perde acesso — continua entrando pelo <i>login do dono</i>.
                </div>
              </div>

              <div>
                <Label>Senha atual da empresa *</Label>
                <Input data-testid="cred-current-password" required type="password" value={curPw} onChange={(e) => setCurPw(e.target.value)} className="mt-1 h-11" />
                <p className="text-xs text-zinc-500 mt-1">Confirme sua senha atual para autorizar a mudança.</p>
              </div>

              <div className="grid md:grid-cols-2 gap-5 border-t border-zinc-100 pt-5">
                <div>
                  <Label>Novo código da empresa</Label>
                  <Input data-testid="cred-new-code" value={newCode} onChange={(e) => setNewCode(e.target.value)} className="mt-1 h-11 font-mono-num" placeholder="ex.: neto-materiais" />
                  <p className="text-xs text-zinc-500 mt-1">Deixe em branco para manter <span className="font-semibold">{user?.company?.code || "—"}</span>. Espaços/acentos são convertidos automaticamente.</p>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label>Nova senha</Label>
                    <Input data-testid="cred-new-password" type="password" minLength={4} value={newPw} onChange={(e) => setNewPw(e.target.value)} className="mt-1 h-11" />
                  </div>
                  <div>
                    <Label>Confirmar</Label>
                    <Input data-testid="cred-new-password-confirm" type="password" minLength={4} value={newPwConfirm} onChange={(e) => setNewPwConfirm(e.target.value)} className="mt-1 h-11" />
                  </div>
                </div>
              </div>

              <div className="flex justify-end">
                <Button data-testid="save-credentials-btn" type="submit" disabled={credSaving} className="bg-[#F05D23] hover:bg-[#D94E1B] h-11 px-6">
                  <KeyRound className="w-4 h-4 mr-2" />
                  {credSaving ? "Salvando…" : "Atualizar acesso"}
                </Button>
              </div>
            </form>
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
}
