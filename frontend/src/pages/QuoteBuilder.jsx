import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api, fmtMoney, computeTotals } from "@/lib/api";
import { buildDocumentPdf } from "@/lib/pdf";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Trash2, Plus, FileText, ShoppingCart, Save, Search, X } from "lucide-react";
import { toast } from "sonner";

const emptyLine = () => ({ id: crypto.randomUUID(), product_id: null, code: "", description: "", quantity: 1, unit_price: 0, discount_pct: 0 });

const METHOD_LABELS = {
  pix: "PIX",
  dinheiro: "Dinheiro",
  credito: "Cartão de Crédito",
  debito: "Cartão de Débito",
  boleto: "Boleto",
  transferencia: "Transferência",
};

// -------- Product search cell (inline autocomplete) --------
function ProductSearchCell({ line, idx, products, inputRef, onChange, onPick, onKeyDown, onPriceBlur }) {
  const [open, setOpen] = useState(false);
  const [hover, setHover] = useState(0);
  const q = String(line.code || "").trim().toLowerCase();
  const matches = useMemo(() => {
    if (!q) return [];
    return products
      .filter(p => p.code.toLowerCase().startsWith(q) || p.description.toLowerCase().startsWith(q))
      .slice(0, 8);
  }, [q, products]);

  useEffect(() => { setHover(0); }, [q]);

  const handleKey = (e) => {
    if (open && matches.length > 0) {
      if (e.key === "ArrowDown") { e.preventDefault(); setHover(h => Math.min(h + 1, matches.length - 1)); return; }
      if (e.key === "ArrowUp") { e.preventDefault(); setHover(h => Math.max(h - 1, 0)); return; }
      if (e.key === "Enter") {
        e.preventDefault();
        onPick(matches[hover]);
        setOpen(false);
        return;
      }
      if (e.key === "Escape") { setOpen(false); return; }
    }
    onKeyDown(e);
  };

  return (
    <div className="relative">
      <input
        ref={inputRef}
        data-testid={`line-code-${idx}`}
        className="qb-input"
        value={line.code}
        onChange={(e) => { onChange(e.target.value); setOpen(true); }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        onKeyDown={handleKey}
        placeholder="—"
      />
      {open && matches.length > 0 && (
        <div className="absolute left-0 top-full mt-1 w-[420px] max-w-[85vw] z-40 bg-white border border-zinc-200 rounded-lg shadow-xl overflow-hidden" data-testid={`product-suggest-${idx}`}>
          {matches.map((p, i) => (
            <button
              key={p.id}
              type="button"
              data-testid={`product-option-${idx}-${p.code}`}
              onMouseEnter={() => setHover(i)}
              onMouseDown={(e) => { e.preventDefault(); onPick(p); setOpen(false); }}
              className={`w-full text-left px-3 py-2 flex items-center gap-3 border-b last:border-b-0 border-zinc-50 ${i === hover ? "bg-[#FDF0EC]" : "bg-white"}`}
            >
              <span className="font-mono-num text-xs bg-zinc-900 text-white px-1.5 py-0.5 rounded shrink-0">{p.code}</span>
              <span className="text-sm truncate flex-1">{p.description}</span>
              <span className="font-mono-num text-xs text-zinc-500 shrink-0">{fmtMoney(p.price)}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// -------- Client search combobox --------
function ClientSearchInput({ clients, value, onChange }) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const selected = clients.find(c => c.id === value);
  useEffect(() => { if (selected) setQ(selected.name); }, [selected]);
  const term = q.toLowerCase().trim();
  const matches = !term ? clients.slice(0, 10) : clients.filter(c =>
    (c.name || "").toLowerCase().includes(term) ||
    (c.document || "").toLowerCase().includes(term) ||
    (c.city || "").toLowerCase().includes(term)
  ).slice(0, 10);

  return (
    <div className="relative">
      <div className="relative">
        <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400" />
        <Input
          data-testid="client-search-combobox"
          className="pl-9 h-11 pr-9"
          value={q}
          onChange={(e) => { setQ(e.target.value); setOpen(true); if (!e.target.value) onChange(""); }}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
          placeholder="Buscar cliente por nome, documento…"
        />
        {value && (
          <button type="button" onClick={() => { onChange(""); setQ(""); }} className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-zinc-400 hover:text-red-600" data-testid="clear-client-btn">
            <X className="w-4 h-4" />
          </button>
        )}
      </div>
      {open && (
        <div className="absolute z-40 mt-1 w-full bg-white border border-zinc-200 rounded-md shadow-xl max-h-72 overflow-auto">
          {matches.length === 0 ? (
            <div className="px-3 py-4 text-sm text-zinc-500 text-center">Nenhum cliente</div>
          ) : matches.map(c => (
            <button
              key={c.id}
              type="button"
              data-testid={`client-option-${c.id}`}
              onMouseDown={(e) => { e.preventDefault(); onChange(c.id); setQ(c.name); setOpen(false); }}
              className="w-full text-left px-3 py-2 hover:bg-[#FDF0EC] flex items-center gap-3"
            >
              <div className="min-w-0 flex-1">
                <div className="font-medium text-sm truncate">{c.name}</div>
                <div className="text-xs text-zinc-500 truncate">{c.document || c.email || c.phone || "—"}</div>
              </div>
              {c.city && <div className="text-xs text-zinc-400 shrink-0">{c.city}/{c.state}</div>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// -------- Main page --------
export default function QuoteBuilder() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const editId = params.get("id");
  const [docType, setDocType] = useState("orcamento");
  const [clients, setClients] = useState([]);
  const [products, setProducts] = useState([]);
  const [clientId, setClientId] = useState("");
  const [notes, setNotes] = useState("");
  const [lines, setLines] = useState([emptyLine()]);
  const [payments, setPayments] = useState([]);
  const [globalDiscountPct, setGlobalDiscountPct] = useState(0);
  const [globalDiscountAmount, setGlobalDiscountAmount] = useState(0);
  const [saving, setSaving] = useState(false);
  const [tab, setTab] = useState("itens");
  const [loadedDoc, setLoadedDoc] = useState(null);
  const rowsRef = useRef({});

  useEffect(() => {
    api.get("/clients").then(r => setClients(r.data));
    api.get("/products").then(r => setProducts(r.data));
  }, []);

  useEffect(() => {
    if (!editId) return;
    api.get(`/documents/${editId}`).then(r => {
      const d = r.data;
      setLoadedDoc(d);
      setDocType(d.doc_type);
      setClientId(d.client_id);
      setNotes(d.notes || "");
      setLines(d.lines && d.lines.length ? d.lines.map(l => ({ ...l, id: l.id || crypto.randomUUID() })) : [emptyLine()]);
      setPayments((d.payments || []).map(p => ({ ...p, id: p.id || crypto.randomUUID() })));
      setGlobalDiscountPct(Number(d.global_discount_pct || 0));
      setGlobalDiscountAmount(Number(d.global_discount_amount || 0));
    }).catch(() => toast.error("Documento não encontrado"));
  }, [editId]);

  const productMap = useMemo(() => {
    const m = {};
    products.forEach(p => { m[p.code.toLowerCase()] = p; m[p.id] = p; });
    return m;
  }, [products]);

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
    setTimeout(() => rowsRef.current[`${idx}-quantity`]?.focus(), 30);
  };

  const onPriceBlur = (idx, val) => {
    const line = lines[idx];
    if (!line?.product_id) return;
    const p = productMap[line.product_id];
    if (!p) return;
    const typed = Number(val);
    const list = Number(p.price);
    if (!typed || !list || typed >= list) return;
    const pct = Math.round((1 - typed / list) * 10000) / 100;
    updateLine(idx, { unit_price: list, discount_pct: pct });
  };

  const addLine = () => {
    setLines((cur) => {
      const next = [...cur, emptyLine()];
      setTimeout(() => rowsRef.current[`${next.length - 1}-code`]?.focus(), 30);
      return next;
    });
  };

  const removeLine = (idx) => {
    setLines((cur) => (cur.length === 1 ? [emptyLine()] : cur.filter((_, i) => i !== idx)));
  };

  const onKeyDown = (idx, field, e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      const order = ["code", "description", "quantity", "unit_price", "discount_pct"];
      const pos = order.indexOf(field);
      if (pos < order.length - 1) {
        rowsRef.current[`${idx}-${order[pos + 1]}`]?.focus();
      } else {
        if (idx === lines.length - 1) addLine();
        else rowsRef.current[`${idx + 1}-code`]?.focus();
      }
    }
  };

  const totals = computeTotals(lines, { global_discount_pct: globalDiscountPct, global_discount_amount: globalDiscountAmount });
  const totalPaid = payments.reduce((s, p) => s + Number(p.amount || 0), 0);
  const remaining = Math.round((totals.net - totalPaid) * 100) / 100;

  const remainingClass = () => {
    if (Math.abs(remaining) < 0.01) return "text-[#F05D23]";
    if (remaining > 0) return "text-zinc-900";
    return "text-red-600";
  };

  const saveButtonLabel = () => {
    if (saving) return "Salvando…";
    if (editId) return "Atualizar e gerar PDF";
    return "Salvar e gerar PDF";
  };

  const applyRoundDown = (step) => {
    const target = Math.floor(totals.lineNet / step) * step;
    const diff = Math.max(totals.lineNet - target, 0);
    setGlobalDiscountPct(0);
    setGlobalDiscountAmount(Number(diff.toFixed(2)));
  };

  const addPayment = (method = "pix") => {
    const suggestedAmount = Math.max(0, Math.round(remaining * 100) / 100);
    setPayments(cur => [...cur, { id: crypto.randomUUID(), method, amount: suggestedAmount, installments: 1, boleto_days: [] }]);
  };

  const parseBoletoDays = (raw) => {
    return String(raw || "")
      .split(/[,;\s]+/)
      .map(x => parseInt(x, 10))
      .filter(n => Number.isFinite(n) && n > 0);
  };

  const updatePayment = (idx, patch) => {
    setPayments(cur => cur.map((p, i) => (i === idx ? { ...p, ...patch } : p)));
  };

  const removePayment = (idx) => setPayments(cur => cur.filter((_, i) => i !== idx));

  const save = async () => {
    if (!clientId) { toast.error("Selecione um cliente"); setTab("itens"); return; }
    const valid = lines.filter(l => (l.description || l.code) && Number(l.quantity) > 0);
    if (!valid.length) { toast.error("Adicione ao menos um item"); setTab("itens"); return; }
    setSaving(true);
    const body = {
      doc_type: docType,
      client_id: clientId,
      lines: valid.map(l => ({
        product_id: l.product_id || null,
        code: l.code || "",
        description: l.description || "",
        quantity: Number(l.quantity) || 0,
        unit_price: Number(l.unit_price) || 0,
        discount_pct: Number(l.discount_pct) || 0,
      })),
      payments: payments.map(p => ({
        method: p.method,
        amount: Number(p.amount) || 0,
        installments: Math.max(1, parseInt(p.installments) || 1),
        boleto_days: Array.isArray(p.boleto_days) ? p.boleto_days.map(d => parseInt(d) || 0).filter(d => d > 0) : [],
      })),
      global_discount_pct: Number(globalDiscountPct) || 0,
      global_discount_amount: Number(globalDiscountAmount) || 0,
      notes,
    };
    try {
      let data;
      if (editId) {
        ({ data } = await api.put(`/documents/${editId}`, body));
        toast.success(`Documento Nº ${String(data.number).padStart(6, "0")} atualizado`);
      } else {
        ({ data } = await api.post("/documents", body));
        toast.success(`${docType === "orcamento" ? "Orçamento" : "Venda"} Nº ${String(data.number).padStart(6, "0")} criado`);
      }
      try {
        const [companyRes, clientsRes] = await Promise.all([
          api.get("/company"),
          api.get("/clients"),
        ]);
        const client = clientsRes.data.find((c) => c.id === data.client_id) || {};
        await buildDocumentPdf(data, companyRes.data, client);
      } catch { toast.error("Documento salvo, mas falhou ao abrir PDF"); }
      navigate("/documentos");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Erro ao salvar");
    } finally { setSaving(false); }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="font-display text-3xl font-semibold tracking-tight">
            {editId ? "Editar Documento" : "Novo Documento"}
            {loadedDoc && <span className="ml-3 font-mono-num text-lg text-zinc-400">Nº {String(loadedDoc.number).padStart(6, "0")}</span>}
          </h1>
          <p className="text-sm text-zinc-500 mt-1">
            {editId ? "Atualize itens e condições de pagamento." : (<>Monte um orçamento ou uma venda. Pressione <kbd className="px-1.5 py-0.5 rounded bg-zinc-100 text-xs font-mono">Enter</kbd> para pular colunas.</>)}
          </p>
        </div>
        {!editId && (
          <div className="flex gap-2">
            <button
              data-testid="doc-type-orcamento"
              onClick={() => setDocType("orcamento")}
              className={`h-11 px-4 rounded-md border font-semibold text-sm inline-flex items-center gap-2 transition-colors ${docType === "orcamento" ? "bg-zinc-900 text-white border-zinc-900" : "bg-white text-zinc-700 border-zinc-200 hover:border-zinc-900"}`}
            ><FileText className="w-4 h-4" /> Orçamento</button>
            <button
              data-testid="doc-type-venda"
              onClick={() => setDocType("venda")}
              className={`h-11 px-4 rounded-md border font-semibold text-sm inline-flex items-center gap-2 transition-colors ${docType === "venda" ? "bg-[#F05D23] text-white border-[#F05D23]" : "bg-white text-zinc-700 border-zinc-200 hover:border-[#F05D23]"}`}
            ><ShoppingCart className="w-4 h-4" /> Venda direta</button>
          </div>
        )}
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger data-testid="tab-itens" value="itens">1. Itens</TabsTrigger>
          <TabsTrigger data-testid="tab-pagamento" value="pagamento">2. Pagamento</TabsTrigger>
        </TabsList>

        <TabsContent value="itens" className="space-y-5 mt-6">
          {/* client + notes */}
          <div className="grid md:grid-cols-3 gap-4">
            <div className="md:col-span-2 border border-zinc-200 rounded-lg bg-white p-4">
              <Label>Cliente *</Label>
              <div className="mt-1">
                <ClientSearchInput clients={clients} value={clientId} onChange={setClientId} />
              </div>
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
          <div className="border border-zinc-200 rounded-lg bg-white overflow-visible">
            <div className="hidden md:block overflow-x-visible">
              <table className="w-full text-sm">
                <thead className="bg-zinc-900 text-white">
                  <tr className="text-xs uppercase tracking-wider">
                    <th className="text-left px-3 py-3 w-40">Código / Buscar</th>
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
                      <tr key={l.id} className="border-t border-zinc-100">
                        <td className="px-3 py-1.5 align-top">
                          <ProductSearchCell
                            idx={idx}
                            line={l}
                            products={products}
                            inputRef={(el) => (rowsRef.current[`${idx}-code`] = el)}
                            onChange={(v) => updateLine(idx, { code: v, product_id: null })}
                            onPick={(p) => applyProduct(idx, p)}
                            onKeyDown={(e) => onKeyDown(idx, "code", e)}
                          />
                        </td>
                        <td className="px-3 py-1.5 align-top">
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
                        <td className="px-3 py-1.5 align-top">
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
                        <td className="px-3 py-1.5 align-top">
                          <input
                            ref={(el) => (rowsRef.current[`${idx}-unit_price`] = el)}
                            data-testid={`line-price-${idx}`}
                            className="qb-input text-right"
                            type="number" step="0.01" min="0"
                            value={l.unit_price}
                            onChange={(e) => updateLine(idx, { unit_price: e.target.value })}
                            onBlur={(e) => onPriceBlur(idx, e.target.value)}
                            onKeyDown={(e) => onKeyDown(idx, "unit_price", e)}
                          />
                        </td>
                        <td className="px-3 py-1.5 align-top">
                          <input
                            ref={(el) => (rowsRef.current[`${idx}-discount_pct`] = el)}
                            data-testid={`line-discount-${idx}`}
                            className="qb-input text-right"
                            type="number" step="0.01" min="0" max="100"
                            value={l.discount_pct}
                            onChange={(e) => updateLine(idx, { discount_pct: e.target.value })}
                            onKeyDown={(e) => onKeyDown(idx, "discount_pct", e)}
                          />
                          {Number(l.discount_pct) > 0 && Number(l.unit_price) > 0 && (
                            <div className="text-[10px] text-emerald-600 font-mono-num text-right mt-1" data-testid={`line-net-unit-${idx}`}>
                              {fmtMoney(Number(l.unit_price) * (1 - Number(l.discount_pct) / 100))}/un
                            </div>
                          )}
                        </td>
                        <td className="px-3 py-1.5 text-right font-mono-num font-semibold align-top">{fmtMoney(net)}</td>
                        <td className="px-2 py-1.5 text-right align-top">
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

            {/* Mobile line editor */}
            <div className="md:hidden divide-y divide-zinc-100">
              {lines.map((l, idx) => {
                const net = Number(l.quantity || 0) * Number(l.unit_price || 0) * (1 - Number(l.discount_pct || 0) / 100);
                return (
                  <div key={l.id} className="p-4 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-zinc-500">Item #{idx + 1}</span>
                      <button onClick={() => removeLine(idx)} className="text-red-500"><Trash2 className="w-4 h-4" /></button>
                    </div>
                    <div>
                      <Label className="text-xs">Buscar / Código</Label>
                      <ProductSearchCell
                        idx={idx}
                        line={l}
                        products={products}
                        inputRef={() => {}}
                        onChange={(v) => updateLine(idx, { code: v, product_id: null })}
                        onPick={(p) => applyProduct(idx, p)}
                        onKeyDown={() => {}}
                      />
                    </div>
                    <div><Label className="text-xs">Descrição</Label><Input value={l.description} onChange={(e) => updateLine(idx, { description: e.target.value })} /></div>
                    <div className="grid grid-cols-3 gap-2">
                      <div><Label className="text-xs">Qtd.</Label><Input type="number" value={l.quantity} onChange={(e) => updateLine(idx, { quantity: e.target.value })} /></div>
                      <div><Label className="text-xs">Valor</Label><Input type="number" step="0.01" value={l.unit_price} onBlur={(e) => onPriceBlur(idx, e.target.value)} onChange={(e) => updateLine(idx, { unit_price: e.target.value })} /></div>
                      <div><Label className="text-xs">Desc. %</Label>
                        <Input type="number" step="0.01" value={l.discount_pct} onChange={(e) => updateLine(idx, { discount_pct: e.target.value })} />
                        {Number(l.discount_pct) > 0 && Number(l.unit_price) > 0 && (
                          <div className="text-[10px] text-emerald-600 font-mono-num mt-1">
                            {fmtMoney(Number(l.unit_price) * (1 - Number(l.discount_pct) / 100))}/un
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="text-right font-mono-num font-semibold">{fmtMoney(net)}</div>
                  </div>
                );
              })}
            </div>

            <div className="p-3 border-t border-zinc-100 bg-zinc-50 flex justify-between items-center">
              <button data-testid="add-line-btn" onClick={addLine} className="inline-flex items-center gap-2 text-sm text-[#F05D23] font-semibold hover:underline">
                <Plus className="w-4 h-4" /> Adicionar item
              </button>
              <div className="text-xs text-zinc-500">{lines.length} linha(s)</div>
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

          <div className="flex justify-end">
            <Button
              data-testid="next-to-payment-btn"
              onClick={() => setTab("pagamento")}
              className="h-11 px-6 bg-zinc-900 hover:bg-zinc-800 text-white font-semibold"
            >
              Ir para pagamento →
            </Button>
          </div>
        </TabsContent>

        <TabsContent value="pagamento" className="space-y-5 mt-6">
          {/* Global discount / rounding */}
          <div className="border border-zinc-200 rounded-lg bg-white p-5 space-y-4">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div>
                <h2 className="font-display text-lg font-semibold">Desconto no total</h2>
                <p className="text-sm text-zinc-500">Aplique um percentual ou tire um valor fixo em cima do total (para arredondar, por exemplo).</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <button type="button" data-testid="quick-pct-5" onClick={() => { setGlobalDiscountAmount(0); setGlobalDiscountPct(5); }} className="h-9 px-3 rounded-md border border-zinc-200 text-xs font-semibold hover:border-[#F05D23] hover:text-[#F05D23]">-5%</button>
                <button type="button" data-testid="quick-pct-10" onClick={() => { setGlobalDiscountAmount(0); setGlobalDiscountPct(10); }} className="h-9 px-3 rounded-md border border-zinc-200 text-xs font-semibold hover:border-[#F05D23] hover:text-[#F05D23]">-10%</button>
                <button type="button" data-testid="quick-round-10" onClick={() => applyRoundDown(10)} className="h-9 px-3 rounded-md border border-zinc-200 text-xs font-semibold hover:border-[#F05D23] hover:text-[#F05D23]">Arred. R$10</button>
                <button type="button" data-testid="quick-round-100" onClick={() => applyRoundDown(100)} className="h-9 px-3 rounded-md border border-zinc-200 text-xs font-semibold hover:border-[#F05D23] hover:text-[#F05D23]">Arred. R$100</button>
                <button type="button" data-testid="clear-global-discount" onClick={() => { setGlobalDiscountPct(0); setGlobalDiscountAmount(0); }} className="h-9 px-3 rounded-md border border-zinc-200 text-xs font-semibold text-zinc-500 hover:text-red-600">Limpar</button>
              </div>
            </div>
            <div className="grid sm:grid-cols-2 gap-3">
              <div>
                <Label className="text-xs">Percentual sobre o total (%)</Label>
                <Input data-testid="global-discount-pct" type="number" step="0.01" min="0" max="100" value={globalDiscountPct} onChange={(e) => setGlobalDiscountPct(parseFloat(e.target.value) || 0)} />
              </div>
              <div>
                <Label className="text-xs">Valor fixo em R$</Label>
                <Input data-testid="global-discount-amount" type="number" step="0.01" min="0" value={globalDiscountAmount} onChange={(e) => setGlobalDiscountAmount(parseFloat(e.target.value) || 0)} />
              </div>
            </div>
            {(totals.globalDisc > 0) && (
              <div className="text-sm text-zinc-600 flex justify-between border-t border-zinc-100 pt-3">
                <span>Total antes: <span className="font-mono-num line-through">{fmtMoney(totals.lineNet)}</span></span>
                <span>Você tira <span className="font-mono-num text-red-600">- {fmtMoney(totals.globalDisc)}</span> → <span className="font-mono-num font-bold text-[#F05D23]">{fmtMoney(totals.net)}</span></span>
              </div>
            )}
          </div>

          <div className="border border-zinc-200 rounded-lg bg-white p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="font-display text-lg font-semibold">Condições de pagamento</h2>
                <p className="text-sm text-zinc-500">Divida em quantas formas quiser. Ex.: parte no PIX, parte no cartão.</p>
              </div>
              <div className="flex flex-wrap gap-2">
                {Object.entries(METHOD_LABELS).map(([k, v]) => (
                  <button
                    key={k}
                    type="button"
                    data-testid={`add-payment-${k}`}
                    onClick={() => addPayment(k)}
                    className="h-9 px-3 rounded-md border border-zinc-200 text-xs font-semibold hover:border-[#F05D23] hover:text-[#F05D23] transition-colors"
                  >
                    + {v}
                  </button>
                ))}
              </div>
            </div>

            {payments.length === 0 ? (
              <div className="border border-dashed border-zinc-300 rounded-lg p-8 text-center text-sm text-zinc-500">
                Nenhuma condição adicionada. Clique em um dos botões acima para começar.
              </div>
            ) : (
              <div className="space-y-2">
                {payments.map((p, idx) => (
                  <div key={p.id} className="grid grid-cols-12 gap-2 items-end p-3 border border-zinc-200 rounded-lg" data-testid={`payment-row-${idx}`}>
                    <div className="col-span-12 sm:col-span-4">
                      <Label className="text-xs">Forma</Label>
                      <Select value={p.method} onValueChange={(v) => updatePayment(idx, { method: v })}>
                        <SelectTrigger data-testid={`payment-method-${idx}`} className="h-10"><SelectValue /></SelectTrigger>
                        <SelectContent>
                          {Object.entries(METHOD_LABELS).map(([k, v]) => (
                            <SelectItem key={k} value={k}>{v}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="col-span-6 sm:col-span-3">
                      <Label className="text-xs">Valor (R$)</Label>
                      <Input
                        data-testid={`payment-amount-${idx}`}
                        type="number" step="0.01" min="0"
                        value={p.amount}
                        onChange={(e) => updatePayment(idx, { amount: e.target.value })}
                      />
                    </div>
                    {p.method === "credito" && (
                      <div className="col-span-6 sm:col-span-3">
                        <Label className="text-xs">Parcelas</Label>
                        <Select value={String(p.installments || 1)} onValueChange={(v) => updatePayment(idx, { installments: parseInt(v) })}>
                          <SelectTrigger data-testid={`payment-installments-${idx}`} className="h-10"><SelectValue /></SelectTrigger>
                          <SelectContent>
                            {Array.from({ length: 12 }, (_, i) => i + 1).map(n => (
                              <SelectItem key={n} value={String(n)}>{n}x{n > 1 && p.amount ? ` de ${fmtMoney(Number(p.amount) / n)}` : ""}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    )}
                    {p.method === "boleto" && (
                      <div className="col-span-12 sm:col-span-5">
                        <Label className="text-xs">Vencimentos (dias após emissão)</Label>
                        <Input
                          data-testid={`payment-boleto-days-${idx}`}
                          placeholder="ex.: 30, 60, 90"
                          value={(p.boleto_days || []).join(", ")}
                          onChange={(e) => updatePayment(idx, { boleto_days: parseBoletoDays(e.target.value) })}
                        />
                        <div className="flex gap-1 mt-1 flex-wrap">
                          <button type="button" onClick={() => updatePayment(idx, { boleto_days: [30, 60, 90] })} className="text-[10px] px-2 py-0.5 rounded bg-zinc-100 hover:bg-[#FDF0EC] hover:text-[#F05D23] font-semibold">30/60/90</button>
                          <button type="button" onClick={() => updatePayment(idx, { boleto_days: [15, 30, 45] })} className="text-[10px] px-2 py-0.5 rounded bg-zinc-100 hover:bg-[#FDF0EC] hover:text-[#F05D23] font-semibold">15/30/45</button>
                          <button type="button" onClick={() => updatePayment(idx, { boleto_days: [28, 56, 84, 112] })} className="text-[10px] px-2 py-0.5 rounded bg-zinc-100 hover:bg-[#FDF0EC] hover:text-[#F05D23] font-semibold">4x 28d</button>
                          <button type="button" onClick={() => updatePayment(idx, { boleto_days: [] })} className="text-[10px] px-2 py-0.5 rounded bg-zinc-100 hover:bg-red-50 hover:text-red-600 font-semibold">à vista</button>
                        </div>
                        {(p.boleto_days || []).length > 0 && Number(p.amount) > 0 && (
                          <div className="mt-2 text-[11px] text-zinc-600 font-mono-num">
                            {p.boleto_days.length}x de {fmtMoney(Number(p.amount) / p.boleto_days.length)} nos dias {p.boleto_days.join("/")}
                          </div>
                        )}
                      </div>
                    )}
                    <div className="col-span-12 sm:col-span-2 flex justify-end">
                      <button data-testid={`remove-payment-${idx}`} onClick={() => removePayment(idx)} className="h-10 w-10 rounded hover:bg-red-50 text-zinc-400 hover:text-red-600 grid place-items-center">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Summary */}
          <div className="grid sm:grid-cols-3 gap-4">
            <div className="border border-zinc-200 rounded-lg bg-white p-4">
              <div className="text-xs uppercase tracking-wider text-zinc-500">Total do documento</div>
              <div className="font-mono-num text-2xl font-bold mt-1">{fmtMoney(totals.net)}</div>
            </div>
            <div className="border border-zinc-200 rounded-lg bg-white p-4">
              <div className="text-xs uppercase tracking-wider text-zinc-500">Total pago</div>
              <div className="font-mono-num text-2xl font-bold mt-1">{fmtMoney(totalPaid)}</div>
            </div>
            <div className={`border rounded-lg p-4 ${Math.abs(remaining) < 0.01 ? "bg-[#FDF0EC] border-[#F05D23]" : "bg-white border-zinc-200"}`}>
              <div className="text-xs uppercase tracking-wider text-zinc-500">Restante</div>
              <div className={`font-mono-num text-2xl font-bold mt-1 ${remainingClass()}`}>
                {fmtMoney(remaining)}
              </div>
            </div>
          </div>

          <div className="flex justify-between">
            <Button variant="outline" onClick={() => setTab("itens")} className="h-11">← Voltar aos itens</Button>
            <Button
              data-testid="save-doc-btn"
              onClick={save} disabled={saving}
              className="h-11 px-6 bg-[#F05D23] hover:bg-[#D94E1B] text-white font-semibold"
            >
              <Save className="w-4 h-4 mr-2" />
              {saveButtonLabel()}
            </Button>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
