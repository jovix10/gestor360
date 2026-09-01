import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, fmtMoney, fmtDateTime } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Download, Repeat2, Trash2, Plus, ScrollText, Pencil } from "lucide-react";
import { toast } from "sonner";

export default function Documents() {
  const [rows, setRows] = useState([]);
  const [filter, setFilter] = useState("all");
  const navigate = useNavigate();

  const load = () => api.get("/documents").then(r => setRows(r.data));
  useEffect(() => { load(); }, []);

  const filtered = rows.filter(r => filter === "all" ? true : r.doc_type === filter);

  const isExpired = (r) => {
    if (r.doc_type !== "orcamento" || !r.valid_until) return false;
    return new Date(r.valid_until) < new Date();
  };

  const download = async (id) => {
    try {
      const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || "America/Sao_Paulo";
      const res = await api.get(`/documents/${id}/pdf?tz=${encodeURIComponent(tz)}`, { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.target = "_blank";
      a.rel = "noopener";
      a.download = `documento_${id}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch (err) {
      toast.error("Falha ao gerar PDF");
    }
  };

  const convert = async (id) => {
    if (!confirm("Converter este orçamento em venda?")) return;
    try {
      const { data } = await api.post(`/documents/${id}/convert`);
      toast.success(`Venda Nº ${String(data.number).padStart(6, "0")} criada`);
      load();
    } catch (err) { toast.error(err.response?.data?.detail || "Erro"); }
  };

  const del = async (id) => {
    if (!confirm("Excluir documento?")) return;
    await api.delete(`/documents/${id}`);
    load();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="font-display text-3xl font-semibold tracking-tight">Documentos</h1>
          <p className="text-sm text-zinc-500 mt-1">Orçamentos e vendas emitidos</p>
        </div>
        <Link to="/orcamento" data-testid="new-doc-btn" className="inline-flex items-center gap-2 h-11 px-5 rounded-md bg-[#F05D23] text-white font-semibold hover:bg-[#D94E1B]">
          <Plus className="w-4 h-4" /> Novo
        </Link>
      </div>

      <Tabs value={filter} onValueChange={setFilter}>
        <TabsList>
          <TabsTrigger data-testid="tab-all" value="all">Todos</TabsTrigger>
          <TabsTrigger data-testid="tab-orcamento" value="orcamento">Orçamentos</TabsTrigger>
          <TabsTrigger data-testid="tab-venda" value="venda">Vendas</TabsTrigger>
        </TabsList>
      </Tabs>

      {filtered.length === 0 ? (
        <div className="border border-dashed border-zinc-300 rounded-lg p-12 text-center">
          <ScrollText className="w-8 h-8 mx-auto text-zinc-300" />
          <p className="mt-3 text-sm text-zinc-500">Nenhum documento.</p>
        </div>
      ) : (
        <>
          <div className="hidden md:block border border-zinc-200 rounded-lg overflow-hidden bg-white">
            <table className="w-full text-sm">
              <thead className="bg-zinc-50 text-zinc-600 text-xs uppercase tracking-wider">
                <tr>
                  <th className="text-left px-4 py-3">Tipo</th>
                  <th className="text-left px-4 py-3">Nº</th>
                  <th className="text-left px-4 py-3">Cliente</th>
                  <th className="text-left px-4 py-3">Emissão</th>
                  <th className="text-left px-4 py-3">Validade</th>
                  <th className="text-right px-4 py-3">Total</th>
                  <th className="text-right px-4 py-3">Ações</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((d) => {
                  const expired = isExpired(d);
                  return (
                    <tr key={d.id} className="border-t border-zinc-100 hover:bg-zinc-50" data-testid={`doc-row-${d.id}`}>
                      <td className="px-4 py-3">
                        <span className={`text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded ${d.doc_type === "orcamento" ? "bg-zinc-100 text-zinc-700" : "bg-[#FDF0EC] text-[#F05D23]"}`}>
                          {d.doc_type === "orcamento" ? "Orçamento" : "Venda"}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-mono-num">{String(d.number).padStart(6, "0")}</td>
                      <td className="px-4 py-3 text-zinc-700">{d.client_name}</td>
                      <td className="px-4 py-3 text-zinc-500 text-xs">{fmtDateTime(d.created_at)}</td>
                      <td className="px-4 py-3 text-xs">
                        {d.doc_type === "orcamento"
                          ? (expired ? <span className="text-red-600 font-semibold">Expirado</span> : <span className="text-zinc-500">{fmtDateTime(d.valid_until)}</span>)
                          : <span className="text-zinc-400">—</span>}
                      </td>
                      <td className="px-4 py-3 text-right font-mono-num font-semibold">{fmtMoney(d.total)}</td>
                      <td className="px-4 py-3 text-right">
                        <button data-testid={`edit-${d.id}`} onClick={() => navigate(`/orcamento?id=${d.id}`)} className="w-8 h-8 rounded hover:bg-zinc-100 inline-grid place-items-center text-zinc-500 hover:text-zinc-900" title="Editar"><Pencil className="w-4 h-4" /></button>
                        <button data-testid={`pdf-${d.id}`} onClick={() => download(d.id)} className="ml-1 w-8 h-8 rounded hover:bg-zinc-100 inline-grid place-items-center text-zinc-500 hover:text-zinc-900" title="Baixar PDF"><Download className="w-4 h-4" /></button>
                        {d.doc_type === "orcamento" && (
                          <button data-testid={`convert-${d.id}`} onClick={() => convert(d.id)} className="ml-1 w-8 h-8 rounded hover:bg-[#FDF0EC] inline-grid place-items-center text-zinc-500 hover:text-[#F05D23]" title="Converter em venda"><Repeat2 className="w-4 h-4" /></button>
                        )}
                        <button data-testid={`del-${d.id}`} onClick={() => del(d.id)} className="ml-1 w-8 h-8 rounded hover:bg-red-50 inline-grid place-items-center text-zinc-500 hover:text-red-600" title="Excluir"><Trash2 className="w-4 h-4" /></button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="md:hidden space-y-3">
            {filtered.map((d) => {
              const expired = isExpired(d);
              return (
                <div key={d.id} className="border border-zinc-200 rounded-lg bg-white p-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <span className={`text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded ${d.doc_type === "orcamento" ? "bg-zinc-100 text-zinc-700" : "bg-[#FDF0EC] text-[#F05D23]"}`}>
                        {d.doc_type === "orcamento" ? "Orçamento" : "Venda"}
                      </span>
                      <div className="font-mono-num text-lg mt-1">Nº {String(d.number).padStart(6, "0")}</div>
                      <div className="text-sm text-zinc-700 mt-1">{d.client_name}</div>
                      <div className="text-xs text-zinc-500 mt-1">{fmtDateTime(d.created_at)}</div>
                      {d.doc_type === "orcamento" && (expired ? <div className="text-xs text-red-600 font-semibold mt-1">Expirado</div> : <div className="text-xs text-zinc-500 mt-0.5">Válido até {fmtDateTime(d.valid_until)}</div>)}
                    </div>
                    <div className="font-mono-num font-bold text-lg">{fmtMoney(d.total)}</div>
                  </div>
                  <div className="mt-3 flex gap-2 border-t border-zinc-100 pt-3 flex-wrap">
                    <Button size="sm" variant="outline" onClick={() => navigate(`/orcamento?id=${d.id}`)}><Pencil className="w-3.5 h-3.5 mr-1" />Editar</Button>
                    <Button size="sm" variant="outline" onClick={() => download(d.id)}><Download className="w-3.5 h-3.5 mr-1" />PDF</Button>
                    {d.doc_type === "orcamento" && <Button size="sm" variant="outline" onClick={() => convert(d.id)}><Repeat2 className="w-3.5 h-3.5 mr-1" />Converter</Button>}
                    <Button size="sm" variant="ghost" className="text-red-600 ml-auto" onClick={() => del(d.id)}><Trash2 className="w-3.5 h-3.5" /></Button>
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
