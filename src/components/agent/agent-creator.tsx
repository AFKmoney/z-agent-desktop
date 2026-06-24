"use client";

import { useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Bot, Plus, Trash2, Save, X, Copy, Edit, Sparkles,
} from "lucide-react";
import { agentApi } from "@/lib/agent-api";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const EMOJI_OPTIONS = ["🤖", "📧", "🔍", "📚", "📁", "⚙️", "🌐", "💻", "🎨", "📊", "🔬", "🎬", "🎮", "💡", "🚀", "⚡"];
const COLOR_OPTIONS = [
  "#10B981", "#06B6D4", "#8B5CF6", "#EC4899",
  "#F59E0B", "#3B82F6", "#EF4444", "#14B8A6",
  "#F97316", "#A855F7", "#22C55E", "#6366F1",
];

const ACTION_PREFIXES = [
  { id: "screen.", label: "Screen Control", desc: "Cursor, keyboard, screenshots" },
  { id: "files.", label: "File Manager", desc: "Organize, move, read, write files" },
  { id: "email.", label: "Email", desc: "Read, send, reply to emails" },
  { id: "calendar.", label: "Calendar", desc: "Events, reminders" },
  { id: "browser.", label: "Browser", desc: "Open, click, fill, extract" },
  { id: "system.", label: "System", desc: "Apps, processes, clipboard" },
  { id: "windows.", label: "Windows", desc: "Registry, services, COM, PowerShell" },
  { id: "code.", label: "Code Interpreter", desc: "Run Python in sandbox" },
  { id: "web.", label: "Web Search", desc: "Search and read web pages" },
  { id: "voice.", label: "Voice Control", desc: "Transcribe, TTS" },
  { id: "vision.", label: "Vision Stream", desc: "Screen monitoring" },
  { id: "kb.", label: "Knowledge Base", desc: "RAG document search" },
  { id: "plugin.", label: "Plugin Manager", desc: "Install/uninstall plugins" },
  { id: "mcp.", label: "MCP Client", desc: "External tool servers" },
  { id: "slack.", label: "Slack", desc: "Slack messages and files" },
];

export function AgentCreatorModal({
  open,
  onClose,
  lang,
}: {
  open: boolean;
  onClose: () => void;
  lang: "en" | "fr";
}) {
  const [agents, setAgents] = useState<Array<Record<string, unknown>>>([]);
  const [editing, setEditing] = useState<Record<string, unknown> | null>(null);
  const [showEditor, setShowEditor] = useState(false);

  // Form state
  const [form, setForm] = useState({
    name: "",
    description: "",
    system_prompt: "",
    provider: "zai",
    model: "",
    temperature: 0.3,
    max_tokens: 4096,
    allowed_actions: [] as string[],
    blocked_actions: [] as string[],
    memory_mode: "conversation",
    autonomy_mode: "full",
    color: "#10B981",
    emoji: "🤖",
  });

  const load = useCallback(async () => {
    try {
      const r = await agentApi.agentsList();
      setAgents(r.agents || []);
    } catch {}
  }, []);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    const doLoad = async () => {
      await load();
      if (cancelled) return;
    };
    doLoad();
    return () => { cancelled = true; };
  }, [open, load]);

  const startNew = () => {
    setForm({
      name: "",
      description: "",
      system_prompt: "",
      provider: "zai",
      model: "",
      temperature: 0.3,
      max_tokens: 4096,
      allowed_actions: [],
      blocked_actions: [],
      memory_mode: "conversation",
      autonomy_mode: "full",
      color: COLOR_OPTIONS[Math.floor(Math.random() * COLOR_OPTIONS.length)],
      emoji: "🤖",
    });
    setEditing(null);
    setShowEditor(true);
  };

  const startEdit = (agent: Record<string, unknown>) => {
    setForm({
      name: String(agent.name || ""),
      description: String(agent.description || ""),
      system_prompt: String(agent.system_prompt || ""),
      provider: String(agent.provider || "zai"),
      model: String(agent.model || ""),
      temperature: Number(agent.temperature || 0.3),
      max_tokens: Number(agent.max_tokens || 4096),
      allowed_actions: (agent.allowed_actions as string[]) || [],
      blocked_actions: (agent.blocked_actions as string[]) || [],
      memory_mode: String(agent.memory_mode || "conversation"),
      autonomy_mode: String(agent.autonomy_mode || "full"),
      color: String(agent.color || "#10B981"),
      emoji: String(agent.emoji || "🤖"),
    });
    setEditing(agent);
    setShowEditor(true);
  };

  const save = async () => {
    if (!form.name.trim()) return;
    try {
      if (editing) {
        await agentApi.agentsUpdate(String(editing.id), form);
      } else {
        await agentApi.agentsCreate(form);
      }
      setShowEditor(false);
      load();
    } catch {}
  };

  const remove = async (id: string) => {
    try {
      await agentApi.agentsDelete(id);
      load();
    } catch {}
  };

  const toggleAction = (list: "allowed_actions" | "blocked_actions", prefix: string) => {
    setForm(prev => {
      const current = prev[list];
      if (current.includes(prefix)) {
        return { ...prev, [list]: current.filter(a => a !== prefix) };
      }
      return { ...prev, [list]: [...current, prefix] };
    });
  };

  if (!open) return null;

  return (
    <AnimatePresence>
      <motion.div
        className="fixed inset-0 z-50 flex items-center justify-center p-4"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
      >
        <div className="absolute inset-0 bg-black/70 backdrop-blur-md" onClick={onClose} />

        <motion.div
          className="glass-strong rounded-2xl w-full max-w-3xl max-h-[90vh] flex flex-col glow-primary"
          initial={{ scale: 0.95, y: 20 }}
          animate={{ scale: 1, y: 0 }}
          exit={{ scale: 0.95, y: 20 }}
          transition={{ type: "spring", damping: 25 }}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-5 border-b border-border/50">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-primary/15 border border-primary/30 flex items-center justify-center">
                <Bot className="w-5 h-5 text-primary" />
              </div>
              <div>
                <h2 className="text-base font-bold">
                  {showEditor
                    ? (editing ? (lang === "fr" ? "Modifier l'agent" : "Edit Agent") : (lang === "fr" ? "Créer un agent" : "Create Agent"))
                    : (lang === "fr" ? "Agents personnalisés" : "Custom Agents")}
                </h2>
                <p className="text-xs text-muted-foreground">
                  {showEditor
                    ? (lang === "fr" ? "Configurez les paramètres" : "Configure parameters")
                    : `${agents.length} ${lang === "fr" ? "agents" : "agents"}`}
                </p>
              </div>
            </div>
            <div className="flex gap-2">
              {!showEditor && (
                <Button size="sm" onClick={startNew} className="gap-1.5">
                  <Plus className="w-3.5 h-3.5" />
                  {lang === "fr" ? "Nouveau" : "New"}
                </Button>
              )}
              <button
                onClick={() => { setShowEditor(false); onClose(); }}
                className="w-8 h-8 rounded-lg hover:bg-accent/30 flex items-center justify-center transition-colors text-muted-foreground"
              >
                ✕
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-5">
            {!showEditor ? (
              /* Agent list */
              <div className="space-y-2">
                {agents.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-8">
                    {lang === "fr" ? "Aucun agent. Créez-en un !" : "No agents. Create one!"}
                  </p>
                ) : (
                  agents.map((agent, i) => {
                    const isTemplate = String(agent.id).startsWith("template_");
                    const allowedCount = (agent.allowed_actions as string[])?.length || 0;
                    const blockedCount = (agent.blocked_actions as string[])?.length || 0;
                    return (
                      <motion.div
                        key={String(agent.id)}
                        className="glass rounded-xl p-4 flex items-center gap-3"
                        initial={{ opacity: 0, y: 5 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.03 }}
                      >
                        <div
                          className="w-12 h-12 rounded-xl flex items-center justify-center text-xl flex-shrink-0"
                          style={{ background: `${String(agent.color)}20`, border: `1px solid ${String(agent.color)}40` }}
                        >
                          {String(agent.emoji)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium truncate">{String(agent.name)}</span>
                            {isTemplate && (
                              <span className="text-[9px] px-1 py-0.5 rounded bg-muted/40 font-mono uppercase">
                                {lang === "fr" ? "Modèle" : "Template"}
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-muted-foreground truncate">
                            {String(agent.description || "")}
                          </p>
                          <div className="flex gap-2 mt-1 text-[9px] text-muted-foreground font-mono">
                            <span className="text-emerald-400">{allowedCount} allowed</span>
                            <span className="text-red-400">{blockedCount} blocked</span>
                            <span>{String(agent.autonomy_mode)}</span>
                          </div>
                        </div>
                        <div className="flex gap-1 flex-shrink-0">
                          <button
                            onClick={() => startEdit(agent)}
                            className="w-7 h-7 rounded-lg hover:bg-accent/30 flex items-center justify-center text-muted-foreground hover:text-primary transition-all"
                          >
                            <Edit className="w-3.5 h-3.5" />
                          </button>
                          {!isTemplate && (
                            <button
                              onClick={() => remove(String(agent.id))}
                              className="w-7 h-7 rounded-lg hover:bg-red-500/20 flex items-center justify-center text-muted-foreground hover:text-red-400 transition-all"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>
                      </motion.div>
                    );
                  })
                )}
              </div>
            ) : (
              /* Editor */
              <div className="space-y-4">
                {/* Emoji + Color */}
                <div className="flex gap-4">
                  <div className="flex-1">
                    <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2 block">
                      {lang === "fr" ? "Emoji" : "Emoji"}
                    </label>
                    <div className="flex flex-wrap gap-1.5">
                      {EMOJI_OPTIONS.map(e => (
                        <button
                          key={e}
                          onClick={() => setForm(prev => ({ ...prev, emoji: e }))}
                          className={cn(
                            "w-8 h-8 rounded-lg flex items-center justify-center text-lg transition-all",
                            form.emoji === e ? "bg-primary/20 border border-primary/40" : "bg-muted/30 hover:bg-muted/50"
                          )}
                        >
                          {e}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div className="flex-1">
                    <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2 block">
                      {lang === "fr" ? "Couleur" : "Color"}
                    </label>
                    <div className="flex flex-wrap gap-1.5">
                      {COLOR_OPTIONS.map(c => (
                        <button
                          key={c}
                          onClick={() => setForm(prev => ({ ...prev, color: c }))}
                          className={cn(
                            "w-8 h-8 rounded-lg transition-all",
                            form.color === c ? "ring-2 ring-offset-2 ring-offset-background" : ""
                          )}
                          style={{ background: c, boxShadow: form.color === c ? `0 0 12px ${c}` : "none" }}
                        />
                      ))}
                    </div>
                  </div>
                </div>

                {/* Name */}
                <div>
                  <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5 block">
                    {lang === "fr" ? "Nom" : "Name"} <span className="text-red-400">*</span>
                  </label>
                  <input
                    value={form.name}
                    onChange={e => setForm(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="Email Assistant"
                    className="w-full bg-background/50 rounded-md px-3 py-2 text-sm outline-none border border-border/50 focus:border-primary/50"
                  />
                </div>

                {/* Description */}
                <div>
                  <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5 block">
                    {lang === "fr" ? "Description" : "Description"}
                  </label>
                  <input
                    value={form.description}
                    onChange={e => setForm(prev => ({ ...prev, description: e.target.value }))}
                    placeholder={lang === "fr" ? "Gère mes emails" : "Manages my emails"}
                    className="w-full bg-background/50 rounded-md px-3 py-2 text-sm outline-none border border-border/50 focus:border-primary/50"
                  />
                </div>

                {/* System Prompt */}
                <div>
                  <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5 block">
                    {lang === "fr" ? "Prompt système (persona)" : "System Prompt (persona)"}
                  </label>
                  <textarea
                    value={form.system_prompt}
                    onChange={e => setForm(prev => ({ ...prev, system_prompt: e.target.value }))}
                    placeholder="You are a helpful email assistant. Be concise and professional..."
                    rows={3}
                    className="w-full bg-background/50 rounded-md px-3 py-2 text-sm outline-none border border-border/50 focus:border-primary/50 resize-none"
                  />
                </div>

                {/* Provider + Model */}
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5 block">
                      {lang === "fr" ? "Fournisseur LLM" : "LLM Provider"}
                    </label>
                    <select
                      value={form.provider}
                      onChange={e => setForm(prev => ({ ...prev, provider: e.target.value }))}
                      className="w-full bg-background/50 rounded-md px-3 py-2 text-sm outline-none border border-border/50"
                    >
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
                    <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5 block">
                      {lang === "fr" ? "Modèle (vide = défaut)" : "Model (empty = default)"}
                    </label>
                    <input
                      value={form.model}
                      onChange={e => setForm(prev => ({ ...prev, model: e.target.value }))}
                      placeholder="glm-4.6"
                      className="w-full bg-background/50 rounded-md px-3 py-2 text-sm font-mono outline-none border border-border/50 focus:border-primary/50"
                    />
                  </div>
                </div>

                {/* Temperature + Max tokens */}
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5 block">
                      {lang === "fr" ? "Température" : "Temperature"}: {form.temperature}
                    </label>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.1"
                      value={form.temperature}
                      onChange={e => setForm(prev => ({ ...prev, temperature: Number(e.target.value) }))}
                      className="w-full accent-primary"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5 block">
                      {lang === "fr" ? "Max tokens" : "Max tokens"}
                    </label>
                    <input
                      type="number"
                      value={form.max_tokens}
                      onChange={e => setForm(prev => ({ ...prev, max_tokens: Number(e.target.value) }))}
                      className="w-full bg-background/50 rounded-md px-3 py-2 text-sm font-mono outline-none border border-border/50 focus:border-primary/50"
                    />
                  </div>
                </div>

                {/* Memory + Autonomy */}
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5 block">
                      {lang === "fr" ? "Mémoire" : "Memory"}
                    </label>
                    <select
                      value={form.memory_mode}
                      onChange={e => setForm(prev => ({ ...prev, memory_mode: e.target.value }))}
                      className="w-full bg-background/50 rounded-md px-3 py-2 text-sm outline-none border border-border/50"
                    >
                      <option value="none">{lang === "fr" ? "Aucune" : "None"}</option>
                      <option value="conversation">{lang === "fr" ? "Conversation" : "Conversation"}</option>
                      <option value="persistent">{lang === "fr" ? "Persistante" : "Persistent"}</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5 block">
                      {lang === "fr" ? "Autonomie" : "Autonomy"}
                    </label>
                    <select
                      value={form.autonomy_mode}
                      onChange={e => setForm(prev => ({ ...prev, autonomy_mode: e.target.value }))}
                      className="w-full bg-background/50 rounded-md px-3 py-2 text-sm outline-none border border-border/50"
                    >
                      <option value="full">{lang === "fr" ? "Plein contrôle" : "Full control"}</option>
                      <option value="confirmation">{lang === "fr" ? "Confirmation requise" : "Confirmation required"}</option>
                      <option value="readonly">{lang === "fr" ? "Lecture seule" : "Read only"}</option>
                    </select>
                  </div>
                </div>

                {/* Allowed actions */}
                <div>
                  <label className="text-xs font-semibold uppercase tracking-wider text-emerald-400 mb-2 block">
                    {lang === "fr" ? "Actions autorisées" : "Allowed Actions"} ({form.allowed_actions.length})
                  </label>
                  <div className="flex flex-wrap gap-1.5">
                    {ACTION_PREFIXES.map(a => {
                      const active = form.allowed_actions.includes(a.id);
                      return (
                        <button
                          key={a.id}
                          onClick={() => toggleAction("allowed_actions", a.id)}
                          className={cn(
                            "px-2 py-1 rounded-md text-[10px] border transition-all",
                            active
                              ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/40"
                              : "bg-muted/30 text-muted-foreground border-border/50 hover:bg-muted/50"
                          )}
                          title={a.desc}
                        >
                          {a.label}
                        </button>
                      );
                    })}
                  </div>
                  <p className="text-[9px] text-muted-foreground mt-1">
                    {lang === "fr"
                      ? "Vide = toutes les actions autorisées"
                      : "Empty = all actions allowed"}
                  </p>
                </div>

                {/* Blocked actions */}
                <div>
                  <label className="text-xs font-semibold uppercase tracking-wider text-red-400 mb-2 block">
                    {lang === "fr" ? "Actions bloquées" : "Blocked Actions"} ({form.blocked_actions.length})
                  </label>
                  <div className="flex flex-wrap gap-1.5">
                    {ACTION_PREFIXES.map(a => {
                      const active = form.blocked_actions.includes(a.id);
                      return (
                        <button
                          key={a.id}
                          onClick={() => toggleAction("blocked_actions", a.id)}
                          className={cn(
                            "px-2 py-1 rounded-md text-[10px] border transition-all",
                            active
                              ? "bg-red-500/20 text-red-400 border-red-500/40"
                              : "bg-muted/30 text-muted-foreground border-border/50 hover:bg-muted/50"
                          )}
                          title={a.desc}
                        >
                          {a.label}
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Footer */}
          {showEditor && (
            <div className="p-5 border-t border-border/50 flex justify-end gap-2">
              <Button size="sm" variant="ghost" onClick={() => setShowEditor(false)}>
                {lang === "fr" ? "Annuler" : "Cancel"}
              </Button>
              <Button size="sm" onClick={save} disabled={!form.name.trim()} className="gap-1.5">
                <Save className="w-3.5 h-3.5" />
                {editing ? (lang === "fr" ? "Mettre à jour" : "Update") : (lang === "fr" ? "Créer" : "Create")}
              </Button>
            </div>
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
