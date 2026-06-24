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
  labels: Record<string, string>;
  icon: typeof LayoutDashboard;
  descriptions: Record<string, string>;
}

const NAV_ITEMS: NavItem[] = [
  {
    id: "overview",
    labels: { en: "Overview", fr: "Aperçu", es: "Resumen", de: "Übersicht", pt: "Visão Geral" },
    icon: LayoutDashboard,
    descriptions: { en: "Agent status and quick actions", fr: "Statut de l'agent et actions rapides", es: "Estado del agente y acciones rápidas", de: "Agent-Status und Schnellaktionen", pt: "Status do agente e ações rápidas" },
  },
  {
    id: "chat",
    labels: { en: "Chat", fr: "Chat", es: "Chat", de: "Chat", pt: "Chat" },
    icon: MessageCircle,
    descriptions: { en: "Conversations with custom agents", fr: "Conversations avec agents personnalisés", es: "Conversaciones con agentes personalizados", de: "Konversationen mit benutzerdefinierten Agenten", pt: "Conversas com agentes personalizados" },
  },
  {
    id: "tasks",
    labels: { en: "Tasks", fr: "Tâches", es: "Tareas", de: "Aufgaben", pt: "Tarefas" },
    icon: ListTodo,
    descriptions: { en: "Submit tasks and view history", fr: "Soumettre des tâches et voir l'historique", es: "Enviar tareas y ver historial", de: "Aufgaben senden und Verlauf anzeigen", pt: "Enviar tarefas e ver histórico" },
  },
  {
    id: "monitor",
    labels: { en: "Monitor", fr: "Moniteur", es: "Monitor", de: "Monitor", pt: "Monitor" },
    icon: Activity,
    descriptions: { en: "Live logs, screenshots, audit trail", fr: "Logs en direct, captures, audit", es: "Registros en vivo, capturas, auditoría", de: "Live-Protokolle, Screenshots, Audit-Trail", pt: "Logs ao vivo, capturas, auditoria" },
  },
  {
    id: "analytics",
    labels: { en: "Analytics", fr: "Analytique", es: "Analítica", de: "Analytik", pt: "Análises" },
    icon: BarChart3,
    descriptions: { en: "Costs, activity heatmap, stats", fr: "Coûts, activité, statistiques", es: "Costos, mapa de actividad, estadísticas", de: "Kosten, Aktivitäts-Heatmap, Statistiken", pt: "Custos, mapa de atividade, estatísticas" },
  },
  {
    id: "automation",
    labels: { en: "Automation", fr: "Automatisation", es: "Automatización", de: "Automatisierung", pt: "Automação" },
    icon: Zap,
    descriptions: { en: "Scheduled tasks, watchers, webhooks", fr: "Tâches planifiées, watchers, webhooks", es: "Tareas programadas, watchers, webhooks", de: "Geplante Aufgaben, Watcher, Webhooks", pt: "Tarefas agendadas, watchers, webhooks" },
  },
  {
    id: "knowledge",
    labels: { en: "Knowledge", fr: "Connaissance", es: "Conocimiento", de: "Wissen", pt: "Conhecimento" },
    icon: BookOpen,
    descriptions: { en: "RAG documents and vector memory", fr: "Documents RAG et mémoire vectorielle", es: "Documentos RAG y memoria vectorial", de: "RAG-Dokumente und Vektorspeicher", pt: "Documentos RAG e memória vetorial" },
  },
  {
    id: "agents",
    labels: { en: "Agents", fr: "Agents", es: "Agentes", de: "Agenten", pt: "Agentes" },
    icon: Users,
    descriptions: { en: "Create and manage custom agents", fr: "Créer et gérer des agents personnalisés", es: "Crear y gestionar agentes personalizados", de: "Benutzerdefinierte Agenten erstellen und verwalten", pt: "Criar e gerenciar agentes personalizados" },
  },
  {
    id: "settings",
    labels: { en: "Settings", fr: "Paramètres", es: "Ajustes", de: "Einstellungen", pt: "Configurações" },
    icon: SettingsIcon,
    descriptions: { en: "API keys and configuration", fr: "Clés API et configuration", es: "Claves API y configuración", de: "API-Schlüssel und Konfiguration", pt: "Chaves de API e configuração" },
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
              title={item.descriptions[lang] || item.descriptions.en}
            >
              {isActive && (
                <motion.div
                  className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-6 bg-primary rounded-full"
                  layoutId="activeNav"
                />
              )}
              <Icon className={cn("w-4 h-4 flex-shrink-0", isActive && "text-primary")} />
              <span className="text-sm font-medium truncate">
                {item.labels[lang] || item.labels.en}
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
              {lang === "fr" ? "État" : lang === "es" ? "Estado" : lang === "de" ? "Zustand" : lang === "pt" ? "Estado" : "State"}
            </p>
            <p className="text-xs font-mono font-medium truncate capitalize">{agentState}</p>
          </div>
          <Cpu className="w-3 h-3 text-muted-foreground" />
        </div>
      </div>
    </aside>
  );
}
