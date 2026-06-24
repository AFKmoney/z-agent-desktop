"use client";

import { motion } from "framer-motion";
import {
  LayoutDashboard, MessageCircle, ListTodo, Activity,
  BarChart3, Zap, BookOpen, Users, Settings as SettingsIcon,
  Bot, Cpu,
} from "lucide-react";
import { cn } from "@/lib/utils";

export type SectionId =
  | "overview"
  | "chat"
  | "tasks"
  | "monitor"
  | "analytics"
  | "automation"
  | "knowledge"
  | "agents"
  | "settings";

interface NavItem {
  id: SectionId;
  label: string;
  label_fr: string;
  icon: typeof LayoutDashboard;
  description: string;
  description_fr: string;
}

const NAV_ITEMS: NavItem[] = [
  {
    id: "overview",
    label: "Overview",
    label_fr: "Aperçu",
    icon: LayoutDashboard,
    description: "Agent status and quick actions",
    description_fr: "Statut de l'agent et actions rapides",
  },
  {
    id: "chat",
    label: "Chat",
    label_fr: "Chat",
    icon: MessageCircle,
    description: "Conversations with custom agents",
    description_fr: "Conversations avec agents personnalisés",
  },
  {
    id: "tasks",
    label: "Tasks",
    label_fr: "Tâches",
    icon: ListTodo,
    description: "Submit tasks and view history",
    description_fr: "Soumettre des tâches et voir l'historique",
  },
  {
    id: "monitor",
    label: "Monitor",
    label_fr: "Moniteur",
    icon: Activity,
    description: "Live logs, screenshots, audit trail",
    description_fr: "Logs en direct, captures, audit",
  },
  {
    id: "analytics",
    label: "Analytics",
    label_fr: "Analytique",
    icon: BarChart3,
    description: "Costs, activity heatmap, stats",
    description_fr: "Coûts, activité, statistiques",
  },
  {
    id: "automation",
    label: "Automation",
    label_fr: "Automatisation",
    icon: Zap,
    description: "Scheduled tasks, watchers, webhooks",
    description_fr: "Tâches planifiées, watchers, webhooks",
  },
  {
    id: "knowledge",
    label: "Knowledge",
    label_fr: "Connaissance",
    icon: BookOpen,
    description: "RAG documents and vector memory",
    description_fr: "Documents RAG et mémoire vectorielle",
  },
  {
    id: "agents",
    label: "Agents",
    label_fr: "Agents",
    icon: Users,
    description: "Create and manage custom agents",
    description_fr: "Créer et gérer des agents personnalisés",
  },
  {
    id: "settings",
    label: "Settings",
    label_fr: "Paramètres",
    icon: SettingsIcon,
    description: "API keys and configuration",
    description_fr: "Clés API et configuration",
  },
];

export function Sidebar({
  active,
  onSelect,
  lang,
  agentState,
  connected,
}: {
  active: SectionId;
  onSelect: (id: SectionId) => void;
  lang: "en" | "fr";
  agentState: string;
  connected: boolean;
}) {
  return (
    <aside className="w-60 flex-shrink-0 border-r border-border/50 flex flex-col h-full">
      {/* Logo */}
      <div className="p-4 border-b border-border/50">
        <div className="flex items-center gap-2.5">
          <motion.div
            className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary/30 to-accent/30 border border-primary/40 flex items-center justify-center flex-shrink-0"
            animate={{ boxShadow: ["0 0 15px oklch(0.78 0.18 165 / 0.2)", "0 0 25px oklch(0.78 0.18 165 / 0.4)", "0 0 15px oklch(0.78 0.18 165 / 0.2)"] }}
            transition={{ duration: 3, repeat: Infinity }}
          >
            <Bot className="w-5 h-5 text-primary" />
          </motion.div>
          <div className="min-w-0">
            <h1 className="text-sm font-bold tracking-tight leading-none">Z.AGENT</h1>
            <p className="text-[9px] text-muted-foreground mt-0.5 font-mono">
              v4.0 · {connected ? "● online" : "○ offline"}
            </p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-2 px-2 space-y-0.5">
        {NAV_ITEMS.map((item, i) => {
          const Icon = item.icon;
          const isActive = active === item.id;
          return (
            <motion.button
              key={item.id}
              onClick={() => onSelect(item.id)}
              className={cn(
                "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all group relative",
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:text-foreground hover:bg-accent/20"
              )}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.03 }}
              title={lang === "fr" ? item.description_fr : item.description}
            >
              {isActive && (
                <motion.div
                  className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-6 bg-primary rounded-full"
                  layoutId="activeNav"
                />
              )}
              <Icon className={cn("w-4 h-4 flex-shrink-0", isActive && "text-primary")} />
              <span className="text-sm font-medium truncate">
                {lang === "fr" ? item.label_fr : item.label}
              </span>
            </motion.button>
          );
        })}
      </nav>

      {/* Footer — agent state indicator */}
      <div className="p-3 border-t border-border/50">
        <div className="glass rounded-lg p-2.5 flex items-center gap-2.5">
          <div className="relative">
            <motion.div
              className={cn(
                "w-2 h-2 rounded-full",
                agentState === "idle" ? "bg-emerald-500"
                : agentState === "planning" ? "bg-amber-500"
                : agentState === "executing" ? "bg-cyan-500"
                : agentState === "error" || agentState === "stopped" ? "bg-red-500"
                : "bg-zinc-500"
              )}
              animate={agentState !== "stopped" && agentState !== "paused" ? { scale: [1, 1.3, 1] } : {}}
              transition={{ duration: 1.5, repeat: Infinity }}
            />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-[10px] text-muted-foreground uppercase tracking-wider">
              {lang === "fr" ? "État" : "State"}
            </p>
            <p className="text-xs font-mono font-medium truncate capitalize">{agentState}</p>
          </div>
          <Cpu className="w-3 h-3 text-muted-foreground" />
        </div>
      </div>
    </aside>
  );
}
