"use client";

import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import {
  Bot, Activity, Send, Square, Play, Pause, RefreshCw,
  Terminal, Image as ImageIcon, Brain, Cpu, Clock, Zap,
  ChevronRight, Circle, AlertCircle, CheckCircle2, XCircle,
  Camera, Trash2, FileText, Mail, Calendar, Globe, Monitor,
  Lightbulb, Eye,
} from "lucide-react";
import { useAgent } from "@/hooks/use-agent";
import { agentApi, type TaskRecord } from "@/lib/agent-api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
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

const STATE_LABELS: Record<string, string> = {
  idle: "En attente",
  planning: "Planification",
  executing: "Exécution",
  paused: "En pause",
  error: "Erreur",
  stopped: "Arrêté",
};

const MODULE_ICONS: Record<string, typeof FileText> = {
  screen: Monitor,
  files: FileText,
  email: Mail,
  calendar: Calendar,
  browser: Globe,
  system: Cpu,
};

const QUICK_TASKS = [
  { icon: FileText, label: "Trier Téléchargements", prompt: "Organise mon dossier Téléchargements par type de fichier" },
  { icon: Mail, label: "Lire emails non lus", prompt: "Lis mes 5 derniers emails non lus et fais-moi un résumé" },
  { icon: Calendar, label: "Prochains événements", prompt: "Liste mes 10 prochains événements de calendrier" },
  { icon: Monitor, label: "Décrire l'écran", prompt: "Décris ce qu'il y a actuellement sur mon écran" },
  { icon: Cpu, label: "Infos système", prompt: "Donne-moi les informations système (CPU, RAM, disque)" },
  { icon: Camera, label: "Capture d'écran", prompt: "Prends une capture d'écran et analyse-la" },
];

export default function Dashboard() {
  const { status, logs, progress, connected, refresh } = useAgent();
  const { toast } = useToast();
  const [taskInput, setTaskInput] = useState("");
  const [tasks, setTasks] = useState<TaskRecord[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [screenshots, setScreenshots] = useState<Array<{ name: string; size: number; modified: number }>>([]);
  const [activeTab, setActiveTab] = useState("tasks");
  const logsEndRef = useRef<HTMLDivElement>(null);

  // Load tasks + screenshots periodically
  const loadData = useCallback(async () => {
    try {
      const [tasksRes, shotsRes] = await Promise.all([
        agentApi.recentTasks(30).catch(() => ({ tasks: [] as TaskRecord[] })),
        agentApi.screenshots(12).catch(() => ({ screenshots: [] })),
      ]);
      setTasks(tasksRes.tasks || []);
      setScreenshots(shotsRes.screenshots || []);
    } catch (e) {
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
      toast({
        title: "Tâche envoyée",
        description: `ID: ${res.task_id}`,
      });
      setTaskInput("");
      setTimeout(loadData, 500);
    } catch (e) {
      toast({
        title: "Erreur",
        description: e instanceof Error ? e.message : "Échec de l'envoi",
        variant: "destructive",
      });
    } finally {
      setSubmitting(false);
    }
  };

  const sendCommand = async (cmd: "pause" | "resume" | "stop" | "start") => {
    try {
      await agentApi.command(cmd);
      toast({ title: `Commande: ${cmd}`, description: "Envoyée à l'agent" });
      setTimeout(refresh, 200);
    } catch (e) {
      toast({
        title: "Erreur",
        description: e instanceof Error ? e.message : "Échec",
        variant: "destructive",
      });
    }
  };

  const captureScreenshot = async () => {
    try {
      await agentApi.captureScreenshot();
      toast({ title: "Capture prise", description: "Rafraîchissement..." });
      setTimeout(loadData, 500);
    } catch (e) {
      toast({
        title: "Erreur",
        description: "Agent hors-ligne ou perception indisponible",
        variant: "destructive",
      });
    }
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
              <p className="text-xs text-muted-foreground">Desktop Control Center</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 text-xs">
              <Circle
                className={cn(
                  "w-2 h-2 fill-current",
                  connected ? "text-emerald-500" : "text-red-500"
                )}
              />
              <span className="text-muted-foreground">
                {connected ? "WS connecté" : "Hors-ligne"}
              </span>
            </div>
            <Badge
              variant="outline"
              className={cn("font-mono uppercase", STATE_COLORS[state])}
            >
              {STATE_LABELS[state] || state}
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
                title="Reprendre"
              >
                <Play className="w-4 h-4" />
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={refresh}
                title="Rafraîchir"
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
          <StatCard
            icon={Activity}
            label="État"
            value={STATE_LABELS[state] || state}
            color={STATE_COLORS[state] || ""}
          />
          <StatCard
            icon={Clock}
            label="File d'attente"
            value={String(status?.queue_size ?? 0)}
          />
          <StatCard
            icon={Brain}
            label="Faits mémo"
            value={String(memory?.facts_count ?? 0)}
          />
          <StatCard
            icon={Zap}
            label="Tâches"
            value={String(memory?.tasks_count ?? 0)}
          />
          <StatCard
            icon={Cpu}
            label="Uptime"
            value={`${Math.floor((status?.uptime_s ?? 0) / 60)}m`}
          />
          <StatCard
            icon={Terminal}
            label="Logs"
            value={String(logs.length)}
          />
        </div>

        {/* Main grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: Task submission + current task */}
          <div className="lg:col-span-2 space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Send className="w-4 h-4 text-primary" />
                  Soumettre une tâche
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <Textarea
                  placeholder="Décris la tâche en langage naturel. Ex: « Tri mes téléchargements par type de fichier et envoie-moi un résumé par mail »"
                  value={taskInput}
                  onChange={(e) => setTaskInput(e.target.value)}
                  rows={3}
                  className="resize-none"
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                      submitTask();
                    }
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
                    Cmd/Ctrl+Enter pour envoyer
                  </span>
                  <Button
                    onClick={submitTask}
                    disabled={!taskInput.trim() || submitting}
                  >
                    <Send className="w-4 h-4 mr-2" />
                    {submitting ? "Envoi..." : "Envoyer"}
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
                    Tâche en cours
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Badge variant="outline" className="font-mono text-xs">
                        {currentTask.id}
                      </Badge>
                      <Badge variant="secondary" className="text-xs">
                        via {currentTask.source}
                      </Badge>
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
                  Tâches ({tasks.length})
                </TabsTrigger>
                <TabsTrigger value="logs">
                  <Terminal className="w-4 h-4 mr-2" />
                  Logs ({logs.length})
                </TabsTrigger>
                <TabsTrigger value="screens">
                  <ImageIcon className="w-4 h-4 mr-2" />
                  Captures ({screenshots.length})
                </TabsTrigger>
              </TabsList>

              {/* Tasks tab */}
              <TabsContent value="tasks" className="mt-4">
                <Card>
                  <CardContent className="p-0">
                    <ScrollArea className="h-[500px]">
                      {tasks.length === 0 ? (
                        <div className="p-8 text-center text-muted-foreground text-sm">
                          <FileText className="w-12 h-12 mx-auto mb-3 opacity-30" />
                          Aucune tâche pour le moment.
                          <br />
                          Soumets-en une ci-dessus pour commencer.
                        </div>
                      ) : (
                        <div className="divide-y divide-border">
                          {tasks.map((task, idx) => (
                            <TaskItem key={task.task_id || idx} task={task} />
                          ))}
                        </div>
                      )}
                    </ScrollArea>
                  </CardContent>
                </Card>
              </TabsContent>

              {/* Logs tab */}
              <TabsContent value="logs" className="mt-4">
                <Card>
                  <CardContent className="p-0">
                    <ScrollArea className="h-[500px]">
                      <div className="font-mono text-xs p-3 space-y-0.5">
                        {logs.length === 0 ? (
                          <div className="p-8 text-center text-muted-foreground">
                            <Terminal className="w-12 h-12 mx-auto mb-3 opacity-30" />
                            Aucun log. Connectez l'agent Python pour voir les logs en temps réel.
                          </div>
                        ) : (
                          logs.map((log, idx) => (
                            <LogLine key={idx} log={log} />
                          ))
                        )}
                        <div ref={logsEndRef} />
                      </div>
                    </ScrollArea>
                  </CardContent>
                </Card>
              </TabsContent>

              {/* Screenshots tab */}
              <TabsContent value="screens" className="mt-4">
                <Card>
                  <CardContent className="p-4">
                    <div className="flex justify-between items-center mb-4">
                      <p className="text-sm text-muted-foreground">
                        Captures d'écran de l'agent (VLM perception)
                      </p>
                      <Button size="sm" variant="outline" onClick={captureScreenshot}>
                        <Camera className="w-4 h-4 mr-2" />
                        Capturer maintenant
                      </Button>
                    </div>
                    {screenshots.length === 0 ? (
                      <div className="p-8 text-center text-muted-foreground text-sm">
                        <ImageIcon className="w-12 h-12 mx-auto mb-3 opacity-30" />
                        Aucune capture disponible.
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
                  Mémoire
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <MemoryRow label="Faits persistants" value={memory?.facts_count ?? 0} />
                <MemoryRow label="Préférences" value={memory?.preferences_count ?? 0} />
                <MemoryRow label="Raccourcis appris" value={memory?.shortcuts_count ?? 0} />
                <Separator />
                <div>
                  <p className="text-xs text-muted-foreground mb-2">Dernières tâches</p>
                  <div className="space-y-1.5">
                    {memory?.recent_tasks?.map((t, idx) => (
                      <div key={idx} className="flex items-center gap-2 text-xs">
                        {(t as Record<string, unknown>).success ? (
                          <CheckCircle2 className="w-3 h-3 text-emerald-500" />
                        ) : (
                          <XCircle className="w-3 h-3 text-red-500" />
                        )}
                        <span className="truncate">
                          {String((t as Record<string, unknown>).request || "").slice(0, 40)}
                        </span>
                      </div>
                    )) ?? (
                      <p className="text-xs text-muted-foreground">Aucune tâche récente</p>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Cpu className="w-4 h-4 text-primary" />
                  Modules actifs
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-2">
                  {Object.entries(MODULE_ICONS).map(([name, Icon]) => (
                    <div
                      key={name}
                      className="flex items-center gap-2 p-2 rounded-md border border-border bg-card/50"
                    >
                      <Icon className="w-4 h-4 text-primary" />
                      <span className="text-xs capitalize">{name}</span>
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
                  Perception VLM
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-xs text-muted-foreground mb-3">
                  GLM-4V analyse l'écran pour comprendre l'interface et localiser les éléments.
                </p>
                <Button
                  size="sm"
                  variant="outline"
                  className="w-full"
                  onClick={captureScreenshot}
                >
                  <Camera className="w-4 h-4 mr-2" />
                  Analyser l'écran
                </Button>
              </CardContent>
            </Card>

            <Card className="bg-gradient-to-br from-primary/5 to-accent/5 border-primary/20">
              <CardContent className="pt-6">
                <div className="flex items-start gap-3">
                  <Lightbulb className="w-5 h-5 text-primary flex-shrink-0 mt-0.5" />
                  <div className="space-y-1.5">
                    <p className="text-sm font-medium">Astuce</p>
                    <p className="text-xs text-muted-foreground leading-relaxed">
                      L'agent fonctionne en autonomie complète. Tu peux lui envoyer
                      des tâches depuis Telegram quand tu es absent — il planifie,
                      exécute et te notifie du résultat.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </main>

      <footer className="border-t border-border mt-12 py-4">
        <div className="container mx-auto px-4 flex justify-between items-center text-xs text-muted-foreground">
          <span>Z.AGENT v1.0.0 — propulsé par z.ai GLM</span>
          <span className="font-mono">{connected ? "●" : "○"} {state}</span>
        </div>
      </footer>
    </div>
  );
}

// === Sub-components ===

function StatCard({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: typeof Activity;
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <Card className="overflow-hidden">
      <CardContent className="p-3">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs text-muted-foreground uppercase tracking-wider">
            {label}
          </span>
          <Icon className="w-3.5 h-3.5 text-muted-foreground" />
        </div>
        <div className={cn("text-lg font-bold", color && "font-mono")}>
          {value}
        </div>
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

function LogLine({ log }: { log: { timestamp: string; level: string; logger: string; message: string } }) {
  const levelColors: Record<string, string> = {
    DEBUG: "text-zinc-500",
    INFO: "text-emerald-400",
    WARNING: "text-amber-400",
    ERROR: "text-red-400",
    CRITICAL: "text-red-500",
  };

  const time = log.timestamp ? new Date(log.timestamp).toLocaleTimeString("fr-FR", { hour12: false }) : "";

  return (
    <div className="flex gap-2 leading-relaxed hover:bg-accent/20 -mx-1 px-1 rounded">
      <span className="text-zinc-600 flex-shrink-0">{time}</span>
      <span className={cn("flex-shrink-0 w-12", levelColors[log.level] || "text-zinc-400")}>
        {log.level}
      </span>
      <span className="text-zinc-500 flex-shrink-0 w-20 truncate">{log.logger}</span>
      <span className="text-foreground/90 break-all">{log.message}</span>
    </div>
  );
}

function TaskItem({ task }: { task: TaskRecord }) {
  const [expanded, setExpanded] = useState(false);
  const success = task.success;
  const plan = task.plan;
  const result = task.result;
  const steps = plan?.plan || [];
  const results = result?.results || [];
  const time = task.timestamp ? new Date(task.timestamp * 1000).toLocaleString("fr-FR") : "";

  return (
    <div className="p-4 hover:bg-accent/20 transition-colors">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left flex items-start gap-3"
      >
        {success ? (
          <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" />
        ) : (
          <XCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
        )}
        <div className="flex-1 min-w-0">
          <p className="text-sm truncate">{task.request}</p>
          <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
            <span>{time}</span>
            {task.source && (
              <>
                <span>·</span>
                <Badge variant="outline" className="text-[10px] py-0 h-4">{task.source}</Badge>
              </>
            )}
            {result && (
              <>
                <span>·</span>
                <span>{result.succeeded}/{result.total_steps} étapes</span>
              </>
            )}
          </div>
        </div>
        <ChevronRight className={cn("w-4 h-4 text-muted-foreground transition-transform", expanded && "rotate-90")} />
      </button>

      {expanded && (
        <div className="mt-3 ml-7 space-y-2">
          {plan?.understanding && (
            <p className="text-xs text-muted-foreground italic">
              💡 {plan.understanding}
            </p>
          )}
          {steps.length > 0 && (
            <div className="space-y-1">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Plan ({steps.length} étapes)
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
    try {
      return agentApi.screenshotUrl(shot.name);
    } catch {
      return null;
    }
  }, [shot.name]);

  const time = new Date(shot.modified * 1000).toLocaleTimeString("fr-FR", { hour: 2, minute: 2, second: 2 });

  return (
    <div className="relative group rounded-md overflow-hidden border border-border bg-card">
      {src && !errored ? (
        <img
          src={src}
          alt={shot.name}
          className="w-full aspect-video object-cover"
          loading="lazy"
          onError={() => setErrored(true)}
        />
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
