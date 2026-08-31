import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, fmtMoney, fmtDateTime } from "@/lib/api";
import { Users, Package, FileText, TrendingUp, ArrowRight } from "lucide-react";

const cards = [
  { key: "clients", label: "Clientes", icon: Users, to: "/clientes" },
  { key: "products", label: "Produtos", icon: Package, to: "/produtos" },
  { key: "orcamentos", label: "Orçamentos", icon: FileText, to: "/documentos" },
  { key: "vendas", label: "Vendas", icon: TrendingUp, to: "/documentos" },
];

export default function Finances() {
  const [stats, setStats] = useState(null);
  const [recent, setRecent] = useState([]);

  useEffect(() => {
    api.get("/stats").then(r => setStats(r.data));
    api.get("/documents").then(r => setRecent(r.data.slice(0, 8)));
  }, []);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-3xl sm:text-4xl font-semibold tracking-tight">Finanças</h1>
        <p className="text-sm text-zinc-500 mt-1">Métricas, receita e documentos recentes.</p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {cards.map((c) => (
          <Link
            to={c.to}
            key={c.key}
            data-testid={`stat-${c.key}`}
            className="group p-5 border border-zinc-200 rounded-lg bg-white hover:border-[#F05D23] transition-colors"
          >
            <div className="flex items-center justify-between">
              <c.icon className="w-5 h-5 text-zinc-400 group-hover:text-[#F05D23] transition-colors" />
              <ArrowRight className="w-4 h-4 text-zinc-300 group-hover:text-[#F05D23] group-hover:translate-x-0.5 transition-all" />
            </div>
            <div className="mt-4 font-mono-num text-3xl font-semibold tracking-tight text-zinc-900">
              {stats ? stats[c.key] : "—"}
            </div>
            <div className="text-xs uppercase tracking-wider text-zinc-500 mt-1">{c.label}</div>
          </Link>
        ))}
      </div>

      {/* Revenue banner */}
      <div className="p-6 sm:p-8 rounded-lg border border-zinc-200 bg-gradient-to-br from-white to-[#FDF0EC] flex flex-col sm:flex-row sm:items-center gap-6">
        <div className="flex-1">
          <div className="text-xs uppercase tracking-wider text-zinc-500">Receita do mês</div>
          <div className="font-mono-num text-4xl sm:text-5xl font-bold tracking-tight mt-2 text-zinc-900">
            {stats ? fmtMoney(stats.revenue_month) : "—"}
          </div>
        </div>
        <Link
          to="/documentos"
          data-testid="see-documents-btn"
          className="inline-flex items-center gap-2 px-5 h-11 rounded-md border border-zinc-900 text-zinc-900 hover:bg-zinc-900 hover:text-white transition-colors font-semibold"
        >
          Ver documentos <ArrowRight className="w-4 h-4" />
        </Link>
      </div>

      {/* Recent */}
      <div>
        <h2 className="font-display text-xl font-semibold mb-4">Recentes</h2>
        {recent.length === 0 ? (
          <div className="border border-dashed border-zinc-300 rounded-lg p-10 text-center">
            <p className="text-sm text-zinc-500">Nenhum documento ainda.</p>
            <Link to="/orcamento" className="text-[#F05D23] font-semibold text-sm hover:underline">Criar o primeiro →</Link>
          </div>
        ) : (
          <div className="border border-zinc-200 rounded-lg overflow-hidden bg-white">
            {recent.map((d) => (
              <Link
                key={d.id}
                to={`/documentos`}
                className="flex items-center justify-between p-4 border-b border-zinc-100 last:border-b-0 hover:bg-zinc-50 transition-colors"
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded ${d.doc_type === "orcamento" ? "bg-zinc-100 text-zinc-700" : "bg-[#FDF0EC] text-[#F05D23]"}`}>
                      {d.doc_type === "orcamento" ? "Orçamento" : "Venda"}
                    </span>
                    <span className="font-mono-num text-sm">Nº {String(d.number).padStart(6, "0")}</span>
                    <span className="text-xs text-zinc-400">· {fmtDateTime(d.created_at)}</span>
                  </div>
                  <div className="text-sm text-zinc-700 mt-1 truncate">{d.client_name}</div>
                </div>
                <div className="font-mono-num text-sm font-semibold text-zinc-900">{fmtMoney(d.total)}</div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
