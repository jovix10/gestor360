import { Link } from "react-router-dom";
import { Users, Package, FileText, ScrollText, ArrowRight, Plus, Settings, LineChart } from "lucide-react";

const shortcuts = [
  { to: "/orcamento", label: "Novo Documento", desc: "Monte um orçamento ou venda", icon: Plus, primary: true, testId: "sc-new-doc" },
  { to: "/clientes", label: "Clientes", desc: "Cadastro e histórico", icon: Users, testId: "sc-clients" },
  { to: "/produtos", label: "Produtos", desc: "Catálogo e preços", icon: Package, testId: "sc-products" },
  { to: "/documentos", label: "Documentos", desc: "Orçamentos e vendas", icon: ScrollText, testId: "sc-documents" },
  { to: "/financas", label: "Finanças", desc: "Métricas e receita", icon: LineChart, testId: "sc-finances" },
  { to: "/configuracoes", label: "Empresa", desc: "Dados e logo do PDF", icon: Settings, testId: "sc-settings" },
];

export default function Dashboard() {
  return (
    <div className="space-y-10">
      <div>
        <div className="text-xs uppercase tracking-widest text-[#F05D23] font-semibold">Bem-vindo ao Gestor360</div>
        <h1 className="font-display text-3xl sm:text-4xl font-semibold tracking-tight mt-2">Por onde começar?</h1>
        <p className="text-sm text-zinc-500 mt-2 max-w-xl">
          Um ambiente limpo para você tocar sua operação. Escolha um atalho abaixo e siga em frente.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {shortcuts.map((s) => (
          <Link
            key={s.to}
            to={s.to}
            data-testid={s.testId}
            className={`group p-6 border rounded-lg transition-all
              ${s.primary
                ? "bg-[#09090B] text-white border-[#09090B] hover:bg-[#F05D23] hover:border-[#F05D23]"
                : "bg-white border-zinc-200 hover:border-[#F05D23]"}`}
          >
            <div className="flex items-center justify-between">
              <s.icon className={`w-6 h-6 ${s.primary ? "text-[#F05D23] group-hover:text-white" : "text-zinc-400 group-hover:text-[#F05D23]"} transition-colors`} />
              <ArrowRight className={`w-4 h-4 ${s.primary ? "text-white/70" : "text-zinc-300 group-hover:text-[#F05D23]"} group-hover:translate-x-0.5 transition-all`} />
            </div>
            <div className="font-display text-xl font-semibold mt-6">{s.label}</div>
            <div className={`text-sm mt-1 ${s.primary ? "text-zinc-300" : "text-zinc-500"}`}>{s.desc}</div>
          </Link>
        ))}
      </div>
    </div>
  );
}
