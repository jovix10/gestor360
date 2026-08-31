import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, fmtMoney, computeTotals, API } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Trash2, Plus, FileText, ShoppingCart, Save } from "lucide-react";
import { toast } from "sonner";

const emptyLine = () => ({ product_id: null, code: "", description: "", quantity: 1, unit_price: 0, discount_pct: 0 });

export default function QuoteBuilder() {
  const navigate = useNavigate();
  const [docType, setDocType] = useState("orcamento");
  const [clients, setClients] = useState([]);
  const [products, setProducts] = useState([]);
  const [clientId, setClientId] = useState("");
  const [notes, setNotes] = useState("");
  const [lines, setLines] = useState([emptyLine()]);
  const [saving, setSaving] = useState(false);
  const rowsRef = useRef({});

  useEffect(() => {
    api.get("/clients").then(r => setClients(r.data));
    api.get("/products").then(r => setProducts(r.data));
  }, []);

  const productMap = useMemo(() => {
    const m = {};
    products.forEach(p => { m[p.code.toLowerCase()] = p; m[p.id] = p; });
    return m;
  }, [products]);

  const findProduct = (val) => {
    if (!val) return null;
    const key = String(val).toLowerCase().trim();
    if (!key) return null;
    if (productMap[key]) return productMap[key];
    // fallback: match by description contains (case-insensitive)
    return products.find(p => p.description.toLowerCase().includes(key)) || null;
  };

  const updateLine = (idx, patch) => {
    setLines((cur) => cur.map((l, i) => (i === idx ? { ...l, ...patch } : l)));
  };

  const applyProduct = (idx, product) => {
    updateLine(idx, {
      product_id: product.id,
      code: product.code,
      description: product.description,
      unit_price: product.price,
    });
  };

  const onCodeBlur = (idx, val) => {
    const p = findProduct(val);
    if (p) applyProduct(idx, p);
  };

  const addLine = (focusIdx) => {
    setLines((cur) => {
      const next = [...cur, emptyLine()];
      setTimeout(() => {
        const el = rowsRef.current[`${next.length - 1}-code`];
        if (el) el.focus();
      }, 30);
      return next;
    });
  };

  const removeLine = (idx) => {
    setLines((cur) => (cur.length === 1 ? [emptyLine()] : cur.filter((_, i) => i !== idx)));
  };

  const onKeyDown = (idx, field, e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      // Move through the columns; last col -> new row
      const order = ["code", "description", "quantity", "unit_price", "discount_pct"];
      const pos = order.indexOf(field);
      if (pos < order.length - 1) {
        const next = rowsRef.current[`${idx}-${order[pos + 1]}`];
        if (next) next.focus();
      } else {
        if (idx === lines.length - 1) addLine(idx);
        else {
          const next = rowsRef.current[`${idx + 1}-code`];
          if (next) next.focus();
        }
      }
    }
  };

  const totals = computeTotals(lines);

  const save = async () => {
    if (!clientId) { toast.error("Selecione um cliente"); return; }
    const valid = lines.filter(l => (l.description || l.code) && Number(l.quantity) > 0);
    if (!valid.length) { toast.error("Adicione ao menos um item"); return; }
    setSaving(true);
    try {
      const { data } = await api.post("/documents", {
        doc_type: docType,
        client_id: clientId,
        lines: valid.map(l => ({
          product_id: l.product_id,
          code: l.code || "",
          description: l.description || "",
          quantity: Number(l.quantity) || 0,
          unit_price: Number(l.unit_price) || 0,
          discount_pct: Number(l.discount_pct) || 0,
        })),
        notes,
      });
      toast.success(`${docType === "orcamento" ? "Orçamento" : "Venda"} Nº ${String(data.number).padStart(6, "0")} criado`);
      // open pdf via anchor click (survives popup blockers, preserves auth)
      try {
        const res = await api.get(`/documents/${data.id}/pdf`, { responseType: "blob" });
        const url = URL.createObjectURL(res.data);
        const a = document.createElement("a");
        a.href = url;
        a.target = "_blank";
        a.rel = "noopener";
        a.download = `${docType}_${String(data.number).padStart(6, "0")}.pdf`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        setTimeout(() => URL.revokeObjectURL(url), 60_000);
      } catch (e) {
        toast.error("Documento salvo, mas falhou ao abrir PDF");
      }
      navigate("/documentos");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Erro ao salvar");
    } finally { setSaving(false); }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="font-display text-3xl font-semibold tracking-tight">Novo Documento</h1>
          <p className="text-sm text-zinc-500 mt-1">Monte um orçamento ou uma venda. Pressione <kbd className="px-1.5 py-0.5 rounded bg-zinc-100 text-xs font-mono">Enter</kbd> para pular colunas.</p>
        </div>
        <div className="flex gap-2">
          <button
            data-testid="doc-type-orcamento"
            onClick={() => setDocType("orcamento")}
            className={`h-11 px-4 rounded-md border font-semibold text-sm inline-flex items-center gap-2 transition-colors ${docType === "orcamento" ? "bg-zinc-900 text-white border-zinc-900" : "bg-white text-zinc-700 border-zinc-200 hover:border-zinc-900"}`}
          >
            <FileText className="w-4 h-4" /> Orçamento
          </button>
          <button
            data-testid="doc-type-venda"
            onClick={() => setDocType("venda")}
            className={`h-11 px-4 rounded-md border font-semibold text-sm inline-flex items-center gap-2 transition-colors ${docType === "venda" ? "bg-[#F05D23] text-white border-[#F05D23]" : "bg-white text-zinc-700 border-zinc-200 hover:border-[#F05D23]"}`}
          >
            <ShoppingCart className="w-4 h-4" /> Venda direta
          </button>
        </div>
      </div>

      {/* client + notes */}
      <div className="grid md:grid-cols-3 gap-4">
        <div className="md:col-span-2 border border-zinc-200 rounded-lg bg-white p-4">
          <Label>Cliente *</Label>
          <Select value={clientId} onValueChange={setClientId}>
            <SelectTrigger data-testid="client-select" className="mt-1 h-11">
              <SelectValue placeholder="Selecione o cliente" />
            </SelectTrigger>
            <SelectContent>
              {clients.map(c => (
                <SelectItem key={c.id} value={c.id} data-testid={`client-option-${c.id}`}>
                  {c.name} {c.document && `· ${c.document}`}
                </SelectItem>
              ))}
              {clients.length === 0 && <div className="px-3 py-6 text-sm text-zinc-500 text-center">Nenhum cliente. Cadastre em Clientes.</div>}
            </SelectContent>
          </Select>
          {docType === "orcamento" && (
            <p className="text-xs text-zinc-500 mt-2">Orçamento válido por 72 horas a partir da emissão.</p>
          )}
        </div>
        <div className="border border-zinc-200 rounded-lg bg-white p-4">
          <Label>Observações</Label>
          <Textarea data-testid="notes-input" value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} placeholder="Condições, prazo, etc." className="mt-1" />
        </div>
      </div>

      {/* line editor */}
      <div className="border border-zinc-200 rounded-lg bg-white overflow-hidden">
        {/* Desktop */}
        <div className="hidden md:block overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-zinc-900 text-white">
              <tr className="text-xs uppercase tracking-wider">
                <th className="text-left px-3 py-3 w-24">Código</th>
                <th className="text-left px-3 py-3">Descrição</th>
                <th className="text-right px-3 py-3 w-24">Qtd.</th>
                <th className="text-right px-3 py-3 w-32">Valor</th>
                <th className="text-right px-3 py-3 w-24">Desc. %</th>
                <th className="text-right px-3 py-3 w-32">Líquido</th>
                <th className="w-12"></th>
              </tr>
            </thead>
            <tbody>
              {lines.map((l, idx) => {
                const net = Number(l.quantity || 0) * Number(l.unit_price || 0) * (1 - Number(l.discount_pct || 0) / 100);
                return (
                  <tr key={idx} className="border-t border-zinc-100">
                    <td className="px-3 py-1.5">
                      <input
                        ref={(el) => (rowsRef.current[`${idx}-code`] = el)}
                        data-testid={`line-code-${idx}`}
                        className="qb-input"
                        value={l.code}
                        onChange={(e) => updateLine(idx, { code: e.target.value })}
                        onBlur={(e) => onCodeBlur(idx, e.target.value)}
                        onKeyDown={(e) => onKeyDown(idx, "code", e)}
                        placeholder="—"
                        list={`prod-list-${idx}`}
                      />
                      <datalist id={`prod-list-${idx}`}>
                        {products.map(p => <option key={p.id} value={p.code}>{p.code} — {p.description}</option>)}
                      </datalist>
                    </td>
                    <td className="px-3 py-1.5">
                      <input
                        ref={(el) => (rowsRef.current[`${idx}-description`] = el)}
                        data-testid={`line-description-${idx}`}
                        className="qb-input qb-text"
                        value={l.description}
                        onChange={(e) => updateLine(idx, { description: e.target.value })}
                        onKeyDown={(e) => onKeyDown(idx, "description", e)}
                        placeholder="Descrição do item"
                      />
                    </td>
                    <td className="px-3 py-1.5">
                      <input
                        ref={(el) => (rowsRef.current[`${idx}-quantity`] = el)}
                        data-testid={`line-quantity-${idx}`}
                        className="qb-input text-right"
                        type="number" step="0.01" min="0"
                        value={l.quantity}
                        onChange={(e) => updateLine(idx, { quantity: e.target.value })}
                        onKeyDown={(e) => onKeyDown(idx, "quantity", e)}
                      />
                    </td>
                    <td className="px-3 py-1.5">
                      <input
                        ref={(el) => (rowsRef.current[`${idx}-unit_price`] = el)}
                        data-testid={`line-price-${idx}`}
                        className="qb-input text-right"
                        type="number" step="0.01" min="0"
                        value={l.unit_price}
                        onChange={(e) => updateLine(idx, { unit_price: e.target.value })}
                        onKeyDown={(e) => onKeyDown(idx, "unit_price", e)}
                      />
                    </td>
                    <td className="px-3 py-1.5">
                      <input
                        ref={(el) => (rowsRef.current[`${idx}-discount_pct`] = el)}
                        data-testid={`line-discount-${idx}`}
                        className="qb-input text-right"
                        type="number" step="0.01" min="0" max="100"
                        value={l.discount_pct}
                        onChange={(e) => updateLine(idx, { discount_pct: e.target.value })}
                        onKeyDown={(e) => onKeyDown(idx, "discount_pct", e)}
                      />
                    </td>
                    <td className="px-3 py-1.5 text-right font-mono-num font-semibold">{fmtMoney(net)}</td>
                    <td className="px-2 py-1.5 text-right">
                      <button data-testid={`remove-line-${idx}`} onClick={() => removeLine(idx)} className="w-8 h-8 rounded hover:bg-red-50 inline-grid place-items-center text-zinc-400 hover:text-red-600">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {/* Mobile */}
        <div className="md:hidden divide-y divide-zinc-100">
          {lines.map((l, idx) => {
            const net = Number(l.quantity || 0) * Number(l.unit_price || 0) * (1 - Number(l.discount_pct || 0) / 100);
            return (
              <div key={idx} className="p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-zinc-500">Item #{idx + 1}</span>
                  <button onClick={() => removeLine(idx)} className="text-red-500"><Trash2 className="w-4 h-4" /></button>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div><Label className="text-xs">Código</Label><Input value={l.code} onBlur={(e) => onCodeBlur(idx, e.target.value)} onChange={(e) => updateLine(idx, { code: e.target.value })} /></div>
                  <div><Label className="text-xs">Qtd.</Label><Input type="number" value={l.quantity} onChange={(e) => updateLine(idx, { quantity: e.target.value })} /></div>
                </div>
                <div><Label className="text-xs">Descrição</Label><Input value={l.description} onChange={(e) => updateLine(idx, { description: e.target.value })} /></div>
                <div className="grid grid-cols-2 gap-2">
                  <div><Label className="text-xs">Valor</Label><Input type="number" step="0.01" value={l.unit_price} onChange={(e) => updateLine(idx, { unit_price: e.target.value })} /></div>
                  <div><Label className="text-xs">Desc. %</Label><Input type="number" step="0.01" value={l.discount_pct} onChange={(e) => updateLine(idx, { discount_pct: e.target.value })} /></div>
                </div>
                <div className="text-right font-mono-num font-semibold">{fmtMoney(net)}</div>
              </div>
            );
          })}
        </div>

        <div className="p-3 border-t border-zinc-100 bg-zinc-50 flex justify-between items-center">
          <button data-testid="add-line-btn" onClick={() => addLine()} className="inline-flex items-center gap-2 text-sm text-[#F05D23] font-semibold hover:underline">
            <Plus className="w-4 h-4" /> Adicionar item
          </button>
          <div className="text-xs text-zinc-500">
            {lines.length} linha(s)
          </div>
        </div>
      </div>

      {/* totals */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-4">
        <div className="flex-1" />
        <div className="w-full sm:w-80 border border-zinc-200 rounded-lg bg-white p-5 space-y-2">
          <div className="flex justify-between text-sm"><span className="text-zinc-500">Subtotal bruto</span><span className="font-mono-num">{fmtMoney(totals.gross)}</span></div>
          <div className="flex justify-between text-sm"><span className="text-zinc-500">Descontos</span><span className="font-mono-num text-red-600">- {fmtMoney(totals.disc)}</span></div>
          <div className="border-t border-zinc-200 pt-2 flex justify-between items-center">
            <span className="text-xs uppercase tracking-wider text-zinc-500">Total líquido</span>
            <span className="font-mono-num font-bold text-2xl text-zinc-900">{fmtMoney(totals.net)}</span>
          </div>
        </div>
      </div>

      <div className="flex justify-end gap-2">
        <Button
          data-testid="save-doc-btn"
          onClick={save} disabled={saving}
          className="h-11 px-6 bg-[#F05D23] hover:bg-[#D94E1B] text-white font-semibold"
        >
          <Save className="w-4 h-4 mr-2" />
          {saving ? "Salvando…" : `Salvar e gerar PDF`}
        </Button>
      </div>
    </div>
  );
}
