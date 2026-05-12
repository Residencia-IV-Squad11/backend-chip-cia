import { Link, useLocation } from "wouter";
import { motion } from "framer-motion";
import { LayoutDashboard, MessageSquarePlus, History, Settings, ChevronLeft, ChevronRight, Zap } from "lucide-react";
import { cn } from "@/lib/utils";

interface SidebarProps {
  collapsed: boolean;
  setCollapsed: (v: boolean) => void;
}

export function Sidebar({ collapsed, setCollapsed }: SidebarProps) {
  const [location] = useLocation();

  const navItems = [
    { href: "/", icon: LayoutDashboard, label: "Dashboard" },
    { href: "/nova-analise", icon: MessageSquarePlus, label: "Nova Análise" },
    { href: "/historico", icon: History, label: "Histórico" },
    { href: "/configuracoes", icon: Settings, label: "Configurações" },
  ];

  return (
    <motion.aside
      initial={{ width: 256 }}
      animate={{ width: collapsed ? 80 : 256 }}
      transition={{ type: "spring", stiffness: 300, damping: 30 }}
      className="relative z-20 flex h-screen flex-col border-r border-white/10 bg-sidebar-background glass-panel-heavy"
    >
      <div className="flex h-20 items-center justify-between px-6">
        <div className={cn("flex items-center gap-3 overflow-hidden", collapsed ? "w-0 opacity-0" : "w-auto opacity-100 transition-opacity duration-300 delay-100")}>
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-white shadow-[0_0_15px_rgba(229,9,20,0.5)]">
            <Zap className="h-5 w-5" />
          </div>
          <span className="font-display text-lg font-bold tracking-wider text-white">CHIP & CIA</span>
        </div>
        
        {collapsed && (
          <div className="mx-auto flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-white shadow-[0_0_15px_rgba(229,9,20,0.5)]">
            <Zap className="h-5 w-5" />
          </div>
        )}
      </div>

      <nav className="flex-1 space-y-2 px-3 py-6">
        {navItems.map((item) => {
          const isActive = location === item.href;
          const Icon = item.icon;
          
          return (
            <Link key={item.href} href={item.href}>
              <div
                className={cn(
                  "group relative flex cursor-pointer items-center rounded-xl px-3 py-3 transition-all duration-200",
                  isActive 
                    ? "bg-primary/10 text-white" 
                    : "text-muted-foreground hover:bg-white/5 hover:text-white"
                )}
              >
                {isActive && (
                  <motion.div
                    layoutId="active-nav"
                    className="absolute left-0 top-0 h-full w-1 rounded-r-full bg-primary shadow-[0_0_10px_rgba(229,9,20,0.8)]"
                  />
                )}
                <Icon className={cn("h-5 w-5 flex-shrink-0 transition-colors", isActive ? "text-primary" : "")} />
                
                <span
                  className={cn(
                    "ml-3 whitespace-nowrap font-medium transition-all duration-300",
                    collapsed ? "w-0 opacity-0 hidden" : "opacity-100 w-auto"
                  )}
                >
                  {item.label}
                </span>
              </div>
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-white/5">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="flex h-10 w-full items-center justify-center rounded-lg text-muted-foreground hover:bg-white/5 hover:text-white transition-colors"
        >
          {collapsed ? <ChevronRight className="h-5 w-5" /> : <ChevronLeft className="h-5 w-5" />}
        </button>
      </div>
    </motion.aside>
  );
}
