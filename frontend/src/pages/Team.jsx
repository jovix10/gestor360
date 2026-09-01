import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger } from "@/components/ui/dialog";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Plus, Pencil, Trash2, KeyRound, UsersRound } from "lucide-react";
import { toast } from "sonner";

const ROLE_BADGE = {
  owner: { label: "Dono", bg: "bg-[#F05D23]/10", fg: "text-[#F05D23]" },
  gerente: { label: "Gerente", bg: "bg-zinc-900/10", fg: "text-zinc-900" },
  vendedor: { label: "Vendedor", bg: "bg-zinc-100", fg: "text-zinc-700" },
};

const emptyForm = { name: "", username: "", email: "", password: "", role: "vendedor" };

export default function Team() {
  const [rows, setRows] = useState([]);
  const [open, setOpen] = useState(false);
  const [pwOpen, setPwOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const [newPassword, setNewPassword] = useState("");

  const load = useCallback(() => api.get("/users").then(r => setRows(r.data)), []);
  useEffect(() => { load(); }, [load]);

  const openNew = () => { setForm(emptyForm); setEditing(null); setOpen(true); };
  const openEdit = (u) => { setForm({ name: u.name, username: u.username, email: u.email || "", password: "", role: u.role }); setEditing(u); setOpen(true); };

  const save = async (e) => {
    e.preventDefault();
    try {
      if (editing) {
        await api.put(`/users/${editing.user_id}`, { name: form.name, role: form.role });
        toast.success("Usuário atualizado");
      } else {
        await api.post("/users", form);
        toast.success("Usuário criado");
      }
      setOpen(false);
      load();
    } catch (err) { toast.error(err.response?.data?.detail || "Erro"); }
  };

  const resetPw = async (e) => {
    e.preventDefault();
    if (newPassword.length < 4) { toast.error("Senha muito curta"); return; }
    try {
      await api.put(`/users/${editing.user_id}`, { password: newPassword });
      toast.success("Senha resetada. Usuário precisará trocar no próximo login.");
      setPwOpen(false);
      setNewPassword("");
    } catch (err) { toast.error(err.response?.data?.detail || "Erro"); }
  };

  const del = async (u) => {
    if (!confirm(`Excluir usuário ${u.name}?`)) return;
    try { await api.delete(`/users/${u.user_id}`); load(); toast.success("Usuário removido"); }
    catch (err) { toast.error(err.response?.data?.detail || "Erro"); }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="font-display text-3xl font-semibold tracking-tight">Equipe</h1>
          <p className="text-sm text-zinc-500 mt-1">{rows.length} usuário(s) na empresa</p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button data-testid="new-user-btn" onClick={openNew} className="h-11 bg-[#F05D23] hover:bg-[#D94E1B]">
              <Plus className="w-4 h-4 mr-1" /> Novo usuário
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-lg">
            <DialogHeader><DialogTitle>{editing ? "Editar usuário" : "Novo usuário"}</DialogTitle></DialogHeader>
            <form onSubmit={save} className="space-y-3">
              <div><Label>Nome completo *</Label><Input data-testid="user-name-input" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
              {!editing && (
                <>
                  <div><Label>Nome de usuário (curto) *</Label><Input data-testid="user-username-input" required value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value.toLowerCase().replace(/[^a-z0-9._-]/g, "") })} placeholder="ex.: joao" /></div>
                  <div><Label>Email (opcional)</Label><Input data-testid="user-email-input" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></div>
                  <div><Label>Senha inicial *</Label><Input data-testid="user-password-input" required minLength={4} type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /><p className="text-xs text-zinc-500 mt-1">O usuário será obrigado a trocar no primeiro acesso.</p></div>
                </>
              )}
              <div>
                <Label>Papel *</Label>
                <Select value={form.role} onValueChange={(v) => setForm({ ...form, role: v })}>
                  <SelectTrigger data-testid="user-role-select"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="vendedor">Vendedor — cria orçamentos/vendas próprios</SelectItem>
                    <SelectItem value="gerente">Gerente — vê tudo, gerencia clientes/produtos</SelectItem>
                    {editing?.role === "owner" && <SelectItem value="owner">Dono</SelectItem>}
                  </SelectContent>
                </Select>
              </div>
              <DialogFooter>
                <Button data-testid="save-user-btn" type="submit" className="bg-[#F05D23] hover:bg-[#D94E1B]">Salvar</Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Reset password dialog */}
      <Dialog open={pwOpen} onOpenChange={setPwOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader><DialogTitle>Resetar senha — {editing?.name}</DialogTitle></DialogHeader>
          <form onSubmit={resetPw} className="space-y-3">
            <div><Label>Nova senha temporária *</Label><Input data-testid="reset-password-input" required minLength={4} type="text" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} /></div>
            <DialogFooter>
              <Button data-testid="reset-password-submit-btn" type="submit" className="bg-[#F05D23] hover:bg-[#D94E1B]">Resetar</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {rows.length === 0 ? (
        <div className="border border-dashed border-zinc-300 rounded-lg p-12 text-center">
          <UsersRound className="w-8 h-8 mx-auto text-zinc-300" />
          <p className="mt-3 text-sm text-zinc-500">Nenhum usuário além do dono.</p>
        </div>
      ) : (
        <div className="border border-zinc-200 rounded-lg overflow-hidden bg-white">
          <table className="w-full text-sm">
            <thead className="bg-zinc-50 text-zinc-600 text-xs uppercase tracking-wider">
              <tr>
                <th className="text-left px-4 py-3">Nome</th>
                <th className="text-left px-4 py-3">Usuário</th>
                <th className="text-left px-4 py-3">Papel</th>
                <th className="text-left px-4 py-3">Email</th>
                <th className="text-right px-4 py-3">Ações</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((u) => {
                const badge = ROLE_BADGE[u.role] || ROLE_BADGE.vendedor;
                return (
                  <tr key={u.user_id} className="border-t border-zinc-100 hover:bg-zinc-50" data-testid={`user-row-${u.username}`}>
                    <td className="px-4 py-3 font-medium text-zinc-900">
                      {u.name}
                      {u.must_change_password && <span className="ml-2 text-[9px] uppercase tracking-widest text-amber-600 font-semibold">Senha temp.</span>}
                    </td>
                    <td className="px-4 py-3 font-mono-num text-zinc-600">@{u.username}</td>
                    <td className="px-4 py-3">
                      <span className={`text-[10px] uppercase tracking-widest font-semibold px-2 py-0.5 rounded ${badge.bg} ${badge.fg}`}>{badge.label}</span>
                    </td>
                    <td className="px-4 py-3 text-zinc-500 text-xs">{u.email || "—"}</td>
                    <td className="px-4 py-3 text-right">
                      <button data-testid={`edit-user-${u.username}`} onClick={() => openEdit(u)} className="w-8 h-8 rounded hover:bg-zinc-100 inline-grid place-items-center text-zinc-500 hover:text-zinc-900" title="Editar"><Pencil className="w-4 h-4" /></button>
                      {u.role !== "owner" && (
                        <>
                          <button data-testid={`reset-user-${u.username}`} onClick={() => { setEditing(u); setPwOpen(true); }} className="ml-1 w-8 h-8 rounded hover:bg-[#FDF0EC] inline-grid place-items-center text-zinc-500 hover:text-[#F05D23]" title="Resetar senha"><KeyRound className="w-4 h-4" /></button>
                          <button data-testid={`delete-user-${u.username}`} onClick={() => del(u)} className="ml-1 w-8 h-8 rounded hover:bg-red-50 inline-grid place-items-center text-zinc-500 hover:text-red-600" title="Excluir"><Trash2 className="w-4 h-4" /></button>
                        </>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
