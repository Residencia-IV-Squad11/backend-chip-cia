import { useState } from "react";
import { Sidebar } from "./sidebar";
import { motion } from "framer-motion";

export function PageLayout({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="flex h-screen overflow-hidden bg-background text-foreground selection:bg-primary/30">
      <Sidebar collapsed={collapsed} setCollapsed={setCollapsed} />
      <main className="flex-1 overflow-y-auto overflow-x-hidden relative">
        <div className="absolute inset-0 z-0 opacity-[0.03] pointer-events-none" 
             style={{ backgroundImage: `url(${import.meta.env.BASE_URL}images/auth-bg.png)`, backgroundSize: 'cover', backgroundPosition: 'center' }} />
        
        <motion.div 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="relative z-10 mx-auto max-w-7xl p-6 md:p-10 min-h-full"
        >
          {children}
        </motion.div>
      </main>
    </div>
  );
}
