"use client";

import { useEffect, useState, useRef, useCallback, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Bot, Activity, Send, Play, Pause, RefreshCw,
  Terminal, Image as ImageIcon, Brain, Cpu, Clock, Zap,
  ChevronRight, Circle, CheckCircle2, XCircle,
  Camera, FileText, Mail, Calendar, Globe, Monitor, MonitorSmartphone,
  Lightbulb, Eye, EyeOff, Sparkles, Search, Code, Network,
  Mic, Plug, Radio, MessageSquare, Command, MessageCircle, Users,
  Plus, Trash2, Pin, Loader2, User, Copy, DollarSign, Shield,
  TrendingUp, BookOpen, Bell, Save, Edit, AlertCircle,
  ListTodo, BarChart3, Settings as SettingsIcon,
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

// ============================================================
// SETTINGS SECTION — full env var editor with fallback
// ============================================================

// Fallback env var schema (used when backend is offline)
const FALLBACK_VARS: Array<Record<string, unknown>> = [
  { key: "ZAI_API_KEY", label: "z.ai API Key", description: "Required — get yours at https://z.ai/", category: "llm", required: true, sensitive: true, placeholder: "your-z.ai-api-key", is_set: false, value: "" },
  { key: "TELEGRAM_BOT_TOKEN", label: "Telegram Bot Token", description: "From @BotFather on Telegram", category: "telegram", required: false, sensitive: true, placeholder: "123456:ABC-DEF...", is_set: false, value: "" },
  { key: "TELEGRAM_ALLOWED_USER_ID", label: "Telegram User ID", description: "Your Telegram user ID (from @userinfobot)", category: "telegram", required: false, sensitive: false, placeholder: "123456789", is_set: false, value: "" },
  { key: "EMAIL_USER", label: "Email Address", description: "Your email for IMAP/SMTP", category: "email", required: false, sensitive: false, placeholder: "you@gmail.com", is_set: false, value: "" },
  { key: "EMAIL_APP_PASSWORD", label: "Email App Password", description: "App password (NOT your real password). Gmail: myaccount.google.com/apppasswords", category: "email", required: false, sensitive: true, placeholder: "aaaa-bbbb-cccc-dddd", is_set: false, value: "" },
  { key: "OPENAI_API_KEY", label: "OpenAI API Key", description: "https://platform.openai.com/api-keys", category: "llm", required: false, sensitive: true, placeholder: "sk-...", is_set: false, value: "" },
  { key: "ANTHROPIC_API_KEY", label: "Anthropic API Key", description: "https://console.anthropic.com/", category: "llm", required: false, sensitive: true, placeholder: "sk-ant-...", is_set: false, value: "" },
  { key: "MISTRAL_API_KEY", label: "Mistral API Key", description: "https://console.mistral.ai/", category: "llm", required: false, sensitive: true, placeholder: "...", is_set: false, value: "" },
  { key: "NVIDIA_API_KEY", label: "NVIDIA NIM API Key", description: "https://build.nvidia.com/", category: "llm", required: false, sensitive: true, placeholder: "nvapi-...", is_set: false, value: "" },
  { key: "GROQ_API_KEY", label: "Groq API Key", description: "https://console.groq.com/ — ultra-fast inference", category: "llm", required: false, sensitive: true, placeholder: "gsk_...", is_set: false, value: "" },
  { key: "DEEPSEEK_API_KEY", label: "DeepSeek API Key", description: "https://platform.deepseek.com/", category: "llm", required: false, sensitive: true, placeholder: "sk-...", is_set: false, value: "" },
  { key: "TOGETHER_API_KEY", label: "Together AI API Key", description: "https://api.together.xyz/", category: "llm", required: false, sensitive: true, placeholder: "...", is_set: false, value: "" },
  { key: "FIREWORKS_API_KEY", label: "Fireworks AI API Key", description: "https://fireworks.ai/", category: "llm", required: false, sensitive: true, placeholder: "...", is_set: false, value: "" },
  { key: "ZDA_USE_SDK", label: "Use z.ai Coding Plan SDK", description: "Set to 'true' to use z-ai-web-dev-sdk via Node sidecar", category: "agent", required: false, sensitive: false, placeholder: "true", is_set: false, value: "" },
  { key: "SLACK_BOT_TOKEN", label: "Slack Bot Token", description: "https://api.slack.com/apps — for the Slack module", category: "integrations", required: false, sensitive: true, placeholder: "xoxb-...", is_set: false, value: "" },
];

export function SettingsSection({ lang }: { lang: Lang }) {
  const [variables, setVariables] = useState<Array<Record<string, unknown>>>(FALLBACK_VARS);
  const [editValues, setEditValues] = useState<Record<string, string>>({});
  const [showValues, setShowValues] = useState<Record<string, boolean>>({});
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [backendOnline, setBackendOnline] = useState(false);
  const [savedMsg, setSavedMsg] = useState("");

  const L2 = (texts: Record<string, string>) => texts[lang] || texts.en;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await agentApi.envList();
      if (r.variables && r.variables.length > 0) {
        setVariables(r.variables);
        setBackendOnline(true);
        const init: Record<string, string> = {};
        for (const v of r.variables) {
          const vv = v as Record<string, unknown>;
          init[String(vv.key)] = (vv.is_set && !vv.sensitive) ? String(vv.value) : "";
        }
        setEditValues(init);
      } else {
        setBackendOnline(false);
      }
    } catch {
      setBackendOnline(false);
      // Keep fallback vars
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    let cancelled = false;
    const doLoad = async () => { await load(); if (cancelled) return; };
    doLoad();
    return () => { cancelled = true; };
  }, [load]);

  const save = async () => {
    setSaving(true);
    const updates: Record<string, string> = {};
    for (const v of variables) {
      const vv = v as Record<string, unknown>;
      const key = String(vv.key);
      const editVal = editValues[key] || "";
      const isSet = Boolean(vv.is_set);
      const isSensitive = Boolean(vv.sensitive);
      if (isSensitive && isSet) {
        if (editVal.length > 0) updates[key] = editVal;
      } else {
        const currentVal = isSet ? String(vv.value) : "";
        if (editVal !== currentVal && editVal) updates[key] = editVal;
      }
    }
    if (Object.keys(updates).length === 0) {
      setSavedMsg(L2({ en: "No changes", fr: "Aucun changement", es: "Sin cambios", de: "Keine Änderungen", pt: "Sem alterações" }));
      setSaving(false);
      return;
    }
    if (!backendOnline) {
      setSavedMsg(L2({
        en: "⚠️ Backend offline — start the Python agent (python main.py) to save settings",
        fr: "⚠️ Backend hors-ligne — démarrez l'agent Python (python main.py) pour sauvegarder",
        es: "⚠️ Backend desconectado — inicia el agente Python (python main.py) para guardar",
        de: "⚠️ Backend offline — starten Sie den Python-Agenten (python main.py) zum Speichern",
        pt: "⚠️ Backend offline — inicie o agente Python (python main.py) para salvar",
      }));
      setSaving(false);
      return;
    }
    try {
      const result = await agentApi.envBatchSet(updates);
      if (result.success) {
        setSavedMsg(L2({ en: `✅ ${result.count} variables updated. Restart the agent.`, fr: `✅ ${result.count} variables mises à jour. Redémarrez l'agent.`, es: `✅ ${result.count} variables actualizadas. Reinicia el agente.`, de: `✅ ${result.count} Variablen aktualisiert. Agent neu starten.`, pt: `✅ ${result.count} variáveis atualizadas. Reinicie o agente.` }));
        setTimeout(load, 500);
      } else {
        setSavedMsg("❌ Error saving");
      }
    } catch { setSavedMsg("❌ Backend unreachable"); }
    setSaving(false);
  };

  const clearVar = async (key: string) => {
    if (!backendOnline) {
      setEditValues(prev => ({ ...prev, [key]: "" }));
      return;
    }
    try {
      await agentApi.envDelete(key);
      setEditValues(prev => ({ ...prev, [key]: "" }));
      setSavedMsg(L2({ en: `✅ ${key} cleared. Restart the agent.`, fr: `✅ ${key} supprimé. Redémarrez l'agent.`, es: `✅ ${key} eliminado. Reinicia el agente.`, de: `✅ ${key} gelöscht. Agent neu starten.`, pt: `✅ ${key} removido. Reinicie o agente.` }));
      setTimeout(load, 500);
    } catch {}
  };

  const testVar = async (key: string) => {
    if (!backendOnline) {
      setSavedMsg(L2({ en: "⚠️ Backend offline — cannot test keys", fr: "⚠️ Backend hors-ligne — impossible de tester les clés", es: "⚠️ Backend desconectado — no se pueden probar las claves", de: "⚠️ Backend offline — Schlüssel können nicht getestet werden", pt: "⚠️ Backend offline — não é possível testar as chaves" }));
      return;
    }
    try {
      const result = await agentApi.envTest(key);
      setSavedMsg(result.success
        ? `✅ ${String(result.provider)}: ${String(result.response || "OK")}`
        : `❌ ${String(result.error || "Failed")}`);
    } catch (e) { setSavedMsg(`❌ ${e}`); }
  };

  // Group by category
  const grouped: Record<string, Array<Record<string, unknown>>> = {};
  for (const v of variables) {
    const cat = String((v as Record<string, unknown>).category || "other");
    if (!grouped[cat]) grouped[cat] = [];
    grouped[cat].push(v);
  }
  const catLabels: Record<string, Record<string, string>> = {
    llm: { en: "LLM Providers", fr: "Fournisseurs LLM", es: "Proveedores LLM", de: "LLM-Anbieter", pt: "Provedores LLM" },
    telegram: { en: "Telegram", fr: "Telegram", es: "Telegram", de: "Telegram", pt: "Telegram" },
    email: { en: "Email", fr: "Email", es: "Correo", de: "E-Mail", pt: "Email" },
    agent: { en: "Agent Settings", fr: "Paramètres Agent", es: "Ajustes del Agente", de: "Agent-Einstellungen", pt: "Configurações do Agente" },
    integrations: { en: "Integrations", fr: "Intégrations", es: "Integraciones", de: "Integrationen", pt: "Integrações" },
  };
  const catOrder = ["llm", "telegram", "email", "agent", "integrations"];

  const dirty = variables.some(v => {
    const vv = v as Record<string, unknown>;
    const key = String(vv.key);
    const editVal = editValues[key] || "";
    if (vv.sensitive && vv.is_set) return editVal.length > 0;
    const currentVal = vv.is_set ? String(vv.value) : "";
    return editVal !== currentVal;
  });

  const setCount = variables.filter(v => Boolean((v as Record<string, unknown>).is_set)).length;

  return (
    <div className="max-w-3xl mx-auto">
      <SectionHeader
        title={L2({ en: "Settings", fr: "Paramètres", es: "Ajustes", de: "Einstellungen", pt: "Configurações" })}
        subtitle={L2({ en: "Configure API keys and tokens", fr: "Configurez les clés API et tokens", es: "Configura claves API y tokens", de: "API-Schlüssel und Tokens konfigurieren", pt: "Configure chaves de API e tokens" })}
        icon={SettingsIcon}
        lang={lang}
        actions={
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono text-muted-foreground">
              {setCount}/{variables.length} {L2({ en: "configured", fr: "configurées", es: "configuradas", de: "konfiguriert", pt: "configuradas" })}
            </span>
            <span className={cn("w-2 h-2 rounded-full", backendOnline ? "bg-emerald-500" : "bg-red-500")} title={backendOnline ? "Backend online" : "Backend offline"} />
          </div>
        }
      />

      {/* Backend status banner */}
      {!backendOnline && !loading && (
        <div className="mb-4 px-4 py-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-400 text-sm flex items-start gap-3">
          <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-medium">
              {L2({ en: "Backend offline", fr: "Backend hors-ligne", es: "Backend desconectado", de: "Backend offline", pt: "Backend offline" })}
            </p>
            <p className="text-xs text-amber-400/70 mt-0.5">
              {L2({
                en: "Start the Python agent to save and test API keys: python main.py",
                fr: "Démarrez l'agent Python pour sauvegarder et tester les clés API : python main.py",
                es: "Inicia el agente Python para guardar y probar las claves API: python main.py",
                de: "Starten Sie den Python-Agenten um API-Schlüssel zu speichern und testen: python main.py",
                pt: "Inicie o agente Python para salvar e testar chaves de API: python main.py",
              })}
            </p>
          </div>
        </div>
      )}

      {loading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 text-primary animate-spin" />
        </div>
      )}

      {savedMsg && (
        <div className={cn("mb-4 px-4 py-2 rounded-lg text-sm", savedMsg.startsWith("✅") ? "bg-emerald-500/10 text-emerald-400" : savedMsg.startsWith("⚠️") ? "bg-amber-500/10 text-amber-400" : "bg-red-500/10 text-red-400")}>
          {savedMsg}
        </div>
      )}

      {!loading && catOrder.filter(cat => grouped[cat]).map(cat => (
        <GlassCard key={cat} className="p-4 mb-4">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
            {catLabels[cat]?.[lang] || cat}
          </h3>
          <div className="space-y-3">
            {grouped[cat].map((v) => {
              const vv = v as Record<string, unknown>;
              const key = String(vv.key);
              const isSet = Boolean(vv.is_set);
              const isSensitive = Boolean(vv.sensitive);
              const isShown = showValues[key];
              const editVal = editValues[key] || "";
              return (
                <div key={key} className={cn("rounded-lg p-3 border transition-all", isSet ? "border-emerald-500/20 bg-emerald-500/5" : "border-border/50", vv.required && !isSet && "border-amber-500/40 bg-amber-500/5", editVal && "border-primary/30")}>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm font-medium">{String(vv.label)}</span>
                    {isSet && <span className="text-[9px] px-1 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-mono">✓ SET</span>}
                    {vv.required && !isSet && <span className="text-[9px] px-1 py-0.5 rounded bg-amber-500/20 text-amber-400 font-mono uppercase">{L2({ en: "Required", fr: "Requis", es: "Requerido", de: "Erforderlich", pt: "Obrigatório" })}</span>}
                    {isSensitive && <span className="text-[9px] text-muted-foreground">🔒</span>}
                  </div>
                  <p className="text-[10px] text-muted-foreground mb-2">{String(vv.description)}</p>
                  <p className="text-[9px] text-muted-foreground/60 font-mono mb-2">{key}</p>
                  <div className="flex gap-2">
                    <input
                      type={isSensitive && !isShown ? "password" : "text"}
                      placeholder={isSet && isSensitive ? "•••••••• (enter new to change)" : String(vv.placeholder || "")}
                      value={editVal}
                      onChange={e => setEditValues(prev => ({ ...prev, [key]: e.target.value }))}
                      className="flex-1 bg-background/50 rounded-md px-2.5 py-1.5 text-xs font-mono outline-none border border-border/50 focus:border-primary/50"
                    />
                    {isSensitive && (
                      <button onClick={() => setShowValues(prev => ({ ...prev, [key]: !prev[key] }))} className="px-2 py-1.5 rounded-md bg-muted/40 text-muted-foreground hover:text-foreground transition-colors" title={L2({ en: "Show/hide", fr: "Afficher/masquer", es: "Mostrar/ocultar", de: "Zeigen/verbergen", pt: "Mostrar/ocultar" })}>
                        {isShown ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                      </button>
                    )}
                    {isSet && key.includes("API_KEY") && (
                      <button onClick={() => testVar(key)} className="px-2 py-1.5 rounded-md text-[10px] bg-cyan-500/15 text-cyan-400 border border-cyan-500/30 hover:bg-cyan-500/25 transition-all flex items-center gap-1" title={L2({ en: "Test connection", fr: "Tester la connexion", es: "Probar conexión", de: "Verbindung testen", pt: "Testar conexão" })}>
                        <Zap className="w-3 h-3" />
                        {L2({ en: "Test", fr: "Test", es: "Probar", de: "Test", pt: "Testar" })}
                      </button>
                    )}
                    {isSet && (
                      <button onClick={() => clearVar(key)} className="px-2 py-1.5 rounded-md bg-muted/40 text-muted-foreground hover:bg-red-500/20 hover:text-red-400 transition-all" title={L2({ en: "Clear", fr: "Supprimer", es: "Eliminar", de: "Löschen", pt: "Remover" })}>
                        <Trash2 className="w-3 h-3" />
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </GlassCard>
      ))}

      {!loading && (
        <div className="flex justify-between items-center">
          <div className="text-[10px] text-muted-foreground">
            {backendOnline
              ? L2({ en: "Changes saved to .env file. Restart agent to apply.", fr: "Modifications sauvegardées dans .env. Redémarrez l'agent.", es: "Cambios guardados en .env. Reinicia el agente.", de: "Änderungen in .env gespeichert. Agent neu starten.", pt: "Alterações salvas em .env. Reinicie o agente." })
              : L2({ en: "Read-only mode (backend offline)", fr: "Mode lecture seule (backend hors-ligne)", es: "Modo solo lectura (backend desconectado)", de: "Schreibgeschützt (Backend offline)", pt: "Modo somente leitura (backend offline)" })
            }
          </div>
          <div className="flex gap-2">
            <Button size="sm" variant="ghost" onClick={load} disabled={loading}>
              <RefreshCw className={cn("w-3.5 h-3.5 mr-1.5", loading && "animate-spin")} />
              {L2({ en: "Refresh", fr: "Actualiser", es: "Actualizar", de: "Aktualisieren", pt: "Atualizar" })}
            </Button>
            <Button size="sm" onClick={save} disabled={saving || !dirty} className="gap-1.5">
              {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
              {L2({ en: "Save", fr: "Sauvegarder", es: "Guardar", de: "Speichern", pt: "Salvar" })}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================
// CHAT SECTION — works with AND without backend
// ============================================================

// Local conversation storage (fallback when backend is offline)
interface LocalConv {
  id: string;
  title: string;
  agent_id?: string;
  created_at: number;
  updated_at: number;
  message_count: number;
  messages: Array<{ id: string; role: string; content: string; datetime: string; metadata?: Record<string, unknown> }>;
}

export function ChatSection({ lang }: { lang: Lang }) {
  const [conversations, setConversations] = useState<LocalConv[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [agents, setAgents] = useState<Array<Record<string, unknown>>>([]);
  const [selectedAgent, setSelectedAgent] = useState<string | undefined>(undefined);
  const [backendOnline, setBackendOnline] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const L2 = (t: Record<string, string>) => t[lang] || t.en;

  const activeConv = conversations.find(c => c.id === activeConvId) || null;
  const messages = activeConv?.messages || [];

  // Load from backend or localStorage
  const loadConvs = useCallback(async () => {
    // Try backend first
    try {
      const r = await agentApi.chatList();
      if (r.conversations && r.conversations.length > 0) {
        setBackendOnline(true);
        // Convert backend format to local
        const localConvs: LocalConv[] = r.conversations.map((c: Record<string, unknown>) => ({
          id: String(c.id),
          title: String(c.title || "Untitled"),
          agent_id: c.agent_id ? String(c.agent_id) : undefined,
          created_at: Number(c.created_at || 0),
          updated_at: Number(c.updated_at || 0),
          message_count: Number(c.message_count || 0),
          messages: [], // lazy load on open
        }));
        setConversations(localConvs);
        return;
      }
    } catch {}
    // Backend offline — load from localStorage
    setBackendOnline(false);
    try {
      const stored = localStorage.getItem("zda-chat-conversations");
      if (stored) {
        setConversations(JSON.parse(stored));
      }
    } catch {}
  }, []);

  const loadAgents = useCallback(async () => {
    try {
      const r = await agentApi.agentsList();
      setAgents(r.agents || []);
    } catch {}
  }, []);

  // Save to localStorage whenever conversations change
  useEffect(() => {
    try {
      localStorage.setItem("zda-chat-conversations", JSON.stringify(conversations));
    } catch {}
  }, [conversations]);

  useEffect(() => {
    let cancelled = false;
    const doLoad = async () => {
      await Promise.all([loadConvs(), loadAgents()]);
      if (cancelled) return;
    };
    doLoad();
    return () => { cancelled = true; };
  }, [loadConvs, loadAgents]);

  useEffect(() => {
    if (messagesEndRef.current) messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const newConv = () => {
    const id = `local_${Date.now()}`;
    const conv: LocalConv = {
      id,
      title: L2({ en: "New chat", fr: "Nouvelle conversation", es: "Nueva conversación", de: "Neue Konversation", pt: "Nova conversa" }),
      agent_id: selectedAgent,
      created_at: Date.now(),
      updated_at: Date.now(),
      message_count: 0,
      messages: [],
    };
    setConversations(prev => [conv, ...prev]);
    setActiveConvId(id);
    setInput("");

    // Also try to create on backend (won't break if offline)
    if (backendOnline) {
      agentApi.chatCreate({ agent_id: selectedAgent }).catch(() => {});
    }
  };

  const openConv = async (convId: string) => {
    const conv = conversations.find(c => c.id === convId);
    if (!conv) return;
    setActiveConvId(convId);

    // If messages not loaded yet and backend is online, fetch them
    if (conv.messages.length === 0 && conv.message_count > 0 && backendOnline) {
      try {
        const r = await agentApi.chatGet(convId);
        const fetched = (r as Record<string, unknown>).messages as Array<Record<string, unknown>> || [];
        setConversations(prev => prev.map(c =>
          c.id === convId ? { ...c, messages: fetched.map(m => ({
            id: String(m.id || ""), role: String(m.role || ""), content: String(m.content || ""),
            datetime: String(m.datetime || ""), metadata: m.metadata as Record<string, unknown>,
          })) } : c
        ));
      } catch {}
    }
  };

  const deleteConv = (convId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setConversations(prev => prev.filter(c => c.id !== convId));
    if (activeConvId === convId) { setActiveConvId(null); }
    if (backendOnline) {
      agentApi.chatDelete(convId).catch(() => {});
    }
  };

  const send = async () => {
    if (!input.trim() || !activeConvId) return;
    const text = input;
    setInput("");
    setSending(true);

    const userMsg = { id: `u_${Date.now()}`, role: "user", content: text, datetime: new Date().toISOString() };

    // Add user message locally immediately
    setConversations(prev => prev.map(c =>
      c.id === activeConvId
        ? {
            ...c,
            messages: [...c.messages, userMsg],
            message_count: c.message_count + 1,
            updated_at: Date.now(),
            title: c.messages.length === 0 ? text.slice(0, 60) : c.title,
          }
        : c
    ));

    // Always try to send via backend — don't check backendOnline flag
    try {
      const r = await agentApi.chatSend(activeConvId, text);
      const assistantMsg = {
        id: `a_${Date.now()}`,
        role: "assistant",
        content: r.response || r.error || "Error",
        datetime: new Date().toISOString(),
        metadata: r.metadata as Record<string, unknown>,
      };
      setConversations(prev => prev.map(c =>
        c.id === activeConvId
          ? { ...c, messages: [...c.messages, assistantMsg], message_count: c.message_count + 1, updated_at: Date.now() }
          : c
      ));
      setBackendOnline(true);
    } catch (e) {
        const errorMsg = {
          id: `e_${Date.now()}`,
          role: "assistant",
          content: L2({ en: "❌ Could not reach the agent. Is the Python backend running?", fr: "❌ Impossible de joindre l'agent. Le backend Python est-il démarré ?", es: "❌ No se pudo contactar al agente. ¿El backend Python está funcionando?", de: "❌ Agent nicht erreichbar. Läuft das Python-Backend?", pt: "❌ Não foi possível contactar o agente. O backend Python está rodando?" }),
          datetime: new Date().toISOString(),
        };
        setConversations(prev => prev.map(c =>
          c.id === activeConvId ? { ...c, messages: [...c.messages, errorMsg] } : c
        ));
      setBackendOnline(false);
    }
    setSending(false);
  };

  return (
    <div className="max-w-5xl mx-auto">
      <SectionHeader
        title={L2({ en: "Chat", fr: "Chat", es: "Chat", de: "Chat", pt: "Chat" })}
        subtitle={L2({ en: "Conversations with custom agents", fr: "Conversations avec agents personnalisés", es: "Conversaciones con agentes personalizados", de: "Konversationen mit benutzerdefinierten Agenten", pt: "Conversas com agentes personalizados" })}
        icon={MessageCircle}
        lang={lang}
        actions={
          <div className="flex items-center gap-2">
            <span className={cn("w-2 h-2 rounded-full", backendOnline ? "bg-emerald-500" : "bg-red-500")} title={backendOnline ? "Backend online" : "Backend offline"} />
            <select
              value={selectedAgent || ""}
              onChange={e => setSelectedAgent(e.target.value || undefined)}
              className="bg-background/50 rounded-md px-2 py-1.5 text-xs outline-none border border-border/50"
            >
              <option value="">{L2({ en: "Default agent", fr: "Agent par défaut", es: "Agente por defecto", de: "Standard-Agent", pt: "Agente padrão" })}</option>
              {agents.map(a => <option key={String(a.id)} value={String(a.id)}>{String(a.emoji)} {String(a.name)}</option>)}
            </select>
          </div>
        }
      />

      <div className="flex gap-4" style={{ height: "calc(100vh - 220px)" }}>
        {/* Conversation list */}
        <div className="w-64 flex-shrink-0 flex flex-col">
          <button onClick={newConv} className="w-full flex items-center justify-center gap-2 px-3 py-2 mb-2 rounded-lg bg-primary/15 text-primary border border-primary/30 hover:bg-primary/25 transition-all text-sm font-medium">
            <Plus className="w-4 h-4" />
            {L2({ en: "New chat", fr: "Nouveau chat", es: "Nuevo chat", de: "Neuer Chat", pt: "Novo chat" })}
          </button>
          <div className="flex-1 overflow-y-auto space-y-0.5">
            {conversations.length === 0 ? (
              <p className="text-xs text-muted-foreground text-center py-4">{L2({ en: "No conversations", fr: "Aucune conversation", es: "Sin conversaciones", de: "Keine Konversationen", pt: "Sem conversas" })}</p>
            ) : (
              conversations.map(conv => (
                <div key={conv.id} onClick={() => openConv(conv.id)} className={cn("group flex items-center gap-2 px-2 py-2 rounded-lg cursor-pointer transition-all", activeConvId === conv.id ? "bg-primary/15 border border-primary/30" : "hover:bg-accent/20")}>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs truncate">{conv.title}</p>
                    <p className="text-[9px] text-muted-foreground">{conv.message_count} {L2({ en: "messages", fr: "messages", es: "mensajes", de: "Nachrichten", pt: "mensagens" })}</p>
                  </div>
                  <button onClick={(e) => deleteConv(conv.id, e)} className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-red-400 transition-all">
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 flex flex-col glass rounded-xl overflow-hidden">
          {activeConv ? (
            <>
              <div className="flex-1 overflow-y-auto p-4 space-y-3">
                {messages.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
                    <Bot className="w-12 h-12 mb-3 opacity-30" />
                    <p className="text-sm">{L2({ en: "Start the conversation", fr: "Démarrez la conversation", es: "Inicia la conversación", de: "Konversation starten", pt: "Inicie a conversa" })}</p>
                  </div>
                ) : (
                  messages.map((msg, i) => (
                    <motion.div key={msg.id || i} className={cn("flex gap-3", msg.role === "user" ? "flex-row-reverse" : "flex-row")} initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }}>
                      <div className={cn("w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0", msg.role === "user" ? "bg-cyan-500/15 border border-cyan-500/30" : "bg-primary/15 border border-primary/30")}>
                        {msg.role === "user" ? <User className="w-3.5 h-3.5 text-cyan-400" /> : <Bot className="w-3.5 h-3.5 text-primary" />}
                      </div>
                      <div className={cn("max-w-[75%] rounded-xl px-3 py-2", msg.role === "user" ? "bg-cyan-500/10 border border-cyan-500/20" : "glass")}>
                        <p className="text-sm whitespace-pre-wrap break-words">{msg.content}</p>
                      </div>
                    </motion.div>
                  ))
                )}
                {sending && (
                  <div className="flex gap-3">
                    <div className="w-7 h-7 rounded-lg bg-primary/15 border border-primary/30 flex items-center justify-center">
                      <Loader2 className="w-3.5 h-3.5 text-primary animate-spin" />
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>
              <div className="p-3 border-t border-border/50">
                <div className="flex gap-2 items-end">
                  <textarea
                    placeholder={L2({ en: "Type your message...", fr: "Tapez votre message...", es: "Escribe tu mensaje...", de: "Nachricht eingeben...", pt: "Digite sua mensagem..." })}
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
                    rows={1}
                    className="flex-1 glass rounded-xl px-3 py-2 text-sm outline-none resize-none focus:border-primary/50"
                  />
                  <button onClick={send} disabled={!input.trim() || sending} className="w-9 h-9 rounded-xl bg-primary/20 text-primary border border-primary/30 hover:bg-primary/30 disabled:opacity-30 flex items-center justify-center flex-shrink-0">
                    <Send className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground">
              <Bot className="w-16 h-16 mb-4 opacity-20" />
              <p className="text-sm">{L2({ en: "Select or create a conversation", fr: "Sélectionnez ou créez une conversation", es: "Selecciona o crea una conversación", de: "Konversation auswählen oder erstellen", pt: "Selecione ou crie uma conversa" })}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ============================================================
// AGENTS SECTION (inline, not modal)
// ============================================================

const EMOJI_OPTIONS = ["🤖", "📧", "🔍", "📚", "📁", "⚙️", "🌐", "💻", "🎨", "📊", "🔬", "🎬", "🎮", "💡", "🚀", "⚡"];
const COLOR_OPTIONS = ["#10B981", "#06B6D4", "#8B5CF6", "#EC4899", "#F59E0B", "#3B82F6", "#EF4444", "#14B8A6", "#F97316", "#A855F7", "#22C55E", "#6366F1"];

const BUILTIN_AGENTS_FALLBACK = [
  { emoji: "🤖", name: "General Assistant", description: "General-purpose agent with access to all actions", color: "#10B981" },
  { emoji: "📧", name: "Email Assistant", description: "Specialized in email management — reads, sorts, drafts replies", color: "#F59E0B" },
  { emoji: "🔍", name: "Code Reviewer", description: "Reviews code for bugs, security issues, and improvements", color: "#06B6D4" },
  { emoji: "📚", name: "Research Bot", description: "Deep research using web search and knowledge base", color: "#8B5CF6" },
  { emoji: "📁", name: "File Organizer", description: "Organizes and cleans up files and folders", color: "#22C55E" },
  { emoji: "⚙️", name: "System Admin", description: "Manages system processes, apps, and settings", color: "#EF4444" },
];

const ACTION_PREFIXES = [
  { id: "screen.", label: "Screen" },
  { id: "files.", label: "Files" },
  { id: "email.", label: "Email" },
  { id: "calendar.", label: "Calendar" },
  { id: "browser.", label: "Browser" },
  { id: "system.", label: "System" },
  { id: "windows.", label: "Windows" },
  { id: "code.", label: "Code" },
  { id: "web.", label: "Web" },
  { id: "voice.", label: "Voice" },
  { id: "vision.", label: "Vision" },
  { id: "kb.", label: "Knowledge" },
  { id: "plugin.", label: "Plugin" },
  { id: "mcp.", label: "MCP" },
  { id: "slack.", label: "Slack" },
];

export function AgentsSection({ lang }: { lang: Lang }) {
  const [agents, setAgents] = useState<Array<Record<string, unknown>>>([]);
  const [showEditor, setShowEditor] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState({
    name: "", description: "", system_prompt: "",
    provider: "zai", model: "", temperature: 0.3, max_tokens: 4096,
    allowed_actions: [] as string[], blocked_actions: [] as string[],
    memory_mode: "conversation", autonomy_mode: "full",
    color: "#10B981", emoji: "🤖",
  });

  const L2 = (t: Record<string, string>) => t[lang] || t.en;

  const load = useCallback(async () => {
    try {
      const r = await agentApi.agentsList();
      setAgents(r.agents || []);
    } catch {}
  }, []);

  useEffect(() => {
    let cancelled = false;
    const doLoad = async () => { await load(); if (cancelled) return; };
    doLoad();
    return () => { cancelled = true; };
  }, [load]);

  const startNew = () => {
    setForm({ name: "", description: "", system_prompt: "", provider: "zai", model: "", temperature: 0.3, max_tokens: 4096, allowed_actions: [], blocked_actions: [], memory_mode: "conversation", autonomy_mode: "full", color: COLOR_OPTIONS[Math.floor(Math.random() * COLOR_OPTIONS.length)], emoji: "🤖" });
    setEditingId(null);
    setShowEditor(true);
  };

  const startEdit = (agent: Record<string, unknown>) => {
    setForm({
      name: String(agent.name || ""), description: String(agent.description || ""),
      system_prompt: String(agent.system_prompt || ""), provider: String(agent.provider || "zai"),
      model: String(agent.model || ""), temperature: Number(agent.temperature || 0.3),
      max_tokens: Number(agent.max_tokens || 4096),
      allowed_actions: (agent.allowed_actions as string[]) || [],
      blocked_actions: (agent.blocked_actions as string[]) || [],
      memory_mode: String(agent.memory_mode || "conversation"),
      autonomy_mode: String(agent.autonomy_mode || "full"),
      color: String(agent.color || "#10B981"), emoji: String(agent.emoji || "🤖"),
    });
    setEditingId(String(agent.id));
    setShowEditor(true);
  };

  const save = async () => {
    if (!form.name.trim()) return;
    try {
      if (editingId) await agentApi.agentsUpdate(editingId, form);
      else await agentApi.agentsCreate(form);
      setShowEditor(false);
      load();
    } catch {}
  };

  const remove = async (id: string) => {
    try { await agentApi.agentsDelete(id); load(); } catch {}
  };

  const toggleAction = (list: "allowed_actions" | "blocked_actions", prefix: string) => {
    setForm(prev => {
      const current = prev[list];
      return { ...prev, [list]: current.includes(prefix) ? current.filter(a => a !== prefix) : [...current, prefix] };
    });
  };

  return (
    <div className="max-w-3xl mx-auto">
      <SectionHeader
        title={L2({ en: "Custom Agents", fr: "Agents personnalisés", es: "Agentes personalizados", de: "Benutzerdefinierte Agenten", pt: "Agentes personalizados" })}
        subtitle={L2({ en: "Create and manage specialized agents", fr: "Créer et gérer des agents spécialisés", es: "Crear y gestionar agentes especializados", de: "Spezialisierte Agenten erstellen und verwalten", pt: "Criar e gerenciar agentes especializados" })}
        icon={Users}
        lang={lang}
        actions={
          !showEditor && (
            <Button size="sm" onClick={startNew} className="gap-1.5">
              <Plus className="w-3.5 h-3.5" />
              {L2({ en: "New", fr: "Nouveau", es: "Nuevo", de: "Neu", pt: "Novo" })}
            </Button>
          )
        }
      />

      {!showEditor ? (
        <div className="space-y-2">
          {agents.length === 0 ? (
            <>
              <div className="mb-3 px-4 py-2 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs flex items-center gap-2">
                <AlertCircle className="w-3.5 h-3.5" />
                {L2({ en: "Backend offline — showing built-in templates. Start the agent to create custom ones.", fr: "Backend hors-ligne — modèles intégrés affichés. Démarrez l'agent pour en créer.", es: "Backend desconectado — mostrando plantillas. Inicia el agente para crear personalizadas.", de: "Backend offline — integrierte Vorlagen werden angezeigt.", pt: "Backend offline — mostrando modelos integrados." })}
              </div>
              {BUILTIN_AGENTS_FALLBACK.map((agent, i) => (
                <motion.div key={i} initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.03 }}>
                  <GlassCard className="p-4 flex items-center gap-3 opacity-80">
                    <div className="w-12 h-12 rounded-xl flex items-center justify-center text-xl flex-shrink-0" style={{ background: `${agent.color}20`, border: `1px solid ${agent.color}40` }}>
                      {agent.emoji}
                    </div>
                    <div className="flex-1 min-w-0">
                      <span className="text-sm font-medium">{agent.name}</span>
                      <p className="text-xs text-muted-foreground truncate">{agent.description}</p>
                    </div>
                    <span className="text-[9px] px-1 py-0.5 rounded bg-muted/40 font-mono uppercase">{L2({ en: "Template", fr: "Modèle", es: "Plantilla", de: "Vorlage", pt: "Modelo" })}</span>
                  </GlassCard>
                </motion.div>
              ))}
            </>
          ) : (
            agents.map((agent, i) => {
              const isTemplate = String(agent.id).startsWith("template_");
              return (
                <motion.div key={String(agent.id)} initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.03 }}>
                  <GlassCard className="p-4 flex items-center gap-3">
                    <div className="w-12 h-12 rounded-xl flex items-center justify-center text-xl flex-shrink-0" style={{ background: `${String(agent.color)}20`, border: `1px solid ${String(agent.color)}40` }}>
                      {String(agent.emoji)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium truncate">{String(agent.name)}</span>
                        {isTemplate && <span className="text-[9px] px-1 py-0.5 rounded bg-muted/40 font-mono uppercase">{L2({ en: "Template", fr: "Modèle", es: "Plantilla", de: "Vorlage", pt: "Modelo" })}</span>}
                      </div>
                      <p className="text-xs text-muted-foreground truncate">{String(agent.description || "")}</p>
                      <div className="flex gap-2 mt-1 text-[9px] text-muted-foreground font-mono">
                        <span className="text-emerald-400">{(agent.allowed_actions as string[])?.length || 0} allowed</span>
                        <span className="text-red-400">{(agent.blocked_actions as string[])?.length || 0} blocked</span>
                        <span>{String(agent.autonomy_mode)}</span>
                      </div>
                    </div>
                    <div className="flex gap-1 flex-shrink-0">
                      <button onClick={() => startEdit(agent)} className="w-7 h-7 rounded-lg hover:bg-accent/30 flex items-center justify-center text-muted-foreground hover:text-primary">
                        <Edit className="w-3.5 h-3.5" />
                      </button>
                      {!isTemplate && (
                        <button onClick={() => remove(String(agent.id))} className="w-7 h-7 rounded-lg hover:bg-red-500/20 flex items-center justify-center text-muted-foreground hover:text-red-400">
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  </GlassCard>
                </motion.div>
              );
            })
          )}
        </div>
      ) : (
        <GlassCard className="p-5 space-y-4">
          {/* Emoji + Color */}
          <div className="flex gap-4">
            <div className="flex-1">
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2 block">{L2({ en: "Emoji", fr: "Emoji", es: "Emoji", de: "Emoji", pt: "Emoji" })}</label>
              <div className="flex flex-wrap gap-1.5">
                {EMOJI_OPTIONS.map(e => (
                  <button key={e} onClick={() => setForm(p => ({ ...p, emoji: e }))} className={cn("w-8 h-8 rounded-lg flex items-center justify-center text-lg transition-all", form.emoji === e ? "bg-primary/20 border border-primary/40" : "bg-muted/30 hover:bg-muted/50")}>{e}</button>
                ))}
              </div>
            </div>
            <div className="flex-1">
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2 block">{L2({ en: "Color", fr: "Couleur", es: "Color", de: "Farbe", pt: "Cor" })}</label>
              <div className="flex flex-wrap gap-1.5">
                {COLOR_OPTIONS.map(c => (
                  <button key={c} onClick={() => setForm(p => ({ ...p, color: c }))} className={cn("w-8 h-8 rounded-lg transition-all", form.color === c ? "ring-2 ring-offset-2 ring-offset-background" : "")} style={{ background: c, boxShadow: form.color === c ? `0 0 12px ${c}` : "none" }} />
                ))}
              </div>
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5 block">{L2({ en: "Name", fr: "Nom", es: "Nombre", de: "Name", pt: "Nome" })} *</label>
            <input value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))} placeholder="Email Assistant" className="w-full bg-background/50 rounded-md px-3 py-2 text-sm outline-none border border-border/50 focus:border-primary/50" />
          </div>

          <div>
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5 block">{L2({ en: "Description", fr: "Description", es: "Descripción", de: "Beschreibung", pt: "Descrição" })}</label>
            <input value={form.description} onChange={e => setForm(p => ({ ...p, description: e.target.value }))} placeholder={L2({ en: "Manages my emails", fr: "Gère mes emails", es: "Gestiona mis correos", de: "Verwaltet meine E-Mails", pt: "Gerencia meus emails" })} className="w-full bg-background/50 rounded-md px-3 py-2 text-sm outline-none border border-border/50 focus:border-primary/50" />
          </div>

          <div>
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5 block">{L2({ en: "System Prompt (persona)", fr: "Prompt système (persona)", es: "Prompt del sistema (persona)", de: "System-Prompt (Persona)", pt: "Prompt do sistema (persona)" })}</label>
            <textarea value={form.system_prompt} onChange={e => setForm(p => ({ ...p, system_prompt: e.target.value }))} placeholder="You are a helpful email assistant..." rows={3} className="w-full bg-background/50 rounded-md px-3 py-2 text-sm outline-none border border-border/50 focus:border-primary/50 resize-none" />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5 block">{L2({ en: "LLM Provider", fr: "Fournisseur LLM", es: "Proveedor LLM", de: "LLM-Anbieter", pt: "Provedor LLM" })}</label>
              <select value={form.provider} onChange={e => setForm(p => ({ ...p, provider: e.target.value }))} className="w-full bg-background/50 rounded-md px-3 py-2 text-sm outline-none border border-border/50">
                <option value="zai">z.ai (GLM)</option>
                <option value="openai">OpenAI (GPT)</option>
                <option value="anthropic">Anthropic (Claude)</option>
                <option value="mistral">Mistral</option>
                <option value="nvidia">NVIDIA NIM</option>
                <option value="groq">Groq</option>
                <option value="deepseek">DeepSeek</option>
                <option value="ollama">Ollama (local)</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5 block">{L2({ en: "Model (empty = default)", fr: "Modèle (vide = défaut)", es: "Modelo (vacío = default)", de: "Modell (leer = Standard)", pt: "Modelo (vazio = padrão)" })}</label>
              <input value={form.model} onChange={e => setForm(p => ({ ...p, model: e.target.value }))} placeholder="glm-4.6" className="w-full bg-background/50 rounded-md px-3 py-2 text-sm font-mono outline-none border border-border/50 focus:border-primary/50" />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5 block">{L2({ en: "Temperature", fr: "Température", es: "Temperatura", de: "Temperatur", pt: "Temperatura" })}: {form.temperature}</label>
              <input type="range" min="0" max="1" step="0.1" value={form.temperature} onChange={e => setForm(p => ({ ...p, temperature: Number(e.target.value) }))} className="w-full accent-primary" />
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5 block">{L2({ en: "Max tokens", fr: "Max tokens", es: "Máx tokens", de: "Max Tokens", pt: "Máx tokens" })}</label>
              <input type="number" value={form.max_tokens} onChange={e => setForm(p => ({ ...p, max_tokens: Number(e.target.value) }))} className="w-full bg-background/50 rounded-md px-3 py-2 text-sm font-mono outline-none border border-border/50 focus:border-primary/50" />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5 block">{L2({ en: "Memory", fr: "Mémoire", es: "Memoria", de: "Speicher", pt: "Memória" })}</label>
              <select value={form.memory_mode} onChange={e => setForm(p => ({ ...p, memory_mode: e.target.value }))} className="w-full bg-background/50 rounded-md px-3 py-2 text-sm outline-none border border-border/50">
                <option value="none">{L2({ en: "None", fr: "Aucune", es: "Ninguna", de: "Keine", pt: "Nenhuma" })}</option>
                <option value="conversation">{L2({ en: "Conversation", fr: "Conversation", es: "Conversación", de: "Konversation", pt: "Conversa" })}</option>
                <option value="persistent">{L2({ en: "Persistent", fr: "Persistante", es: "Persistente", de: "Beständig", pt: "Persistente" })}</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5 block">{L2({ en: "Autonomy", fr: "Autonomie", es: "Autonomía", de: "Autonomie", pt: "Autonomia" })}</label>
              <select value={form.autonomy_mode} onChange={e => setForm(p => ({ ...p, autonomy_mode: e.target.value }))} className="w-full bg-background/50 rounded-md px-3 py-2 text-sm outline-none border border-border/50">
                <option value="full">{L2({ en: "Full control", fr: "Plein contrôle", es: "Control total", de: "Vollkontrolle", pt: "Controle total" })}</option>
                <option value="confirmation">{L2({ en: "Confirmation required", fr: "Confirmation requise", es: "Confirmación requerida", de: "Bestätigung erforderlich", pt: "Confirmação necessária" })}</option>
                <option value="readonly">{L2({ en: "Read only", fr: "Lecture seule", es: "Solo lectura", de: "Nur Lesen", pt: "Somente leitura" })}</option>
              </select>
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold uppercase tracking-wider text-emerald-400 mb-2 block">{L2({ en: "Allowed Actions", fr: "Actions autorisées", es: "Acciones permitidas", de: "Erlaubte Aktionen", pt: "Ações permitidas" })} ({form.allowed_actions.length})</label>
            <div className="flex flex-wrap gap-1.5">
              {ACTION_PREFIXES.map(a => (
                <button key={a.id} onClick={() => toggleAction("allowed_actions", a.id)} className={cn("px-2 py-1 rounded-md text-[10px] border transition-all", form.allowed_actions.includes(a.id) ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/40" : "bg-muted/30 text-muted-foreground border-border/50 hover:bg-muted/50")}>{a.label}</button>
              ))}
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold uppercase tracking-wider text-red-400 mb-2 block">{L2({ en: "Blocked Actions", fr: "Actions bloquées", es: "Acciones bloqueadas", de: "Blockierte Aktionen", pt: "Ações bloqueadas" })} ({form.blocked_actions.length})</label>
            <div className="flex flex-wrap gap-1.5">
              {ACTION_PREFIXES.map(a => (
                <button key={a.id} onClick={() => toggleAction("blocked_actions", a.id)} className={cn("px-2 py-1 rounded-md text-[10px] border transition-all", form.blocked_actions.includes(a.id) ? "bg-red-500/20 text-red-400 border-red-500/40" : "bg-muted/30 text-muted-foreground border-border/50 hover:bg-muted/50")}>{a.label}</button>
              ))}
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button size="sm" variant="ghost" onClick={() => setShowEditor(false)}>{L2({ en: "Cancel", fr: "Annuler", es: "Cancelar", de: "Abbrechen", pt: "Cancelar" })}</Button>
            <Button size="sm" onClick={save} disabled={!form.name.trim()} className="gap-1.5">
              <Save className="w-3.5 h-3.5" />
              {editingId ? L2({ en: "Update", fr: "Mettre à jour", es: "Actualizar", de: "Aktualisieren", pt: "Atualizar" }) : L2({ en: "Create", fr: "Créer", es: "Crear", de: "Erstellen", pt: "Criar" })}
            </Button>
          </div>
        </GlassCard>
      )}
    </div>
  );
}
