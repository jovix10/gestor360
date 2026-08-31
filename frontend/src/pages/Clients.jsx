import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger } from "@/components/ui/dialog";
import { Plus, Pencil, Trash2, Search, Users, Loader2, ScanSearch } from "lucide-react";
import { toast } from "sonner";

const empty = {
  name: "", document: "", ie: "", email: "", phone: "",
  cep: "", street: "", number: "", complement: "",
  district: "", city: "", state: "", address: "", notes: "",
};

export default function Clients() {
  const [rows, setRows] = useState([]);
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(empty);
  const [editing, setEditing] = useState(null);
  const [cepLoading, setCepLoading] = useState(false);
  const [cnpjLoading, setCnpjLoading] = useState(false);

  const load = () => api.get("/clients").then(r => setRows(r.data));
  useEffect(() => { load(); }, []);

  const openNew = () => { setForm(empty); setEditing(null); setOpen(true); };
  const openEdit = (c) => { setForm({ ...empty, ...c }); setEditing(c.id); setOpen(true); };

  const lookupCnpj = async () => {
    const cnpj = String(form.document || "").replace(/\D/g, "");
    if (cnpj.length !== 14) { toast.error("CNPJ deve ter 14 dígitos"); return; }
    setCnpjLoading(true);
    try {
      const r = await fetch(`https://brasilapi.com.br/api/cnpj/v1/${cnpj}`);
      if (!r.ok) { toast.error("CNPJ não encontrado na Receita"); return; }
      const d = await r.json();
      setForm(f => ({
        ...f,
        name: d.razao_social || d.nome_fantasia || f.name,
        cep: (d.cep || "").replace(/\D/g, "") || f.cep,
        street: d.logradouro || f.street,
        number: d.numero || f.number,
        complement: d.complemento || f.complement,
        district: d.bairro || f.district,
        city: d.municipio || f.city,
        state: d.uf || f.state,
        phone: d.ddd_telefone_1 || f.phone,
        email: d.email || f.email,
      }));
      toast.success("Dados da empresa preenchidos automaticamente");
    } catch { toast.error("Erro ao consultar CNPJ"); }
    finally { setCnpjLoading(false); }
  };

  const lookupCep = async (raw) => {
    const cep = String(raw || "").replace(/\D/g, "");
    if (cep.length !== 8) return;
    setCepLoading(true);
    try {
      const r = await fetch(`https://viacep.com.br/ws/${cep}/json/`);
      const d = await r.json();
      if (d.erro) { toast.error("CEP não encontrado"); return; }
      setForm(f => ({
        ...f,
        cep,
        street: d.logradouro || f.street,
        district: d.bairro || f.district,
        city: d.localidade || f.city,
        state: d.uf || f.state,
        complement: d.complemento || f.complement,
      }));
    } catch { toast.error("Erro ao consultar CEP"); }
    finally { setCepLoading(false); }
  };

  const save = async (e) => {
    e.preventDefault();
    try {
      if (editing) await api.put(`/clients/${editing}`, form);
      else await api.post("/clients", form);
      toast.success(editing ? "Cliente atualizado" : "Cliente criado");
      setOpen(false);
      load();
    } catch (err) { toast.error(err.response?.data?.detail || "Erro"); }
  };

  const del = async (id) => {
    if (!confirm("Excluir cliente?")) return;
    await api.delete(`/clients/${id}`);
    toast.success("Cliente removido");
    load();
  };

  const term = q.toLowerCase().trim();
  const filtered = !term ? rows : rows.filter(r =>
    (r.name || "").toLowerCase().includes(term) ||
    (r.document || "").toLowerCase().includes(term) ||
    (r.email || "").toLowerCase().includes(term) ||
    (r.phone || "").toLowerCase().includes(term) ||
    (r.city || "").toLowerCase().includes(term)
  );

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="font-display text-3xl font-semibold tracking-tight">Clientes</h1>
          <p className="text-sm text-zinc-500 mt-1">{rows.length} cadastrado(s)</p>
        </div>
        <div className="flex gap-2 w-full sm:w-auto">
          <div className="relative flex-1 sm:w-80">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400" />
            <Input
              data-testid="client-search-input"
              value={q} onChange={(e) => setQ(e.target.value)}
              placeholder="Buscar por nome, documento, email…"
              className="pl-9 h-11"
            />
            {term && (
              <div className="absolute z-20 mt-1 w-full bg-white border border-zinc-200 rounded-md shadow-lg max-h-72 overflow-auto">
                {filtered.length === 0 ? (
                  <div className="px-3 py-4 text-sm text-zinc-500 text-center">Nenhum resultado</div>
                ) : filtered.slice(0, 8).map(c => (
                  <button
                    key={c.id}
                    type="button"
                    data-testid={`client-suggest-${c.id}`}
                    onMouseDown={(e) => { e.preventDefault(); openEdit(c); setQ(""); }}
                    className="w-full text-left px-3 py-2 hover:bg-[#FDF0EC] flex items-center gap-3"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="font-medium text-sm truncate">{c.name}</div>
                      <div className="text-xs text-zinc-500 truncate">{c.document || c.email || c.phone || "—"}</div>
                    </div>
                    {c.city && <div className="text-xs text-zinc-400">{c.city}/{c.state}</div>}
                  </button>
                ))}
              </div>
            )}
          </div>
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button data-testid="new-client-btn" onClick={openNew} className="h-11 bg-[#F05D23] hover:bg-[#D94E1B]">
                <Plus className="w-4 h-4 mr-1" /> Novo
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
              <DialogHeader><DialogTitle>{editing ? "Editar cliente" : "Novo cliente"}</DialogTitle></DialogHeader>
              <form onSubmit={save} className="space-y-5">
                <section className="space-y-3">
                  <div className="text-xs uppercase tracking-widest text-zinc-500 font-semibold">Identificação</div>
                  <div className="grid grid-cols-6 gap-3">
                    <div className="col-span-4">
                      <Label>CPF / CNPJ</Label>
                      <Input data-testid="client-document-input" value={form.document} onChange={(e) => setForm({ ...form, document: e.target.value })} />
                    </div>
                    <div className="col-span-2 flex items-end">
                      <Button type="button" onClick={lookupCnpj} disabled={cnpjLoading} data-testid="cnpj-lookup-btn" className="w-full h-10 bg-zinc-900 hover:bg-zinc-800 text-white font-semibold">
                        {cnpjLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <><ScanSearch className="w-4 h-4 mr-1" /> Buscar CNPJ</>}
                      </Button>
                    </div>
                  </div>
                  <p className="text-xs text-zinc-500 -mt-2">Digite o CNPJ e clique em Buscar para preencher nome, endereço e contato automaticamente (via Receita Federal).</p>
                  <div><Label>Nome / Razão Social *</Label><Input data-testid="client-name-input" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
                  <div><Label>Inscrição Estadual</Label><Input data-testid="client-ie-input" value={form.ie} onChange={(e) => setForm({ ...form, ie: e.target.value })} placeholder="Isento se não houver" /></div>
                </section>

                <section className="space-y-3">
                  <div className="text-xs uppercase tracking-widest text-zinc-500 font-semibold">Contato</div>
                  <div className="grid grid-cols-2 gap-3">
                    <div><Label>Telefone</Label><Input data-testid="client-phone-input" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></div>
                    <div><Label>Email</Label><Input data-testid="client-email-input" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></div>
                  </div>
                </section>

                <section className="space-y-3">
                  <div className="text-xs uppercase tracking-widest text-zinc-500 font-semibold">Endereço</div>
                  <div className="grid grid-cols-6 gap-3">
                    <div className="col-span-3 sm:col-span-2">
                      <Label>CEP</Label>
                      <div className="relative">
                        <Input
                          data-testid="client-cep-input"
                          value={form.cep}
                          onChange={(e) => setForm({ ...form, cep: e.target.value })}
                          onBlur={(e) => lookupCep(e.target.value)}
                          placeholder="00000-000"
                        />
                        {cepLoading && <Loader2 className="w-4 h-4 absolute right-3 top-1/2 -translate-y-1/2 animate-spin text-zinc-400" />}
                      </div>
                    </div>
                    <div className="col-span-3 sm:col-span-3"><Label>Endereço</Label><Input data-testid="client-street-input" value={form.street} onChange={(e) => setForm({ ...form, street: e.target.value })} /></div>
                    <div className="col-span-6 sm:col-span-1"><Label>Nº</Label><Input data-testid="client-number-input" value={form.number} onChange={(e) => setForm({ ...form, number: e.target.value })} /></div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div><Label>Complemento</Label><Input data-testid="client-complement-input" value={form.complement} onChange={(e) => setForm({ ...form, complement: e.target.value })} /></div>
                    <div><Label>Bairro</Label><Input data-testid="client-district-input" value={form.district} onChange={(e) => setForm({ ...form, district: e.target.value })} /></div>
                  </div>
                  <div className="grid grid-cols-6 gap-3">
                    <div className="col-span-4"><Label>Cidade</Label><Input data-testid="client-city-input" value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} /></div>
                    <div className="col-span-2"><Label>UF</Label><Input data-testid="client-state-input" maxLength={2} value={form.state} onChange={(e) => setForm({ ...form, state: e.target.value.toUpperCase() })} /></div>
                  </div>
                </section>

                <section className="space-y-2">
                  <div className="text-xs uppercase tracking-widest text-zinc-500 font-semibold">Observações</div>
                  <Textarea rows={2} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
                </section>

                <DialogFooter>
                  <Button data-testid="save-client-btn" type="submit" className="bg-[#F05D23] hover:bg-[#D94E1B]">Salvar</Button>
                </DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="border border-dashed border-zinc-300 rounded-lg p-12 text-center">
          <Users className="w-8 h-8 mx-auto text-zinc-300" />
          <p className="mt-3 text-sm text-zinc-500">Nenhum cliente encontrado.</p>
        </div>
      ) : (
        <>
          <div className="hidden md:block border border-zinc-200 rounded-lg overflow-hidden bg-white">
            <table className="w-full text-sm">
              <thead className="bg-zinc-50 text-zinc-600 text-xs uppercase tracking-wider">
                <tr>
                  <th className="text-left px-4 py-3">Nome</th>
                  <th className="text-left px-4 py-3">Documento</th>
                  <th className="text-left px-4 py-3">Cidade</th>
                  <th className="text-left px-4 py-3">Contato</th>
                  <th className="text-right px-4 py-3">Ações</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((c) => (
                  <tr key={c.id} className="border-t border-zinc-100 hover:bg-zinc-50">
                    <td className="px-4 py-3 font-medium text-zinc-900">{c.name}</td>
                    <td className="px-4 py-3 font-mono-num text-zinc-600">{c.document || "—"}</td>
                    <td className="px-4 py-3 text-zinc-600">{c.city ? `${c.city}/${c.state || ""}` : "—"}</td>
                    <td className="px-4 py-3 text-zinc-600">{c.email || c.phone || "—"}</td>
                    <td className="px-4 py-3 text-right">
                      <button data-testid={`edit-client-${c.id}`} onClick={() => openEdit(c)} className="inline-flex items-center justify-center w-8 h-8 rounded hover:bg-zinc-100 text-zinc-500 hover:text-zinc-900"><Pencil className="w-4 h-4" /></button>
                      <button data-testid={`delete-client-${c.id}`} onClick={() => del(c.id)} className="ml-1 inline-flex items-center justify-center w-8 h-8 rounded hover:bg-red-50 text-zinc-500 hover:text-red-600"><Trash2 className="w-4 h-4" /></button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="md:hidden space-y-3">
            {filtered.map((c) => (
              <div key={c.id} className="border border-zinc-200 rounded-lg bg-white p-4">
                <div className="flex items-start justify-between">
                  <div className="min-w-0">
                    <div className="font-semibold">{c.name}</div>
                    <div className="text-xs text-zinc-500 mt-0.5 font-mono-num">{c.document || "—"}</div>
                    <div className="text-xs text-zinc-500 mt-1">{c.city ? `${c.city}/${c.state || ""}` : c.email || c.phone || "—"}</div>
                  </div>
                  <div className="flex gap-1">
                    <button onClick={() => openEdit(c)} className="w-8 h-8 rounded hover:bg-zinc-100 grid place-items-center"><Pencil className="w-4 h-4" /></button>
                    <button onClick={() => del(c.id)} className="w-8 h-8 rounded hover:bg-red-50 grid place-items-center text-red-500"><Trash2 className="w-4 h-4" /></button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
