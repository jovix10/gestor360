import { useEffect, useState } from "react";
import { api, fmtMoney } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger } from "@/components/ui/dialog";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Plus, Pencil, Trash2, Search, Package } from "lucide-react";
import { toast } from "sonner";

const UNITS = ["UN", "PC", "PAR", "KG", "G", "LT", "ML", "MT", "CM", "M2", "M3", "PCT", "CX", "DZ", "RL", "SC"];

const empty = { code: "", description: "", price: 0, stock: 0, unit: "UN" };

export default function Products() {
  const [rows, setRows] = useState([]);
  const [company, setCompany] = useState(null);
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(empty);
  const [editing, setEditing] = useState(null);

  const load = () => api.get("/products").then(r => setRows(r.data));
  useEffect(() => {
    load();
    api.get("/company").then(r => setCompany(r.data));
  }, []);

  const openNew = () => { setForm(empty); setEditing(null); setOpen(true); };
  const openEdit = (p) => { setForm(p); setEditing(p.id); setOpen(true); };

  const save = async (e) => {
    e.preventDefault();
    try {
      if (editing) await api.put(`/products/${editing}`, form);
      else await api.post("/products", form);
      toast.success(editing ? "Produto atualizado" : "Produto criado");
      setOpen(false);
      load();
    } catch (err) { toast.error(err.response?.data?.detail || "Erro"); }
  };

  const del = async (id) => {
    if (!confirm("Excluir produto?")) return;
    await api.delete(`/products/${id}`);
    load();
  };

  const filtered = rows.filter(r =>
    !q || r.description.toLowerCase().includes(q.toLowerCase()) || r.code.toLowerCase().includes(q.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="font-display text-3xl font-semibold tracking-tight">Produtos</h1>
          <p className="text-sm text-zinc-500 mt-1">{rows.length} cadastrado(s) · Estoque {company?.stock_enabled ? "ativado" : "desativado"}</p>
        </div>
        <div className="flex gap-2 w-full sm:w-auto">
          <div className="relative flex-1 sm:w-72">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400" />
            <Input data-testid="product-search-input" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Buscar por código ou descrição" className="pl-9 h-11" />
          </div>
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button data-testid="new-product-btn" onClick={openNew} className="h-11 bg-[#F05D23] hover:bg-[#D94E1B]">
                <Plus className="w-4 h-4 mr-1" /> Novo
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-lg">
              <DialogHeader><DialogTitle>{editing ? "Editar produto" : "Novo produto"}</DialogTitle></DialogHeader>
              <form onSubmit={save} className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div><Label>Código *</Label><Input data-testid="product-code-input" required value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} /></div>
                  <div>
                    <Label>Unidade de medida</Label>
                    <Select value={form.unit} onValueChange={(v) => setForm({ ...form, unit: v })}>
                      <SelectTrigger data-testid="product-unit-select" className="mt-0"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {UNITS.map(u => <SelectItem key={u} value={u} data-testid={`unit-option-${u}`}>{u}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div><Label>Descrição *</Label><Input data-testid="product-description-input" required value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></div>
                <div className="grid grid-cols-2 gap-3">
                  <div><Label>Preço de tabela (R$) *</Label><Input data-testid="product-price-input" type="number" step="0.01" required value={form.price} onChange={(e) => setForm({ ...form, price: parseFloat(e.target.value) || 0 })} /></div>
                  {company?.stock_enabled && (
                    <div><Label>Estoque</Label><Input data-testid="product-stock-input" type="number" step="1" value={form.stock} onChange={(e) => setForm({ ...form, stock: parseFloat(e.target.value) || 0 })} /></div>
                  )}
                </div>
                <DialogFooter>
                  <Button data-testid="save-product-btn" type="submit" className="bg-[#F05D23] hover:bg-[#D94E1B]">Salvar</Button>
                </DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="border border-dashed border-zinc-300 rounded-lg p-12 text-center">
          <Package className="w-8 h-8 mx-auto text-zinc-300" />
          <p className="mt-3 text-sm text-zinc-500">Nenhum produto encontrado.</p>
        </div>
      ) : (
        <>
          <div className="hidden md:block border border-zinc-200 rounded-lg overflow-hidden bg-white">
            <table className="w-full text-sm">
              <thead className="bg-zinc-50 text-zinc-600 text-xs uppercase tracking-wider">
                <tr>
                  <th className="text-left px-4 py-3">Código</th>
                  <th className="text-left px-4 py-3">Descrição</th>
                  <th className="text-right px-4 py-3">Preço</th>
                  {company?.stock_enabled && <th className="text-right px-4 py-3">Estoque</th>}
                  <th className="text-right px-4 py-3">Ações</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((p) => (
                  <tr key={p.id} className="border-t border-zinc-100 hover:bg-zinc-50">
                    <td className="px-4 py-3 font-mono-num text-zinc-900">{p.code}</td>
                    <td className="px-4 py-3 text-zinc-700">{p.description}</td>
                    <td className="px-4 py-3 text-right font-mono-num">{fmtMoney(p.price)}</td>
                    {company?.stock_enabled && <td className="px-4 py-3 text-right font-mono-num">{p.stock} {p.unit}</td>}
                    <td className="px-4 py-3 text-right">
                      <button data-testid={`edit-product-${p.id}`} onClick={() => openEdit(p)} className="w-8 h-8 rounded hover:bg-zinc-100 inline-grid place-items-center text-zinc-500 hover:text-zinc-900"><Pencil className="w-4 h-4" /></button>
                      <button data-testid={`delete-product-${p.id}`} onClick={() => del(p.id)} className="ml-1 w-8 h-8 rounded hover:bg-red-50 inline-grid place-items-center text-zinc-500 hover:text-red-600"><Trash2 className="w-4 h-4" /></button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="md:hidden space-y-3">
            {filtered.map((p) => (
              <div key={p.id} className="border border-zinc-200 rounded-lg bg-white p-4">
                <div className="flex items-start justify-between">
                  <div className="min-w-0">
                    <div className="font-mono-num text-xs text-zinc-500">{p.code}</div>
                    <div className="font-semibold mt-1 truncate">{p.description}</div>
                    <div className="font-mono-num text-sm mt-1">{fmtMoney(p.price)}</div>
                    {company?.stock_enabled && <div className="text-xs text-zinc-500 mt-1">Estoque: {p.stock} {p.unit}</div>}
                  </div>
                  <div className="flex gap-1">
                    <button onClick={() => openEdit(p)} className="w-8 h-8 rounded hover:bg-zinc-100 grid place-items-center"><Pencil className="w-4 h-4" /></button>
                    <button onClick={() => del(p.id)} className="w-8 h-8 rounded hover:bg-red-50 grid place-items-center text-red-500"><Trash2 className="w-4 h-4" /></button>
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
