"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useState, useRef } from "react";
import {
  Bot, Activity, Send, Play, Pause, RefreshCw,
  Terminal, Image as ImageIcon, Brain, Cpu, Clock, Zap,
  ChevronRight, Circle, CheckCircle2, XCircle,
  Camera, FileText, Mail, Calendar, Globe, Monitor, MonitorSmartphone,
  Lightbulb, Eye, Languages, Sparkles, Search, Code, Network,
  Mic, Plug, Radio, MessageSquare, Command, ArrowUp, Volume2,
} from "lucide-react";

// ============ Animated Counter ============
export function AnimatedCounter({ value, duration = 1 }: { value: number; duration?: number }) {
  const [count, setCount] = useState(0);
  const prevRef = useRef(0);

  useEffect(() => {
    const start = prevRef.current;
    const diff = value - start;
    const startTime = performance.now();

    const tick = (now: number) => {
      const elapsed = (now - startTime) / 1000;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setCount(Math.round(start + diff * eased));
      if (progress < 1) requestAnimationFrame(tick);
      else prevRef.current = value;
    };
    requestAnimationFrame(tick);
  }, [value, duration]);

  return <>{count}</>;
}

// ============ State Orb ============
const STATE_CONFIG: Record<string, { color: string; label_en: string; label_fr: string; speed: number }> = {
  idle:       { color: "#10B981", label_en: "Idle",       label_fr: "En attente",    speed: 8 },
  planning:   { color: "#F59E0B", label_en: "Planning",   label_fr: "Planification", speed: 3 },
  executing:  { color: "#06B6D4", label_en: "Executing",  label_fr: "Exécution",     speed: 1.5 },
  paused:     { color: "#64748B", label_en: "Paused",     label_fr: "En pause",      speed: 0 },
  error:      { color: "#EF4444", label_en: "Error",      label_fr: "Erreur",        speed: 2 },
  stopped:    { color: "#EF4444", label_en: "Stopped",    label_fr: "Arrêté",        speed: 0 },
};

export function StateOrb({ state, lang }: { state: string; lang: "en" | "fr" }) {
  const cfg = STATE_CONFIG[state] || STATE_CONFIG.stopped;
  const label = lang === "fr" ? cfg.label_fr : cfg.label_en;

  return (
    <div className="relative flex items-center justify-center w-20 h-20">
      <motion.div
        className="absolute inset-0 rounded-full"
        style={{
          background: `conic-gradient(from 0deg, ${cfg.color}80, transparent, ${cfg.color}80)`,
          animation: cfg.speed > 0 ? `spin-slow ${cfg.speed}s linear infinite` : "none",
          opacity: cfg.speed > 0 ? 1 : 0.3,
        }}
      />
      <motion.div
        className="absolute inset-3 rounded-full blur-lg"
        style={{ background: cfg.color, opacity: 0.4 }}
        animate={{ scale: [1, 1.15, 1], opacity: [0.3, 0.5, 0.3] }}
        transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="relative w-14 h-14 rounded-full flex items-center justify-center"
        style={{
          background: `radial-gradient(circle, ${cfg.color}30, ${cfg.color}10)`,
          border: `1px solid ${cfg.color}50`,
          boxShadow: `0 0 30px ${cfg.color}40, inset 0 0 20px ${cfg.color}20`,
        }}
        animate={cfg.speed > 0 ? { scale: [1, 1.06, 1] } : {}}
        transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
      >
        <Bot className="w-6 h-6" style={{ color: cfg.color }} />
      </motion.div>
      <motion.div
        className="absolute -bottom-6 text-[10px] font-mono uppercase tracking-widest whitespace-nowrap"
        style={{ color: cfg.color }}
        key={label}
        initial={{ opacity: 0, y: -4 }}
        animate={{ opacity: 1, y: 0 }}
      >
        {label}
      </motion.div>
    </div>
  );
}

// ============ Glass Card ============
export function GlassCard({
  children, className = "", glow = false,
}: {
  children: React.ReactNode;
  className?: string;
  glow?: boolean;
}) {
  return (
    <motion.div
      className={`glass rounded-2xl ${glow ? "glow-primary" : ""} ${className}`}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      {children}
    </motion.div>
  );
}

// ============ Stat Pill ============
export function StatPill({
  icon: Icon, label, value, color = "#10B981",
}: {
  icon: typeof Activity;
  label: string;
  value: number | string;
  color?: string;
}) {
  return (
    <div className="glass rounded-xl p-3 flex items-center gap-3 min-w-0">
      <div
        className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0"
        style={{ background: `${color}20`, border: `1px solid ${color}40` }}
      >
        <Icon className="w-4 h-4" style={{ color }} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-[10px] text-muted-foreground uppercase tracking-wider truncate">{label}</div>
        <div className="text-base font-mono font-bold truncate" style={{ color }}>
          {typeof value === "number" ? <AnimatedCounter value={value} /> : value}
        </div>
      </div>
    </div>
  );
}

// ============ Module Tile ============
const MODULE_META: Record<string, { icon: typeof FileText; color: string }> = {
  screen:      { icon: Monitor,           color: "#06B6D4" },
  files:       { icon: FileText,          color: "#10B981" },
  email:       { icon: Mail,              color: "#F59E0B" },
  calendar:    { icon: Calendar,          color: "#8B5CF6" },
  browser:     { icon: Globe,             color: "#06B6D4" },
  system:      { icon: Cpu,               color: "#EC4899" },
  windows:     { icon: MonitorSmartphone, color: "#3B82F6" },
  code:        { icon: Code,              color: "#10B981" },
  web:         { icon: Search,            color: "#06B6D4" },
  voice:       { icon: Mic,               color: "#F59E0B" },
  plugin:      { icon: Plug,              color: "#8B5CF6" },
  mcp:         { icon: Network,           color: "#EC4899" },
  vision:      { icon: Radio,             color: "#10B981" },
  slack:       { icon: Send,              color: "#3B82F6" },
};

export function ModuleTile({ name }: { name: string }) {
  const meta = MODULE_META[name] || { icon: Sparkles, color: "#64748B" };
  const Icon = meta.icon;

  return (
    <motion.div
      className="module-orb glass rounded-xl p-2.5 flex flex-col items-center gap-1.5 cursor-default"
      whileHover={{ scale: 1.08, y: -3 }}
      whileTap={{ scale: 0.96 }}
      title={name}
    >
      <div
        className="w-9 h-9 rounded-lg flex items-center justify-center relative"
        style={{
          background: `${meta.color}15`,
          border: `1px solid ${meta.color}30`,
        }}
      >
        <Icon className="w-4 h-4" style={{ color: meta.color }} />
        <motion.div
          className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 rounded-full"
          style={{ background: meta.color }}
          animate={{ opacity: [1, 0.3, 1] }}
          transition={{ duration: 2, repeat: Infinity }}
        />
      </div>
      <span className="text-[9px] text-muted-foreground font-mono truncate w-full text-center uppercase">
        {name}
      </span>
    </motion.div>
  );
}

// ============ Thinking Stream ============
export function ThinkingStream({
  traces, live,
}: {
  traces: Array<Record<string, unknown>>;
  live: boolean;
}) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [traces]);

  if (traces.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <motion.div
          animate={{ y: [0, -8, 0] }}
          transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
        >
          <Brain className="w-12 h-12 text-muted-foreground/40" />
        </motion.div>
        <p className="mt-4 text-sm text-muted-foreground">
          {live ? "Waiting for the agent to think..." : "Submit a task to see reasoning here."}
        </p>
        {live && (
          <motion.div className="flex gap-1 mt-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            {[0, 1, 2].map(i => (
              <motion.div
                key={i}
                className="w-1.5 h-1.5 rounded-full bg-primary"
                animate={{ scale: [1, 1.5, 1], opacity: [0.4, 1, 0.4] }}
                transition={{ duration: 1, repeat: Infinity, delay: i * 0.2 }}
              />
            ))}
          </motion.div>
        )}
      </div>
    );
  }

  return (
    <div ref={containerRef} className="space-y-3 overflow-y-auto max-h-[400px] pr-2">
      <AnimatePresence initial={false}>
        {traces.map((entry, idx) => {
          const thought = String(entry.thought || "");
          const action = String(entry.action || "");
          const observation = String(entry.observation || "");
          const success = entry.success as boolean | undefined;
          const turn = Number(entry.turn || idx + 1);
          const isLast = idx === traces.length - 1;

          return (
            <motion.div
              key={idx}
              className="timeline-dot relative pl-6"
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3 }}
            >
              <div className="absolute left-0 top-1.5">
                <motion.div
                  className={`w-3 h-3 rounded-full border-2 ${
                    success === true ? "bg-emerald-500 border-emerald-500/30"
                    : success === false ? "bg-red-500 border-red-500/30"
                    : "bg-primary border-primary/30"
                  }`}
                  animate={isLast && live ? { scale: [1, 1.3, 1] } : {}}
                  transition={{ duration: 1, repeat: Infinity }}
                />
              </div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[10px] font-mono text-muted-foreground">T{turn}</span>
                {isLast && live && (
                  <motion.span
                    className="text-[9px] font-mono text-primary uppercase"
                    animate={{ opacity: [0.5, 1, 0.5] }}
                    transition={{ duration: 1, repeat: Infinity }}
                  >
                    live
                  </motion.span>
                )}
              </div>
              {thought && (
                <div className="text-xs leading-relaxed mb-1.5 italic text-foreground/90">
                  <span className="text-primary/60 mr-1">💭</span>
                  {thought}
                </div>
              )}
              {action && (
                <div className="font-mono text-[11px] text-primary mb-1 pl-3 border-l border-primary/30">
                  → {action}
                </div>
              )}
              {observation && (
                <div className="text-[11px] text-muted-foreground pl-3">
                  <span className="opacity-60">👁</span> {observation.slice(0, 180)}
                  {observation.length > 180 && "..."}
                </div>
              )}
            </motion.div>
          );
        })}
      </AnimatePresence>
      {live && (
        <motion.div
          className="pl-6 text-xs text-primary/70 typewriter"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          thinking
        </motion.div>
      )}
    </div>
  );
}

// ============ Task Card ============
export function TaskCard({
  task, lang,
}: {
  task: Record<string, unknown>;
  lang: "en" | "fr";
}) {
  const [expanded, setExpanded] = useState(false);
  const success = Boolean(task.success);
  const plan = task.plan as Record<string, unknown> | undefined;
  const result = task.result as Record<string, unknown> | undefined;
  const reactTrace = result?.react_trace as Array<Record<string, unknown>> | undefined;
  const isReactMode = plan?.react_mode === true;
  const time = task.timestamp
    ? new Date(Number(task.timestamp) * 1000).toLocaleString(undefined, { dateStyle: "short", timeStyle: "short" })
    : "";
  const succeeded = Number(result?.succeeded || 0);
  const totalSteps = Number(result?.total_steps || 0);

  return (
    <motion.div
      layout
      className="glass rounded-xl overflow-hidden"
      whileHover={{ borderColor: "oklch(0.78 0.18 165 / 0.3)" }}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-4 flex items-start gap-3 text-left"
      >
        <motion.div animate={success ? { scale: [1, 1.2, 1] } : {}} transition={{ duration: 0.4 }}>
          {success ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" />
          ) : (
            <XCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
          )}
        </motion.div>
        <div className="flex-1 min-w-0">
          <p className="text-sm truncate">{String(task.request || "")}</p>
          <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground flex-wrap">
            <span className="font-mono">{time}</span>
            {task.source && (
              <span className="px-1.5 py-0.5 rounded text-[10px] bg-muted/50 font-mono">{String(task.source)}</span>
            )}
            <span>·</span>
            <span className="font-mono">{succeeded}/{totalSteps}</span>
            {isReactMode && (
              <span className="px-1.5 py-0.5 rounded text-[10px] bg-primary/15 text-primary border border-primary/30 flex items-center gap-1">
                <Sparkles className="w-2.5 h-2.5" /> ReAct
              </span>
            )}
          </div>
        </div>
        <motion.div animate={{ rotate: expanded ? 90 : 0 }}>
          <ChevronRight className="w-4 h-4 text-muted-foreground" />
        </motion.div>
      </button>
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4 pl-11 space-y-3">
              {plan?.understanding && (
                <p className="text-xs text-muted-foreground italic">💡 {String(plan.understanding)}</p>
              )}
              {reactTrace && reactTrace.length > 0 && <ThinkingStream traces={reactTrace} live={false} />}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

// ============ Command Palette ============
export function CommandPalette({
  open, onClose, onSubmit,
}: {
  open: boolean;
  onClose: () => void;
  onSubmit: (text: string) => void;
}) {
  const [input, setInput] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus input when palette opens. Input is cleared in handleSubmit after submit.
  useEffect(() => {
    if (open && inputRef.current) {
      const id = setTimeout(() => inputRef.current?.focus(), 50);
      return () => clearTimeout(id);
    }
  }, [open]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape" && open) onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onClose]);

  if (!open) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim()) {
      onSubmit(input);
      onClose();
    }
  };

  return (
    <AnimatePresence>
      <motion.div
        className="fixed inset-0 z-50 flex items-start justify-center pt-32 px-4"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
      >
        <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
        <motion.form
          onSubmit={handleSubmit}
          className="glass-strong rounded-2xl w-full max-w-2xl p-1 glow-primary"
          initial={{ scale: 0.95, y: -10 }}
          animate={{ scale: 1, y: 0 }}
          exit={{ scale: 0.95, y: -10 }}
          transition={{ type: "spring", damping: 25 }}
        >
          <div className="flex items-center gap-3 p-4">
            <Command className="w-5 h-5 text-primary" />
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              placeholder="Type a task in natural language..."
              className="flex-1 bg-transparent outline-none text-sm placeholder:text-muted-foreground"
            />
            <kbd className="text-[10px] font-mono text-muted-foreground bg-muted/50 px-1.5 py-0.5 rounded">
              ESC
            </kbd>
          </div>
        </motion.form>
      </motion.div>
    </AnimatePresence>
  );
}

// ============ Particle Background ============
// Uses deterministic seed to avoid hydration mismatch (no Math.random during render)
const PARTICLE_SEED = [
  { size: 2.1, left: 15.3, top: 22.1, duration: 12.5, delay: 0.3, opacity: 0.15 },
  { size: 1.8, left: 45.7, top: 67.2, duration: 14.2, delay: 1.1, opacity: 0.22 },
  { size: 3.0, left: 78.4, top: 12.5, duration: 11.8, delay: 2.0, opacity: 0.18 },
  { size: 1.5, left: 23.1, top: 88.3, duration: 16.0, delay: 0.7, opacity: 0.12 },
  { size: 2.5, left: 56.8, top: 34.7, duration: 13.3, delay: 1.5, opacity: 0.28 },
  { size: 1.2, left: 89.2, top: 56.1, duration: 15.1, delay: 0.5, opacity: 0.16 },
  { size: 2.8, left: 12.7, top: 45.9, duration: 12.0, delay: 2.3, opacity: 0.20 },
  { size: 1.9, left: 67.3, top: 78.4, duration: 14.5, delay: 1.8, opacity: 0.14 },
  { size: 2.3, left: 34.5, top: 15.2, duration: 13.7, delay: 0.9, opacity: 0.25 },
  { size: 1.6, left: 82.1, top: 89.7, duration: 16.2, delay: 1.3, opacity: 0.17 },
  { size: 2.0, left: 8.9, top: 62.3, duration: 11.5, delay: 2.5, opacity: 0.19 },
  { size: 2.7, left: 51.4, top: 23.8, duration: 15.8, delay: 0.4, opacity: 0.13 },
  { size: 1.4, left: 73.6, top: 71.2, duration: 13.0, delay: 1.7, opacity: 0.24 },
  { size: 2.2, left: 28.9, top: 54.6, duration: 14.8, delay: 2.1, opacity: 0.15 },
  { size: 1.7, left: 95.2, top: 38.4, duration: 12.3, delay: 0.8, opacity: 0.21 },
  { size: 2.9, left: 18.5, top: 81.3, duration: 16.5, delay: 1.9, opacity: 0.11 },
  { size: 1.3, left: 61.7, top: 7.2, duration: 13.9, delay: 0.6, opacity: 0.26 },
  { size: 2.4, left: 42.8, top: 93.1, duration: 11.2, delay: 2.7, opacity: 0.18 },
  { size: 1.8, left: 87.3, top: 48.5, duration: 15.4, delay: 1.0, opacity: 0.14 },
  { size: 2.6, left: 6.4, top: 29.7, duration: 14.1, delay: 1.4, opacity: 0.23 },
  { size: 1.5, left: 38.2, top: 76.8, duration: 12.8, delay: 2.2, opacity: 0.16 },
  { size: 2.1, left: 79.5, top: 5.4, duration: 16.0, delay: 0.2, opacity: 0.19 },
  { size: 1.9, left: 14.8, top: 68.9, duration: 13.5, delay: 1.6, opacity: 0.13 },
  { size: 2.5, left: 64.1, top: 41.7, duration: 15.7, delay: 2.4, opacity: 0.25 },
  { size: 1.6, left: 91.8, top: 84.2, duration: 11.9, delay: 0.1, opacity: 0.17 },
  { size: 2.3, left: 21.3, top: 13.6, duration: 14.4, delay: 1.2, opacity: 0.22 },
  { size: 1.4, left: 55.7, top: 59.3, duration: 13.2, delay: 2.6, opacity: 0.15 },
  { size: 2.8, left: 75.9, top: 25.4, duration: 16.3, delay: 0.5, opacity: 0.20 },
  { size: 1.7, left: 33.6, top: 86.1, duration: 12.6, delay: 2.0, opacity: 0.12 },
  { size: 2.0, left: 48.3, top: 50.8, duration: 15.0, delay: 1.1, opacity: 0.18 },
];

export function ParticleBackground() {
  return (
    <div className="fixed inset-0 pointer-events-none overflow-hidden -z-10">
      {PARTICLE_SEED.map((p, i) => (
        <motion.div
          key={i}
          className="absolute rounded-full bg-primary"
          style={{ width: p.size, height: p.size, left: `${p.left}%`, top: `${p.top}%`, opacity: p.opacity }}
          animate={{
            y: [0, -30, 0],
            x: [0, 20, 0],
            opacity: [p.opacity, p.opacity * 1.5, p.opacity],
          }}
          transition={{ duration: p.duration, delay: p.delay, repeat: Infinity, ease: "easeInOut" }}
        />
      ))}
    </div>
  );
}

// ============ Voice Waveform ============
export function VoiceWaveform({ active }: { active: boolean }) {
  const bars = 5;
  return (
    <div className="flex items-end gap-0.5 h-4">
      {[...Array(bars)].map((_, i) => (
        <motion.div
          key={i}
          className="w-0.5 bg-primary rounded-full"
          animate={active ? { height: [4, 12, 4], opacity: [0.5, 1, 0.5] } : { height: 4, opacity: 0.3 }}
          transition={{ duration: 0.8, repeat: active ? Infinity : 0, delay: i * 0.1 }}
          style={{ height: 4 }}
        />
      ))}
    </div>
  );
}
