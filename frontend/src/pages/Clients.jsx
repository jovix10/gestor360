import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger } from "@/components/ui/dialog";
import { Plus, Pencil, Trash2, Search, Users } from "lucide-react";
import { toast } from "sonner";

const empty = { name: "", document: "", email: "", phone: "", address: "", notes: "" };

export default function Clients() {
  const [rows, setRows] = useState([]);
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(empty);
  const [editing, setEditing] = useState(null);

  const load = () => api.get("/clients").then(r => setRows(r.data));
  useEffect(() => { load(); }, []);

  const openNew = () => { setForm(empty); setEditing(null); setOpen(true); };
  const openEdit = (c) => { setForm(c); setEditing(c.id); setOpen(true); };

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

  const filtered = rows.filter(r =>
    !q || r.name.toLowerCase().includes(q.toLowerCase()) || r.document?.toLowerCase().includes(q.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="font-display text-3xl font-semibold tracking-tight">Clientes</h1>
          <p className="text-sm text-zinc-500 mt-1">{rows.length} cadastrado(s)</p>
        </div>
        <div className="flex gap-2 w-full sm:w-auto">
          <div className="relative flex-1 sm:w-72">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400" />
            <Input data-testid="client-search-input" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Buscar por nome ou CPF/CNPJ" className="pl-9 h-11" />
          </div>
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button data-testid="new-client-btn" onClick={openNew} className="h-11 bg-[#F05D23] hover:bg-[#D94E1B]">
                <Plus className="w-4 h-4 mr-1" /> Novo
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-lg">
              <DialogHeader><DialogTitle>{editing ? "Editar cliente" : "Novo cliente"}</DialogTitle></DialogHeader>
              <form onSubmit={save} className="space-y-3">
                <div><Label>Nome *</Label><Input data-testid="client-name-input" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
                <div className="grid grid-cols-2 gap-3">
                  <div><Label>CPF/CNPJ</Label><Input data-testid="client-document-input" value={form.document} onChange={(e) => setForm({ ...form, document: e.target.value })} /></div>
                  <div><Label>Telefone</Label><Input data-testid="client-phone-input" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></div>
                </div>
                <div><Label>Email</Label><Input data-testid="client-email-input" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></div>
                <div><Label>Endereço</Label><Input data-testid="client-address-input" value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} /></div>
                <div><Label>Observações</Label><Textarea rows={2} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></div>
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
          {/* Desktop table */}
          <div className="hidden md:block border border-zinc-200 rounded-lg overflow-hidden bg-white">
            <table className="w-full text-sm">
              <thead className="bg-zinc-50 text-zinc-600 text-xs uppercase tracking-wider">
                <tr>
                  <th className="text-left px-4 py-3">Nome</th>
                  <th className="text-left px-4 py-3">Documento</th>
                  <th className="text-left px-4 py-3">Contato</th>
                  <th className="text-right px-4 py-3">Ações</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((c) => (
                  <tr key={c.id} className="border-t border-zinc-100 hover:bg-zinc-50">
                    <td className="px-4 py-3 font-medium text-zinc-900">{c.name}</td>
                    <td className="px-4 py-3 font-mono-num text-zinc-600">{c.document || "—"}</td>
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
          {/* Mobile cards */}
          <div className="md:hidden space-y-3">
            {filtered.map((c) => (
              <div key={c.id} className="border border-zinc-200 rounded-lg bg-white p-4">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="font-semibold">{c.name}</div>
                    <div className="text-xs text-zinc-500 mt-0.5 font-mono-num">{c.document || "—"}</div>
                    <div className="text-xs text-zinc-500 mt-1">{c.email || c.phone || "—"}</div>
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
