import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { toast } from "sonner";
import { Building2, Upload } from "lucide-react";

const empty = { name: "", cnpj: "", ie: "", address: "", phone: "", email: "", logo_data_url: "", stock_enabled: false };

export default function Settings() {
  const [form, setForm] = useState(empty);
  const [saving, setSaving] = useState(false);

  useEffect(() => { api.get("/company").then(r => setForm({ ...empty, ...r.data })); }, []);

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
      toast.success("Empresa salva");
    } catch (err) { toast.error(err.response?.data?.detail || "Erro"); }
    finally { setSaving(false); }
  };

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Empresa</h1>
        <p className="text-sm text-zinc-500 mt-1">Estas informações aparecem no cabeçalho do PDF.</p>
      </div>

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
    </div>
  );
}
