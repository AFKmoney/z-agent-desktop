"use client";

import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import {
  Bot, Activity, Send, Play, Pause, RefreshCw,
  Terminal, Image as ImageIcon, Brain, Cpu, Clock, Zap,
  ChevronRight, Circle, CheckCircle2, XCircle,
  Camera, FileText, Mail, Calendar, Globe, Monitor, MonitorSmartphone,
  Lightbulb, Eye, Languages, Sparkles, Search, Code, Network,
  Mic, Plug, Radio, MessageSquare,
} from "lucide-react";
import { useAgent } from "@/hooks/use-agent";
import { agentApi, type TaskRecord } from "@/lib/agent-api";
import { t, detectBrowserLang, setStoredLang, stateLabel, type Lang } from "@/lib/i18n";
import { LanguageSelector } from "@/components/LanguageSelector";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";

const STATE_COLORS: Record<string, string> = {
  idle: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  planning: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  executing: "bg-cyan-500/15 text-cyan-400 border-cyan-500/30",
  paused: "bg-zinc-500/15 text-zinc-400 border-zinc-500/30",
  error: "bg-red-500/15 text-red-400 border-red-500/30",
  stopped: "bg-red-500/15 text-red-400 border-red-500/30",
};

const MODULE_ICONS: Record<string, typeof FileText> = {
  screen: Monitor,
  files: FileText,
  email: Mail,
  calendar: Calendar,
  browser: Globe,
  system: Cpu,
  windows: MonitorSmartphone,
  slack: Send,
};

export default function Dashboard() {
  // Detect language on first render (no flashing)
  const [lang, setLang] = useState<Lang>("en");
  useEffect(() => {
    setLang(detectBrowserLang());
  }, []);

  const { status, logs, progress, connected, refresh } = useAgent();
  const { toast } = useToast();
  const [taskInput, setTaskInput] = useState("");
  const [tasks, setTasks] = useState<TaskRecord[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [screenshots, setScreenshots] = useState<Array<{ name: string; size: number; modified: number }>>([]);
  const [activeTab, setActiveTab] = useState("tasks");
  const logsEndRef = useRef<HTMLDivElement>(null);

  const tr = useCallback((key: string, vars?: Record<string, string | number>) => t(key, lang, vars), [lang]);

  const QUICK_TASKS = useMemo(() => [
    { icon: FileText, label: tr("dash.quick_sort_downloads"), prompt: lang === "fr" ? "Organise mon dossier Téléchargements par type de fichier" : "Organize my Downloads folder by file type" },
    { icon: Mail, label: tr("dash.quick_read_emails"), prompt: lang === "fr" ? "Lis mes 5 derniers emails non lus et fais-moi un résumé" : "Read my 5 latest unread emails and summarize them" },
    { icon: Calendar, label: tr("dash.quick_events"), prompt: lang === "fr" ? "Liste mes 10 prochains événements de calendrier" : "List my 10 upcoming calendar events" },
    { icon: Monitor, label: tr("dash.quick_describe_screen"), prompt: lang === "fr" ? "Décris ce qu'il y a actuellement sur mon écran" : "Describe what's currently on my screen" },
    { icon: Cpu, label: tr("dash.quick_system_info"), prompt: lang === "fr" ? "Donne-moi les informations système (CPU, RAM, disque)" : "Give me system info (CPU, RAM, disk)" },
    { icon: Camera, label: tr("dash.quick_screenshot"), prompt: lang === "fr" ? "Prends une capture d'écran et analyse-la" : "Take a screenshot and analyze it" },
  ], [tr, lang]);

  // Load tasks + screenshots periodically
  const loadData = useCallback(async () => {
    try {
      const [tasksRes, shotsRes] = await Promise.all([
        agentApi.recentTasks(30).catch(() => ({ tasks: [] as TaskRecord[] })),
        agentApi.screenshots(12).catch(() => ({ screenshots: [] })),
      ]);
      setTasks(tasksRes.tasks || []);
      setScreenshots(shotsRes.screenshots || []);
    } catch {
      // silent
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, [loadData, progress]);

  // Auto-scroll logs
  useEffect(() => {
    if (activeTab === "logs" && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [logs, activeTab]);

  const submitTask = async () => {
    if (!taskInput.trim()) return;
    setSubmitting(true);
    try {
      const res = await agentApi.submitTask(taskInput, "dashboard");
      toast({ title: tr("toast.task_sent"), description: `ID: ${res.task_id}` });
      setTaskInput("");
      setTimeout(loadData, 500);
    } catch (e) {
      toast({
        title: tr("toast.error"),
        description: e instanceof Error ? e.message : "",
        variant: "destructive",
      });
    } finally {
      setSubmitting(false);
    }
  };

  const sendCommand = async (cmd: "pause" | "resume" | "stop" | "start") => {
    try {
      await agentApi.command(cmd);
      toast({ title: `${tr("toast.command_sent")}: ${cmd}` });
      setTimeout(refresh, 200);
    } catch (e) {
      toast({
        title: tr("toast.error"),
        description: e instanceof Error ? e.message : "",
        variant: "destructive",
      });
    }
  };

  const captureScreenshot = async () => {
    try {
      await agentApi.captureScreenshot();
      toast({ title: tr("toast.captured") });
      setTimeout(loadData, 500);
    } catch {
      toast({
        title: tr("toast.error"),
        description: tr("toast.agent_offline"),
        variant: "destructive",
      });
    }
  };

  const handleLanguageChange = (newLang: Lang) => {
    setLang(newLang);
    setStoredLang(newLang);
  };

  const state = status?.state ?? "stopped";
  const currentTask = status?.current_task;
  const memory = status?.memory;

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card/30 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="relative">
              <div className="absolute inset-0 bg-primary/30 blur-md rounded-lg" />
              <div className="relative w-10 h-10 rounded-lg bg-gradient-to-br from-primary/20 to-accent/20 border border-primary/30 flex items-center justify-center">
                <Bot className="w-5 h-5 text-primary" />
              </div>
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight">Z.AGENT</h1>
              <p className="text-xs text-muted-foreground">{tr("dash.subtitle")}</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Language toggle */}
            <LanguageSelector currentLang={lang} onLanguageChange={handleLanguageChange} />

            <div className="flex items-center gap-2 text-xs">
              <Circle
                className={cn(
                  "w-2 h-2 fill-current",
                  connected ? "text-emerald-500" : "text-red-500"
                )}
              />
              <span className="text-muted-foreground">
                {connected ? tr("dash.connected") : tr("dash.offline")}
              </span>
            </div>
            <Badge
              variant="outline"
              className={cn("font-mono uppercase", STATE_COLORS[state])}
            >
              {stateLabel(state, lang)}
            </Badge>
            <div className="flex gap-1">
              <Button
                size="sm"
                variant="ghost"
                onClick={() => sendCommand("pause")}
                disabled={state !== "idle" && state !== "executing"}
                title="Pause"
              >
                <Pause className="w-4 h-4" />
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => sendCommand("resume")}
                disabled={state !== "paused"}
                title="Resume"
              >
                <Play className="w-4 h-4" />
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={refresh}
                title="Refresh"
              >
                <RefreshCw className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-6 space-y-6">
        {/* Stats row */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
          <StatCard icon={Activity} label={tr("label.state")} value={stateLabel(state, lang)} color={STATE_COLORS[state] || ""} />
          <StatCard icon={Clock} label={tr("label.queue")} value={String(status?.queue_size ?? 0)} />
          <StatCard icon={Brain} label={tr("dash.facts")} value={String(memory?.facts_count ?? 0)} />
          <StatCard icon={Zap} label={tr("dash.tasks")} value={String(memory?.tasks_count ?? 0)} />
          <StatCard icon={Cpu} label={tr("label.uptime")} value={`${Math.floor((status?.uptime_s ?? 0) / 60)}m`} />
          <StatCard icon={Terminal} label={tr("label.logs")} value={String(logs.length)} />
        </div>

        {/* Main grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: Task submission + current task */}
          <div className="lg:col-span-2 space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Send className="w-4 h-4 text-primary" />
                  {tr("dash.submit_task")}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <Textarea
                  placeholder={tr("dash.task_placeholder")}
                  value={taskInput}
                  onChange={(e) => setTaskInput(e.target.value)}
                  rows={3}
                  className="resize-none"
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submitTask();
                  }}
                />
                <div className="flex flex-wrap gap-2">
                  {QUICK_TASKS.map((qt) => {
                    const Icon = qt.icon;
                    return (
                      <button
                        key={qt.label}
                        onClick={() => setTaskInput(qt.prompt)}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs border border-border bg-card hover:bg-accent hover:text-accent-foreground transition-colors"
                      >
                        <Icon className="w-3 h-3" />
                        {qt.label}
                      </button>
                    );
                  })}
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-xs text-muted-foreground">
                    ⌘/Ctrl+Enter
                  </span>
                  <Button onClick={submitTask} disabled={!taskInput.trim() || submitting}>
                    <Send className="w-4 h-4 mr-2" />
                    {submitting ? tr("dash.sending") : tr("dash.send")}
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Current task */}
            {currentTask && (
              <Card className="border-primary/30">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
                    {tr("dash.current_task")}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Badge variant="outline" className="font-mono text-xs">{currentTask.id}</Badge>
                      <Badge variant="secondary" className="text-xs">{tr("label.via")} {currentTask.source}</Badge>
                    </div>
                    <p className="text-sm">{currentTask.request}</p>
                  </div>
                </CardContent>
              </Card>
            )}

            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="tasks">
                  <FileText className="w-4 h-4 mr-2" />
                  {tr("dash.tasks")} ({tasks.length})
                </TabsTrigger>
                <TabsTrigger value="logs">
                  <Terminal className="w-4 h-4 mr-2" />
                  {tr("dash.logs")} ({logs.length})
                </TabsTrigger>
                <TabsTrigger value="screens">
                  <ImageIcon className="w-4 h-4 mr-2" />
                  {tr("dash.screenshots")} ({screenshots.length})
                </TabsTrigger>
              </TabsList>

              <TabsContent value="tasks" className="mt-4">
                <Card>
                  <CardContent className="p-0">
                    <ScrollArea className="h-[500px]">
                      {tasks.length === 0 ? (
                        <div className="p-8 text-center text-muted-foreground text-sm">
                          <FileText className="w-12 h-12 mx-auto mb-3 opacity-30" />
                          {tr("dash.no_tasks")}
                        </div>
                      ) : (
                        <div className="divide-y divide-border">
                          {tasks.map((task, idx) => (
                            <TaskItem key={task.task_id || idx} task={task} lang={lang} tr={tr} />
                          ))}
                        </div>
                      )}
                    </ScrollArea>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="logs" className="mt-4">
                <Card>
                  <CardContent className="p-0">
                    <ScrollArea className="h-[500px]">
                      <div className="font-mono text-xs p-3 space-y-0.5">
                        {logs.length === 0 ? (
                          <div className="p-8 text-center text-muted-foreground">
                            <Terminal className="w-12 h-12 mx-auto mb-3 opacity-30" />
                            {tr("dash.no_logs")}
                          </div>
                        ) : (
                          logs.map((log, idx) => <LogLine key={idx} log={log} />)
                        )}
                        <div ref={logsEndRef} />
                      </div>
                    </ScrollArea>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="screens" className="mt-4">
                <Card>
                  <CardContent className="p-4">
                    <div className="flex justify-between items-center mb-4">
                      <p className="text-sm text-muted-foreground">{tr("dash.vlm_description")}</p>
                      <Button size="sm" variant="outline" onClick={captureScreenshot}>
                        <Camera className="w-4 h-4 mr-2" />
                        {tr("dash.capture_now")}
                      </Button>
                    </div>
                    {screenshots.length === 0 ? (
                      <div className="p-8 text-center text-muted-foreground text-sm">
                        <ImageIcon className="w-12 h-12 mx-auto mb-3 opacity-30" />
                        {tr("dash.no_screenshots")}
                      </div>
                    ) : (
                      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                        {screenshots.map((shot) => (
                          <ScreenshotTile key={shot.name} shot={shot} />
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
          </div>

          {/* Right: Memory + modules */}
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Brain className="w-4 h-4 text-primary" />
                  {tr("dash.memory")}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <MemoryRow label={tr("dash.facts")} value={memory?.facts_count ?? 0} />
                <MemoryRow label={tr("dash.preferences")} value={memory?.preferences_count ?? 0} />
                <MemoryRow label={tr("dash.shortcuts")} value={memory?.shortcuts_count ?? 0} />
                <Separator />
                <div>
                  <p className="text-xs text-muted-foreground mb-2">{tr("dash.recent_tasks")}</p>
                  <div className="space-y-1.5">
                    {memory?.recent_tasks?.map((task, idx) => (
                      <div key={idx} className="flex items-center gap-2 text-xs">
                        {(task as Record<string, unknown>).success ? (
                          <CheckCircle2 className="w-3 h-3 text-emerald-500" />
                        ) : (
                          <XCircle className="w-3 h-3 text-red-500" />
                        )}
                        <span className="truncate">
                          {String((task as Record<string, unknown>).request || "").slice(0, 40)}
                        </span>
                      </div>
                    )) ?? <p className="text-xs text-muted-foreground">{tr("misc.no_recent_tasks")}</p>}
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Cpu className="w-4 h-4 text-primary" />
                  {tr("dash.modules")}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-2">
                  {Object.entries(MODULE_ICONS).map(([name, Icon]) => (
                    <div key={name} className="flex items-center gap-2 p-2 rounded-md border border-border bg-card/50">
                      <Icon className="w-4 h-4 text-primary" />
                      <span className="text-xs">{tr(`module.${name}`)}</span>
                      <Circle className="w-1.5 h-1.5 fill-emerald-500 text-emerald-500 ml-auto" />
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Eye className="w-4 h-4 text-primary" />
                  {tr("dash.vlm_perception")}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-xs text-muted-foreground mb-3">{tr("dash.vlm_description")}</p>
                <Button size="sm" variant="outline" className="w-full" onClick={captureScreenshot}>
                  <Camera className="w-4 h-4 mr-2" />
                  {tr("dash.analyze_screen")}
                </Button>
              </CardContent>
            </Card>

            <Card className="bg-gradient-to-br from-primary/5 to-accent/5 border-primary/20">
              <CardContent className="pt-6">
                <div className="flex items-start gap-3">
                  <Lightbulb className="w-5 h-5 text-primary flex-shrink-0 mt-0.5" />
                  <div className="space-y-1.5">
                    <p className="text-sm font-medium">{tr("misc.tip_title")}</p>
                    <p className="text-xs text-muted-foreground leading-relaxed">{tr("misc.tip_body")}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Advanced capabilities card (new) */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Sparkles className="w-4 h-4 text-primary" />
                  {lang === "fr" ? "Capacités avancées" : "Advanced capabilities"}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2.5">
                <Capability icon={Sparkles} label={lang === "fr" ? "ReAct loop (auto-critique)" : "ReAct loop (self-critique)"} active />
                <Capability icon={Code} label={lang === "fr" ? "Code interpreter (Python sandbox)" : "Code interpreter (Python sandbox)"} active />
                <Capability icon={Search} label={lang === "fr" ? "Recherche web temps réel" : "Real-time web search"} active />
                <Capability icon={Network} label={lang === "fr" ? "Orchestrateur multi-agents" : "Multi-agent orchestrator"} active />
                <Capability icon={Brain} label={lang === "fr" ? "Skill library (apprentissage)" : "Skill library (learning)"} active />
                <Capability icon={Zap} label={lang === "fr" ? "Tool calling natif GLM" : "Native GLM tool calling"} active />
                <Capability icon={Mic} label={lang === "fr" ? "Voice control (Whisper STT/TTS)" : "Voice control (Whisper STT/TTS)"} active />
                <Capability icon={MessageSquare} label={lang === "fr" ? "Contexte conversation long terme" : "Long-term conversation context"} active />
                <Capability icon={Plug} label={lang === "fr" ? "Plugin marketplace" : "Plugin marketplace"} active />
                <Capability icon={Network} label="MCP (Model Context Protocol)" active />
                <Capability icon={Radio} label={lang === "fr" ? "Vision streaming continu" : "Continuous vision streaming"} active />
              </CardContent>
            </Card>
          </div>
        </div>
      </main>

      <footer className="border-t border-border mt-12 py-4">
        <div className="container mx-auto px-4 flex justify-between items-center text-xs text-muted-foreground">
          <span>Z.AGENT v1.1.0 — {lang === "fr" ? "propulsé par z.ai GLM" : "powered by z.ai GLM"}</span>
          <span className="font-mono">{connected ? "●" : "○"} {state}</span>
        </div>
      </footer>
    </div>
  );
}

// === Sub-components ===

function StatCard({
  icon: Icon, label, value, color,
}: {
  icon: typeof Activity; label: string; value: string; color?: string;
}) {
  return (
    <Card className="overflow-hidden">
      <CardContent className="p-3">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs text-muted-foreground uppercase tracking-wider">{label}</span>
          <Icon className="w-3.5 h-3.5 text-muted-foreground" />
        </div>
        <div className={cn("text-lg font-bold", color && "font-mono")}>{value}</div>
      </CardContent>
    </Card>
  );
}

function MemoryRow({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="text-sm font-mono">{value}</span>
    </div>
  );
}

function Capability({ icon: Icon, label, active }: { icon: typeof Sparkles; label: string; active: boolean }) {
  return (
    <div className="flex items-center gap-2 text-xs">
      <Icon className={cn("w-3.5 h-3.5 flex-shrink-0", active ? "text-primary" : "text-muted-foreground")} />
      <span className="flex-1">{label}</span>
      <Circle className={cn("w-1.5 h-1.5 fill-current flex-shrink-0", active ? "text-emerald-500" : "text-zinc-600")} />
    </div>
  );
}

function LogLine({ log }: { log: { timestamp: string; level: string; logger: string; message: string } }) {
  const levelColors: Record<string, string> = {
    DEBUG: "text-zinc-500",
    INFO: "text-emerald-400",
    WARNING: "text-amber-400",
    ERROR: "text-red-400",
    CRITICAL: "text-red-500",
  };
  const time = log.timestamp ? new Date(log.timestamp).toLocaleTimeString(undefined, { hour12: false }) : "";
  return (
    <div className="flex gap-2 leading-relaxed hover:bg-accent/20 -mx-1 px-1 rounded">
      <span className="text-zinc-600 flex-shrink-0">{time}</span>
      <span className={cn("flex-shrink-0 w-12", levelColors[log.level] || "text-zinc-400")}>{log.level}</span>
      <span className="text-zinc-500 flex-shrink-0 w-20 truncate">{log.logger}</span>
      <span className="text-foreground/90 break-all">{log.message}</span>
    </div>
  );
}

function TaskItem({
  task, lang, tr,
}: {
  task: TaskRecord;
  lang: Lang;
  tr: (key: string, vars?: Record<string, string | number>) => string;
}) {
  const [expanded, setExpanded] = useState(false);
  const success = task.success;
  const plan = task.plan;
  const result = task.result;
  const steps = plan?.plan || [];
  const results = result?.results || [];
  const reactTrace = (result as Record<string, unknown>)?.react_trace as Array<Record<string, unknown>> | undefined;
  const skillsSaved = (result as Record<string, unknown>)?.skills_saved as Array<Record<string, unknown>> | undefined;
  const isReactMode = (plan as Record<string, unknown>)?.react_mode === true;
  const time = task.timestamp ? new Date(task.timestamp * 1000).toLocaleString(undefined, { dateStyle: "short", timeStyle: "short" }) : "";

  return (
    <div className="p-4 hover:bg-accent/20 transition-colors">
      <button onClick={() => setExpanded(!expanded)} className="w-full text-left flex items-start gap-3">
        {success ? <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" />
                 : <XCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />}
        <div className="flex-1 min-w-0">
          <p className="text-sm truncate">{task.request}</p>
          <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground flex-wrap">
            <span>{time}</span>
            {task.source && (<><span>·</span><Badge variant="outline" className="text-[10px] py-0 h-4">{task.source}</Badge></>)}
            {result && (<><span>·</span><span>{result.succeeded}/{result.total_steps} {tr("dash.steps_label")}</span></>)}
            {isReactMode && (
              <Badge variant="outline" className="text-[10px] py-0 h-4 bg-primary/10 text-primary border-primary/30">
                <Sparkles className="w-2.5 h-2.5 mr-1" /> ReAct
              </Badge>
            )}
            {skillsSaved && skillsSaved.length > 0 && (
              <Badge variant="outline" className="text-[10px] py-0 h-4 bg-amber-500/10 text-amber-400 border-amber-500/30">
                <Sparkles className="w-2.5 h-2.5 mr-1" /> {skillsSaved.length} skill{skillsSaved.length > 1 ? "s" : ""}
              </Badge>
            )}
          </div>
        </div>
        <ChevronRight className={cn("w-4 h-4 text-muted-foreground transition-transform", expanded && "rotate-90")} />
      </button>

      {expanded && (
        <div className="mt-3 ml-7 space-y-3">
          {plan?.understanding && (
            <p className="text-xs text-muted-foreground italic">💡 {plan.understanding}</p>
          )}

          {/* ReAct trace (new) */}
          {reactTrace && reactTrace.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-medium text-primary uppercase tracking-wider flex items-center gap-1">
                <Sparkles className="w-3 h-3" />
                ReAct Trace ({reactTrace.length} turns)
              </p>
              <div className="border border-border rounded-md p-3 bg-card/50 space-y-2 max-h-80 overflow-y-auto">
                {reactTrace.map((entry, idx) => {
                  const thought = String(entry.thought || "");
                  const action = String(entry.action || "");
                  const observation = String(entry.observation || "");
                  const critique = String(entry.critique || "");
                  const ok = entry.success as boolean;
                  return (
                    <div key={idx} className="text-xs space-y-1 pb-2 border-b border-border last:border-0 last:pb-0">
                      <div className="flex items-start gap-2">
                        <span className="font-mono text-muted-foreground">T{String(entry.turn || idx + 1)}.</span>
                        {ok === true && <CheckCircle2 className="w-3 h-3 text-emerald-500 mt-0.5 flex-shrink-0" />}
                        {ok === false && <XCircle className="w-3 h-3 text-red-500 mt-0.5 flex-shrink-0" />}
                        {ok === undefined && <Circle className="w-3 h-3 text-muted-foreground mt-0.5 flex-shrink-0" />}
                        <div className="flex-1 min-w-0">
                          <p className="text-foreground/90 italic">💭 {thought}</p>
                          {action && (
                            <p className="font-mono text-primary text-[11px] mt-0.5">→ {action}</p>
                          )}
                          {observation && (
                            <p className="text-muted-foreground text-[11px] mt-0.5">👁 {observation.slice(0, 200)}</p>
                          )}
                          {critique && (
                            <p className="text-amber-400/70 text-[11px] mt-0.5">✓ {critique.slice(0, 150)}</p>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Skills saved (new) */}
          {skillsSaved && skillsSaved.length > 0 && (
            <div className="space-y-1">
              <p className="text-xs font-medium text-amber-400 uppercase tracking-wider flex items-center gap-1">
                <Sparkles className="w-3 h-3" />
                Skills learned
              </p>
              {skillsSaved.map((s, idx) => (
                <div key={idx} className="text-xs bg-amber-500/5 border border-amber-500/20 rounded p-2">
                  <p className="font-mono text-amber-400">{String(s.name || "")}</p>
                  <p className="text-muted-foreground">{String(s.description || "")}</p>
                </div>
              ))}
            </div>
          )}

          {/* Original plan (for non-ReAct tasks) */}
          {steps.length > 0 && !isReactMode && (
            <div className="space-y-1">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                {tr("dash.plan_label")} ({steps.length} {tr("dash.steps_label")})
              </p>
              {steps.map((step, idx) => {
                const stepResult = results[idx];
                const stepOk = stepResult ? (stepResult as Record<string, unknown>).success : null;
                return (
                  <div key={idx} className="flex items-start gap-2 text-xs">
                    <span className="font-mono text-muted-foreground w-6">{step.step}.</span>
                    {stepOk === true && <CheckCircle2 className="w-3 h-3 text-emerald-500 mt-0.5" />}
                    {stepOk === false && <XCircle className="w-3 h-3 text-red-500 mt-0.5" />}
                    {stepOk === null && <Circle className="w-3 h-3 text-muted-foreground mt-0.5" />}
                    <span className="font-mono text-primary">{step.action}</span>
                    <span className="text-muted-foreground truncate">{step.reasoning}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ScreenshotTile({ shot }: { shot: { name: string; size: number; modified: number } }) {
  const [errored, setErrored] = useState(false);
  const src = useMemo(() => {
    try { return agentApi.screenshotUrl(shot.name); } catch { return null; }
  }, [shot.name]);
  const time = new Date(shot.modified * 1000).toLocaleTimeString(undefined, { hour: 2, minute: 2, second: 2 });

  return (
    <div className="relative group rounded-md overflow-hidden border border-border bg-card">
      {src && !errored ? (
        <img src={src} alt={shot.name} className="w-full aspect-video object-cover" loading="lazy" onError={() => setErrored(true)} />
      ) : (
        <div className="w-full aspect-video flex items-center justify-center bg-muted">
          <ImageIcon className="w-6 h-6 text-muted-foreground" />
        </div>
      )}
      <div className="absolute bottom-0 left-0 right-0 p-2 bg-gradient-to-t from-black/80 to-transparent">
        <p className="text-[10px] font-mono text-white/90 truncate">{shot.name}</p>
        <p className="text-[10px] text-white/60">{time}</p>
      </div>
    </div>
  );
}
