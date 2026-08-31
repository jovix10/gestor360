import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { LayoutDashboard, Users, Package, FileText, ScrollText, Settings, LogOut, Menu, MapPin, Clock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent } from "@/components/ui/sheet";

const nav = [
  { to: "/dashboard", label: "Painel", icon: LayoutDashboard, testId: "nav-dashboard" },
  { to: "/clientes", label: "Clientes", icon: Users, testId: "nav-clients" },
  { to: "/produtos", label: "Produtos", icon: Package, testId: "nav-products" },
  { to: "/orcamento", label: "Novo Documento", icon: FileText, testId: "nav-new-doc" },
  { to: "/documentos", label: "Documentos", icon: ScrollText, testId: "nav-documents" },
  { to: "/configuracoes", label: "Empresa", icon: Settings, testId: "nav-settings" },
];

function SidebarInner({ onLogout }) {
  return (
    <div className="h-full flex flex-col bg-white">
      <div className="p-5 flex items-center gap-3 border-b border-zinc-200">
        <div className="w-9 h-9 rounded-md bg-[#F05D23] grid place-items-center font-display font-bold text-white">G</div>
        <div>
          <div className="font-display font-bold text-lg leading-none">Gestor360</div>
          <div className="text-[10px] uppercase tracking-widest text-zinc-400 mt-1">ERP · Vendas</div>
        </div>
      </div>
      <nav className="flex-1 p-3 space-y-1">
        {nav.map((n) => (
          <NavLink
            key={n.to}
            to={n.to}
            data-testid={n.testId}
            className={({ isActive }) =>
              `group flex items-center gap-3 px-3 py-2.5 rounded-md text-sm transition-colors relative
              ${isActive
                ? "bg-[#FDF0EC] text-[#F05D23] font-semibold before:absolute before:left-0 before:top-1/2 before:-translate-y-1/2 before:h-6 before:w-[3px] before:rounded-full before:bg-[#F05D23]"
                : "text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900"}`
            }
          >
            <n.icon className="w-[18px] h-[18px]" />
            <span>{n.label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="p-3 border-t border-zinc-200">
        <Button
          data-testid="logout-btn"
          variant="ghost"
          onClick={onLogout}
          className="w-full justify-start gap-3 text-zinc-600 hover:text-zinc-900 hover:bg-zinc-50"
        >
          <LogOut className="w-[18px] h-[18px]" />
          Sair
        </Button>
      </div>
    </div>
  );
}

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [now, setNow] = useState(new Date());
  const [location, setLocation] = useState("—");
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    // browser geolocation → reverse geocode (best effort, non-blocking)
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        try {
          const r = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${pos.coords.latitude}&lon=${pos.coords.longitude}&zoom=10`, {
            headers: { "Accept-Language": "pt-BR" },
          });
          const d = await r.json();
          const city = d.address?.city || d.address?.town || d.address?.village || d.address?.state || d.display_name;
          if (city) setLocation(city);
        } catch {}
      },
      () => {},
      { maximumAge: 3600_000, timeout: 5000 }
    );
  }, []);

  const doLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  const dateStr = now.toLocaleDateString("pt-BR", { weekday: "long", day: "2-digit", month: "long" });
  const timeStr = now.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  const firstName = user?.name?.split(" ")[0] || "usuário";

  return (
    <div className="min-h-screen flex bg-[#FCFCFC]">
      {/* Desktop sidebar */}
      <aside className="hidden lg:block w-64 border-r border-zinc-200 shrink-0 sticky top-0 h-screen">
        <SidebarInner onLogout={doLogout} />
      </aside>

      {/* Mobile drawer */}
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent side="left" className="p-0 w-72">
          <SidebarInner onLogout={doLogout} />
        </SheetContent>
      </Sheet>

      <div className="flex-1 min-w-0">
        <header className="sticky top-0 z-30 backdrop-blur-xl bg-white/85 border-b border-zinc-200">
          <div className="flex items-center gap-3 px-4 sm:px-6 lg:px-8 h-16">
            <Button
              data-testid="menu-open-btn"
              variant="ghost" size="icon"
              className="lg:hidden"
              onClick={() => setOpen(true)}
            >
              <Menu className="w-5 h-5" />
            </Button>
            <div className="min-w-0">
              <div className="font-display text-lg sm:text-xl font-semibold tracking-tight truncate">
                Olá, <span className="text-[#F05D23]" data-testid="greeting-name">{firstName}</span>
              </div>
              <div className="flex items-center gap-3 text-xs text-zinc-500 mt-0.5">
                <span className="capitalize hidden sm:inline">{dateStr}</span>
                <span className="inline-flex items-center gap-1"><Clock className="w-3 h-3" />{timeStr}</span>
                <span className="inline-flex items-center gap-1"><MapPin className="w-3 h-3" />{location}</span>
              </div>
            </div>
            <div className="ml-auto flex items-center gap-3">
              {user?.picture ? (
                <img src={user.picture} alt={user.name} className="w-9 h-9 rounded-full object-cover ring-2 ring-white shadow-sm" />
              ) : (
                <div className="w-9 h-9 rounded-full bg-zinc-900 text-white grid place-items-center font-semibold text-sm">
                  {firstName.charAt(0).toUpperCase()}
                </div>
              )}
            </div>
          </div>
        </header>

        <main className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
