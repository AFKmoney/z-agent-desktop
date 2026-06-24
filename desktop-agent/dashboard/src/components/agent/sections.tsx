"use client";

import { useEffect, useState, useRef, useCallback, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Bot, Activity, Send, Play, Pause, RefreshCw,
  Terminal, Image as ImageIcon, Brain, Cpu, Clock, Zap,
  ChevronRight, Circle, CheckCircle2, XCircle,
  Camera, FileText, Mail, Calendar, Globe, Monitor, MonitorSmartphone,
  Lightbulb, Eye, Sparkles, Search, Code, Network,
  Mic, Plug, Radio, MessageSquare, Command, MessageCircle, Users,
  Plus, Trash2, Pin, Loader2, User, Copy, DollarSign, Shield,
  TrendingUp, BookOpen, Bell, Save, Edit,
  ListTodo, BarChart3,
} from "lucide-react";
import { useAgent } from "@/hooks/use-agent";
import { agentApi, type TaskRecord } from "@/lib/agent-api";
import { t, type Lang } from "@/lib/i18n";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";
import {
  AnimatedCounter, StateOrb, GlassCard, StatPill, ModuleTile,
  ThinkingStream, TaskCard, ParticleBackground, VoiceWaveform,
} from "@/components/agent";
import {
  ActivityHeatmap, CostPanel, AuditLogPanel, ScheduledTasksPanel,
  KnowledgeBasePanel, NotificationsPanel,
} from "@/components/agent/panels";
import {
  LLMProviderSwitcher, SmartSuggestionsPanel, PromptTemplatesPanel, BackupPanel,
} from "@/components/agent/power-panels";
import { SettingsModal } from "@/components/agent/settings-modal";
import { ChatInterface } from "@/components/agent/chat-interface";
import { AgentCreatorModal } from "@/components/agent/agent-creator";

// ============================================================
// SHARED COMPONENTS
// ============================================================

// Multi-language helper for inline strings
function L(lang: Lang, texts: Record<string, string>): string {
  return texts[lang] || texts.en;
}

export function SectionHeader({
  title, subtitle, icon: Icon, lang, actions,
}: {
  title: string;
  subtitle: string;
  icon: typeof Bot;
  lang: Lang;
  actions?: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between mb-6">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-primary/15 border border-primary/30 flex items-center justify-center">
          <Icon className="w-5 h-5 text-primary" />
        </div>
        <div>
          <h2 className="text-xl font-bold tracking-tight">{title}</h2>
          <p className="text-xs text-muted-foreground">{subtitle}</p>
        </div>
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}

// ============================================================
// OVERVIEW SECTION
// ============================================================

const MODULES_LIST = ["screen", "files", "email", "calendar", "browser", "system", "windows", "code", "web", "voice", "plugin", "mcp", "vision", "slack"];

const CAPABILITIES = [
  { icon: Sparkles, labels: { en: "ReAct loop", fr: "Boucle ReAct", es: "Bucle ReAct", de: "ReAct-Schleife", pt: "Loop ReAct" }, color: "#10B981" },
  { icon: Code, labels: { en: "Code interpreter", fr: "Interpréteur code", es: "Intérprete de código", de: "Code-Interpreter", pt: "Interpretador de código" }, color: "#06B6D4" },
  { icon: Search, labels: { en: "Web search", fr: "Recherche web", es: "Búsqueda web", de: "Websuche", pt: "Busca web" }, color: "#06B6D4" },
  { icon: Network, labels: { en: "Multi-agent", fr: "Multi-agent", es: "Multi-agente", de: "Multi-Agent", pt: "Multi-agente" }, color: "#EC4899" },
  { icon: Brain, labels: { en: "Skill library", fr: "Bibliothèque skills", es: "Biblioteca de skills", de: "Skill-Bibliothek", pt: "Biblioteca de skills" }, color: "#10B981" },
  { icon: Zap, labels: { en: "GLM tool calling", fr: "GLM tool calling", es: "Llamada de herramientas GLM", de: "GLM Tool-Calling", pt: "Chamada de ferramentas GLM" }, color: "#F59E0B" },
  { icon: Mic, labels: { en: "Voice control", fr: "Contrôle vocal", es: "Control por voz", de: "Sprachsteuerung", pt: "Controle por voz" }, color: "#F59E0B" },
  { icon: MessageSquare, labels: { en: "Long context", fr: "Contexte long", es: "Contexto largo", de: "Langer Kontext", pt: "Contexto longo" }, color: "#8B5CF6" },
  { icon: Plug, labels: { en: "Plugin marketplace", fr: "Marché plugins", es: "Mercado de plugins", de: "Plugin-Marktplatz", pt: "Mercado de plugins" }, color: "#8B5CF6" },
  { icon: Network, labels: { en: "MCP protocol", fr: "Protocole MCP", es: "Protocolo MCP", de: "MCP-Protokoll", pt: "Protocolo MCP" }, color: "#EC4899" },
  { icon: Radio, labels: { en: "Vision streaming", fr: "Vision streaming", es: "Transmisión de visión", de: "Vision-Streaming", pt: "Transmissão de visão" }, color: "#10B981" },
  { icon: Cpu, labels: { en: "100% Windows", fr: "100% Windows", es: "100% Windows", de: "100% Windows", pt: "100% Windows" }, color: "#3B82F6" },
];

const QUICK_ACTIONS = [
  { icon: FileText, labels: { en: "Sort Downloads", fr: "Trier Téléch.", es: "Ordenar Desc.", de: "Downloads sort.", pt: "Ordenar Down." }, prompts: { en: "Organize my Downloads folder by file type", fr: "Organise mon dossier Téléchargements par type de fichier", es: "Organiza mis descargas por tipo de archivo", de: "Ordne meine Downloads nach Dateityp", pt: "Organize meus downloads por tipo de arquivo" }, color: "#10B981" },
  { icon: Mail, labels: { en: "Read emails", fr: "Lire emails", es: "Leer emails", de: "E-Mails lesen", pt: "Ler emails" }, prompts: { en: "Read my 5 latest unread emails and summarize them", fr: "Lis mes 5 derniers emails non lus et fais-moi un résumé", es: "Lee mis 5 últimos correos no leídos y resúmelos", de: "Lies meine 5 letzten ungelesenen E-Mails und fasse sie zusammen", pt: "Leia meus 5 últimos emails não lidos e resuma" }, color: "#F59E0B" },
  { icon: Calendar, labels: { en: "Events", fr: "Événements", es: "Eventos", de: "Termine", pt: "Eventos" }, prompts: { en: "List my 10 upcoming calendar events", fr: "Liste mes 10 prochains événements de calendrier", es: "Lista mis 10 próximos eventos del calendario", de: "Liste meine 10 nächsten Kalendertermine", pt: "Liste meus 10 próximos eventos da agenda" }, color: "#8B5CF6" },
  { icon: Monitor, labels: { en: "Describe screen", fr: "Décrire écran", es: "Describir pantalla", de: "Bildschirm beschreiben", pt: "Descrever tela" }, prompts: { en: "Describe what's currently on my screen", fr: "Décris ce qu'il y a actuellement sur mon écran", es: "Describe lo que hay actualmente en mi pantalla", de: "Beschreibe was aktuell auf meinem Bildschirm ist", pt: "Descreva o que está na minha tela agora" }, color: "#06B6D4" },
  { icon: Cpu, labels: { en: "System info", fr: "Infos système", es: "Info sistema", de: "Systeminfo", pt: "Info sistema" }, prompts: { en: "Give me system info (CPU, RAM, disk)", fr: "Donne-moi les informations système (CPU, RAM, disque)", es: "Dame información del sistema (CPU, RAM, disco)", de: "Gib mir Systeminfo (CPU, RAM, Festplatte)", pt: "Dê informações do sistema (CPU, RAM, disco)" }, color: "#EC4899" },
  { icon: Camera, labels: { en: "Screenshot", fr: "Capture", es: "Captura", de: "Screenshot", pt: "Captura" }, prompts: { en: "Take a screenshot and analyze it", fr: "Prends une capture d'écran et analyse-la", es: "Toma una captura de pantalla y analízala", de: "Mach einen Screenshot und analysiere ihn", pt: "Tire um screenshot e analise" }, color: "#10B981" },
];

export function OverviewSection({
  lang, onNavigate,
}: {
  lang: Lang;
  onNavigate: (section: string) => void;
}) {
  const { status, connected, refresh } = useAgent();
  const { toast } = useToast();
  const [taskInput, setTaskInput] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const state = status?.state ?? "stopped";
  const memory = status?.memory;
  const isLive = state === "planning" || state === "executing";

  const tr = useCallback((key: string, vars?: Record<string, string | number>) => t(key, lang, vars), [lang]);

  const submitTask = async () => {
    if (!taskInput.trim()) return;
    setSubmitting(true);
    try {
      await agentApi.submitTask(taskInput, "dashboard");
      toast({ title: L(lang, { en: "Task sent", fr: "Tâche envoyée", es: "Tarea enviada", de: "Aufgabe gesendet", pt: "Tarefa enviada" }) });
      setTaskInput("");
    } catch (e) {
      toast({ title: tr("toast.error"), description: e instanceof Error ? e.message : "", variant: "destructive" });
    } finally { setSubmitting(false); }
  };

  const sendCommand = async (cmd: "pause" | "resume" | "stop" | "start") => {
    try { await agentApi.command(cmd); setTimeout(refresh, 200); } catch {}
  };

  return (
    <div className="max-w-6xl mx-auto">
      <SectionHeader
        title={L(lang, { en: "Overview", fr: "Aperçu", es: "Resumen", de: "Übersicht", pt: "Visão Geral" })}
        subtitle={L(lang, { en: "Agent status and quick actions", fr: "État de l'agent et actions rapides", es: "Estado del agente y acciones rápidas", de: "Agent-Status und Schnellaktionen", pt: "Status do agente e ações rápidas" })}
        icon={Bot}
        lang={lang}
        actions={
          <>
            <Button size="sm" variant="ghost" onClick={() => sendCommand("pause")} disabled={!isLive && state !== "idle"} className="h-8 w-8 p-0">
              <Pause className="w-3.5 h-3.5" />
            </Button>
            <Button size="sm" variant="ghost" onClick={() => sendCommand("resume")} disabled={state !== "paused"} className="h-8 w-8 p-0">
              <Play className="w-3.5 h-3.5" />
            </Button>
            <Button size="sm" variant="ghost" onClick={refresh} className="h-8 w-8 p-0">
              <RefreshCw className="w-3.5 h-3.5" />
            </Button>
          </>
        }
      />

      {/* Hero strip */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 mb-6">
        <GlassCard className="lg:col-span-3 p-6 flex flex-col items-center justify-center" glow={isLive}>
          <StateOrb state={state} lang={lang} />
        </GlassCard>
        <div className="lg:col-span-9 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          <StatPill icon={Activity} label={tr("label.state")} value={state} color="#10B981" />
          <StatPill icon={Clock} label={tr("label.queue")} value={status?.queue_size ?? 0} color="#06B6D4" />
          <StatPill icon={Brain} label={tr("dash.facts")} value={memory?.facts_count ?? 0} color="#8B5CF6" />
          <StatPill icon={Zap} label={tr("dash.tasks")} value={memory?.tasks_count ?? 0} color="#F59E0B" />
          <StatPill icon={Cpu} label={tr("label.uptime")} value={`${Math.floor((status?.uptime_s ?? 0) / 60)}m`} color="#EC4899" />
        </div>
      </div>

      {/* Quick task input */}
      <GlassCard className="p-4 mb-6" glow={isLive}>
        <div className="flex items-center gap-2 mb-3">
          <Send className="w-4 h-4 text-primary" />
          <h3 className="text-sm font-semibold">{tr("dash.submit_task")}</h3>
          {isLive && (
            <motion.span className="ml-auto text-[10px] font-mono uppercase text-primary flex items-center gap-1" animate={{ opacity: [0.5, 1, 0.5] }} transition={{ duration: 1.5, repeat: Infinity }}>
              <VoiceWaveform active={isLive} />
              {L(lang, { en: "agent busy", fr: "agent actif", es: "agente activo", de: "Agent beschäftigt", pt: "agente ativo" })}
            </motion.span>
          )}
        </div>
        <Textarea
          placeholder={tr("dash.task_placeholder")}
          value={taskInput}
          onChange={e => setTaskInput(e.target.value)}
          rows={2}
          className="resize-none bg-background/50 border-border/50 focus:border-primary/50"
          onKeyDown={e => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submitTask(); }}
        />
        <div className="flex flex-wrap gap-1.5 mt-3">
          {QUICK_ACTIONS.map(qa => {
            const Icon = qa.icon;
            return (
              <button key={qa.labels.en} onClick={() => setTaskInput(qa.prompts[lang] || qa.prompts.en)}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs border border-border/50 bg-card/30 hover:bg-accent/30 transition-all hover:scale-105"
                style={{ borderColor: `${qa.color}30` }}>
                <Icon className="w-3 h-3" style={{ color: qa.color }} />
                {qa.labels[lang] || qa.labels.en}
              </button>
            );
          })}
        </div>
        <div className="flex justify-between items-center mt-3">
          <span className="text-[10px] text-muted-foreground font-mono">⌘+Enter</span>
          <Button size="sm" onClick={submitTask} disabled={!taskInput.trim() || submitting} className="gap-1.5">
            <Send className="w-3.5 h-3.5" />
            {submitting ? L(lang, { en: "Sending...", fr: "Envoi...", es: "Enviando...", de: "Senden...", pt: "Enviando..." }) : tr("dash.send")}
          </Button>
        </div>
      </GlassCard>

      {/* Two columns: modules + capabilities */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <GlassCard className="p-4">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3 flex items-center gap-2">
            <Cpu className="w-3.5 h-3.5" />
            {L(lang, { en: "Modules", fr: "Modules", es: "Módulos", de: "Module", pt: "Módulos" })} ({MODULES_LIST.length})
          </h3>
          <div className="grid grid-cols-4 sm:grid-cols-5 gap-2">
            {MODULES_LIST.map((m, i) => (
              <motion.div key={m} initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: i * 0.02 }}>
                <ModuleTile name={m} />
              </motion.div>
            ))}
          </div>
        </GlassCard>

        <GlassCard className="p-4">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3 flex items-center gap-2">
            <Sparkles className="w-3.5 h-3.5" />
            {L(lang, { en: "Capabilities", fr: "Capacités", es: "Capacidades", de: "Fähigkeiten", pt: "Capacidades" })} ({CAPABILITIES.length})
          </h3>
          <div className="grid grid-cols-2 gap-2">
            {CAPABILITIES.map((cap, i) => {
              const Icon = cap.icon;
              return (
                <motion.div key={i} className="flex items-center gap-2 text-xs" initial={{ opacity: 0, x: -5 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.3 + i * 0.02 }}>
                  <div className="w-6 h-6 rounded-md flex items-center justify-center flex-shrink-0" style={{ background: `${cap.color}15`, border: `1px solid ${cap.color}30` }}>
                    <Icon className="w-3 h-3" style={{ color: cap.color }} />
                  </div>
                  <span className="text-foreground/80 truncate">{cap.labels[lang] || cap.labels.en}</span>
                  <Circle className="w-1 h-1 fill-emerald-500 text-emerald-500 ml-auto flex-shrink-0" />
                </motion.div>
              );
            })}
          </div>
        </GlassCard>
      </div>
    </div>
  );
}

// ============================================================
// TASKS SECTION
// ============================================================

export function TasksSection({ lang }: { lang: Lang }) {
  const { progress, refresh } = useAgent();
  const { toast } = useToast();
  const [tasks, setTasks] = useState<TaskRecord[]>([]);
  const [taskInput, setTaskInput] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [liveTrace, setLiveTrace] = useState<Array<Record<string, unknown>>>([]);
  const [showInput, setShowInput] = useState(false);

  const tr = useCallback((key: string, vars?: Record<string, string | number>) => t(key, lang, vars), [lang]);

  const loadData = useCallback(async () => {
    try {
      const tasksRes = await agentApi.recentTasks(50).catch(() => ({ tasks: [] as TaskRecord[] }));
      setTasks(tasksRes.tasks || []);
    } catch {}
  }, []);

  useEffect(() => {
    loadData();
    const i = setInterval(loadData, 5000);
    return () => clearInterval(i);
  }, [loadData, progress]);

  useEffect(() => {
    if (progress.length === 0) return;
    const last = progress[progress.length - 1];
    if (last.event === "react_thought" || last.event === "react_step") {
      setLiveTrace(prev => [...prev.slice(-30), last as Record<string, unknown>]);
    }
    if (last.event === "task_end") {
      setTimeout(() => { setLiveTrace([]); loadData(); }, 500);
    }
  }, [progress, loadData]);

  const submitTask = async () => {
    if (!taskInput.trim()) return;
    setSubmitting(true);
    try {
      await agentApi.submitTask(taskInput, "dashboard");
      setTaskInput("");
      setShowInput(false);
      setLiveTrace([]);
      toast({ title: L(lang, { en: "Task sent", fr: "Tâche envoyée", es: "Tarea enviada", de: "Aufgabe gesendet", pt: "Tarefa enviada" }) });
      setTimeout(loadData, 500);
    } catch (e) {
      toast({ title: tr("toast.error"), description: e instanceof Error ? e.message : "", variant: "destructive" });
    } finally { setSubmitting(false); }
  };

  return (
    <div className="max-w-4xl mx-auto">
      <SectionHeader
        title={L(lang, { en: "Tasks", fr: "Tâches", es: "Tareas", de: "Aufgaben", pt: "Tarefas" })}
        subtitle={L(lang, { en: "Submit tasks and view history", fr: "Soumettez des tâches et consultez l'historique", es: "Enviar tareas y ver historial", de: "Aufgaben senden und Verlauf anzeigen", pt: "Enviar tarefas e ver histórico" })}
        icon={ListTodo}
        lang={lang}
        actions={
          <Button size="sm" onClick={() => setShowInput(!showInput)} className="gap-1.5">
            <Plus className="w-3.5 h-3.5" />
            {L(lang, { en: "New Task", fr: "Nouvelle tâche", es: "Nueva Tarea", de: "Neue Aufgabe", pt: "Nova Tarefa" })}
          </Button>
        }
      />

      {/* Inline task input */}
      <AnimatePresence>
        {showInput && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden mb-4">
            <GlassCard className="p-4" glow>
              <Textarea
                placeholder={tr("dash.task_placeholder")}
                value={taskInput}
                onChange={e => setTaskInput(e.target.value)}
                rows={3}
                className="resize-none bg-background/50 border-border/50 focus:border-primary/50"
                onKeyDown={e => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submitTask(); }}
                autoFocus
              />
              <div className="flex justify-end gap-2 mt-3">
                <Button size="sm" variant="ghost" onClick={() => setShowInput(false)}>{L(lang, { en: "Cancel", fr: "Annuler", es: "Cancelar", de: "Abbrechen", pt: "Cancelar" })}</Button>
                <Button size="sm" onClick={submitTask} disabled={!taskInput.trim() || submitting} className="gap-1.5">
                  <Send className="w-3.5 h-3.5" />
                  {submitting ? L(lang, { en: "Sending...", fr: "Envoi...", es: "Enviando...", de: "Senden...", pt: "Enviando..." }) : tr("dash.send")}
                </Button>
              </div>
            </GlassCard>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Live ReAct trace */}
      {liveTrace.length > 0 && (
        <GlassCard className="p-4 mb-4 border-primary/30" glow>
          <h3 className="text-xs font-semibold uppercase tracking-wider text-primary mb-3 flex items-center gap-2">
            <motion.div className="w-2 h-2 rounded-full bg-primary" animate={{ scale: [1, 1.5, 1] }} transition={{ duration: 1, repeat: Infinity }} />
            {L(lang, { en: "Live Reasoning", fr: "Raisonnement en direct", es: "Razonamiento en vivo", de: "Live-Denken", pt: "Raciocínio ao vivo" })}
          </h3>
          <ThinkingStream traces={liveTrace} live={true} />
        </GlassCard>
      )}

      {/* Task history */}
      <div className="space-y-2">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
          {L(lang, { en: "History", fr: "Historique", es: "Historial", de: "Verlauf", pt: "Histórico" })} ({tasks.length})
        </h3>
        {tasks.length === 0 ? (
          <GlassCard className="p-8 text-center text-sm text-muted-foreground">
            <FileText className="w-10 h-10 mx-auto mb-3 opacity-30" />
            {tr("dash.no_tasks")}
          </GlassCard>
        ) : (
          tasks.map((task, i) => <TaskCard key={task.task_id || i} task={task as Record<string, unknown>} lang={lang} />)
        )}
      </div>
    </div>
  );
}

// ============================================================
// MONITOR SECTION
// ============================================================

export function MonitorSection({ lang }: { lang: Lang }) {
  const { logs } = useAgent();
  const [activeTab, setActiveTab] = useState<"logs" | "screens" | "audit">("logs");
  const [screenshots, setScreenshots] = useState<Array<{ name: string; size: number; modified: number }>>([]);
  const [auditEntries, setAuditEntries] = useState<Array<Record<string, unknown>>>([]);
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const load = async () => {
      const [shotsRes, auditRes] = await Promise.all([
        agentApi.screenshots(12).catch(() => ({ screenshots: [] })),
        agentApi.auditRecent({ limit: 50 }).catch(() => ({ entries: [] })),
      ]);
      setScreenshots(shotsRes.screenshots || []);
      setAuditEntries(auditRes.entries || []);
    };
    load();
    const i = setInterval(load, 5000);
    return () => clearInterval(i);
  }, []);

  useEffect(() => {
    if (activeTab === "logs" && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs, activeTab]);

  const tabs = [
    { id: "logs" as const, label: L(lang, { en: "Logs", fr: "Logs", es: "Registros", de: "Protokolle", pt: "Logs" }), icon: Terminal, count: logs.length },
    { id: "screens" as const, label: L(lang, { en: "Screenshots", fr: "Captures", es: "Capturas", de: "Screenshots", pt: "Capturas" }), icon: ImageIcon, count: screenshots.length },
    { id: "audit" as const, label: L(lang, { en: "Audit", fr: "Audit", es: "Auditoría", de: "Audit", pt: "Auditoria" }), icon: Shield, count: auditEntries.length },
  ];

  return (
    <div className="max-w-5xl mx-auto">
      <SectionHeader
        title={L(lang, { en: "Monitor", fr: "Moniteur", es: "Monitor", de: "Monitor", pt: "Monitor" })}
        subtitle={L(lang, { en: "Logs, screenshots, and audit trail", fr: "Logs, captures d'écran et audit", es: "Registros, capturas y auditoría", de: "Protokolle, Screenshots und Audit-Trail", pt: "Logs, capturas e auditoria" })}
        icon={Activity}
        lang={lang}
      />

      {/* Tabs */}
      <div className="flex gap-1 mb-4 border-b border-border/50">
        {tabs.map(tab => {
          const Icon = tab.icon;
          return (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)}
              className={cn("flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-all",
                activeTab === tab.id ? "border-primary text-primary" : "border-transparent text-muted-foreground hover:text-foreground")}>
              <Icon className="w-4 h-4" />
              {tab.label}
              {tab.count > 0 && <span className="text-[10px] font-mono bg-muted/60 px-1.5 py-0.5 rounded">{tab.count}</span>}
            </button>
          );
        })}
      </div>

      <AnimatePresence mode="wait">
        {activeTab === "logs" && (
          <motion.div key="logs" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <GlassCard className="p-3 font-mono text-xs max-h-[600px] overflow-y-auto">
              {logs.length === 0 ? (
                <div className="p-8 text-center text-muted-foreground">
                  <Terminal className="w-10 h-10 mx-auto mb-3 opacity-30" />
                  {L(lang, { en: "No logs. Connect the Python agent.", fr: "Aucun log. Connectez l'agent Python.", es: "Sin registros. Conecta el agente Python.", de: "Keine Protokolle. Verbinde den Python-Agenten.", pt: "Sem logs. Conecte o agente Python." })}
                </div>
              ) : (
                logs.map((log, i) => {
                  const colors: Record<string, string> = { INFO: "text-emerald-400", WARNING: "text-amber-400", ERROR: "text-red-400", DEBUG: "text-zinc-500" };
                  const time = log.timestamp ? new Date(log.timestamp).toLocaleTimeString(undefined, { hour12: false }) : "";
                  return (
                    <div key={i} className="flex gap-2 leading-relaxed hover:bg-accent/20 -mx-1 px-1 rounded">
                      <span className="text-zinc-600 flex-shrink-0">{time}</span>
                      <span className={cn("flex-shrink-0 w-12", colors[log.level] || "text-zinc-400")}>{log.level}</span>
                      <span className="text-zinc-500 flex-shrink-0 w-20 truncate">{log.logger}</span>
                      <span className="text-foreground/90 break-all">{log.message}</span>
                    </div>
                  );
                })
              )}
              <div ref={logsEndRef} />
            </GlassCard>
          </motion.div>
        )}

        {activeTab === "screens" && (
          <motion.div key="screens" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="flex justify-end mb-3">
              <Button size="sm" variant="outline" onClick={() => agentApi.captureScreenshot().then(() => setTimeout(() => location.reload(), 500))} className="gap-1.5">
                <Camera className="w-3.5 h-3.5" />
                {L(lang, { en: "Capture", fr: "Capturer", es: "Capturar", de: "Aufnehmen", pt: "Capturar" })}
              </Button>
            </div>
            {screenshots.length === 0 ? (
              <GlassCard className="p-8 text-center text-sm text-muted-foreground">
                <ImageIcon className="w-10 h-10 mx-auto mb-3 opacity-30" />
                {tr("dash.no_screenshots", lang)}
              </GlassCard>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {screenshots.map(shot => <ScreenshotTile key={shot.name} shot={shot} />)}
              </div>
            )}
          </motion.div>
        )}

        {activeTab === "audit" && (
          <motion.div key="audit" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <GlassCard className="p-4">
              <AuditLogPanel />
            </GlassCard>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ============================================================
// ANALYTICS SECTION
// ============================================================

export function AnalyticsSection({ lang }: { lang: Lang }) {
  return (
    <div className="max-w-5xl mx-auto">
      <SectionHeader
        title={L(lang, { en: "Analytics", fr: "Analytique", es: "Analítica", de: "Analytik", pt: "Análises" })}
        subtitle={L(lang, { en: "Costs, activity, and statistics", fr: "Coûts, activité et statistiques", es: "Costos, actividad y estadísticas", de: "Kosten, Aktivität und Statistiken", pt: "Custos, atividade e estatísticas" })}
        icon={BarChart3}
        lang={lang}
      />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <GlassCard className="p-4 md:col-span-2">
          <ActivityHeatmap />
        </GlassCard>
        <GlassCard className="p-4">
          <CostPanel />
        </GlassCard>
        <GlassCard className="p-4">
          <NotificationsPanel />
        </GlassCard>
      </div>
    </div>
  );
}

// ============================================================
// AUTOMATION SECTION
// ============================================================

export function AutomationSection({ lang }: { lang: Lang }) {
  return (
    <div className="max-w-5xl mx-auto">
      <SectionHeader
        title={L(lang, { en: "Automation", fr: "Automatisation", es: "Automatización", de: "Automatisierung", pt: "Automação" })}
        subtitle={L(lang, { en: "Scheduled tasks, watchers, webhooks, templates", fr: "Tâches planifiées, watchers, webhooks, templates", es: "Tareas programadas, watchers, webhooks, plantillas", de: "Geplante Aufgaben, Watcher, Webhooks, Vorlagen", pt: "Tarefas agendadas, watchers, webhooks, modelos" })}
        icon={Zap}
        lang={lang}
      />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <GlassCard className="p-4">
          <ScheduledTasksPanel />
        </GlassCard>
        <GlassCard className="p-4">
          <PromptTemplatesPanel onUse={() => {}} />
        </GlassCard>
        <GlassCard className="p-4">
          <BackupPanel />
        </GlassCard>
        <GlassCard className="p-4">
          <LLMProviderSwitcher />
        </GlassCard>
      </div>
    </div>
  );
}

// ============================================================
// KNOWLEDGE SECTION
// ============================================================

export function KnowledgeSection({ lang }: { lang: Lang }) {
  return (
    <div className="max-w-4xl mx-auto">
      <SectionHeader
        title={L(lang, { en: "Knowledge", fr: "Connaissance", es: "Conocimiento", de: "Wissen", pt: "Conhecimento" })}
        subtitle={L(lang, { en: "RAG knowledge base and vector memory", fr: "Base de connaissances RAG et mémoire vectorielle", es: "Base de conocimiento RAG y memoria vectorial", de: "RAG-Wissensbasis und Vektorspeicher", pt: "Base de conhecimento RAG e memória vetorial" })}
        icon={BookOpen}
        lang={lang}
      />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <GlassCard className="p-4">
          <KnowledgeBasePanel />
        </GlassCard>
        <GlassCard className="p-4">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3 flex items-center gap-2">
            <Brain className="w-3.5 h-3.5" />
            {L(lang, { en: "Vector Memory", fr: "Mémoire vectorielle", es: "Memoria vectorial", de: "Vektorspeicher", pt: "Memória vetorial" })}
          </h4>
          <p className="text-xs text-muted-foreground text-center py-4">
            {L(lang, { en: "Long-term semantic memory", fr: "Mémoire sémantique longue durée", es: "Memoria semántica a largo plazo", de: "Langzeit-Semantikspeicher", pt: "Memória semântica de longo prazo" })}
          </p>
        </GlassCard>
      </div>
    </div>
  );
}

// ============================================================
// SCREENSHOT TILE (shared)
// ============================================================

function ScreenshotTile({ shot }: { shot: { name: string; size: number; modified: number } }) {
  const [errored, setErrored] = useState(false);
  const src = useMemo(() => { try { return agentApi.screenshotUrl(shot.name); } catch { return null; } }, [shot.name]);
  const time = new Date(shot.modified * 1000).toLocaleTimeString(undefined, { hour: 2, minute: 2, second: 2 });

  return (
    <motion.div className="relative group rounded-lg overflow-hidden border border-border/50 bg-card/50" whileHover={{ scale: 1.03 }} transition={{ type: "spring", damping: 20 }}>
      {src && !errored ? (
        <img src={src} alt={shot.name} className="w-full aspect-video object-cover" loading="lazy" onError={() => setErrored(true)} />
      ) : (
        <div className="w-full aspect-video flex items-center justify-center bg-muted/30">
          <ImageIcon className="w-6 h-6 text-muted-foreground/50" />
        </div>
      )}
      <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-end p-2">
        <div>
          <p className="text-[9px] font-mono text-white/90 truncate">{shot.name}</p>
          <p className="text-[9px] text-white/60">{time}</p>
        </div>
      </div>
    </motion.div>
  );
}
