"use client";

import { useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Bot, Plus, Trash2, Save, X, Copy, Edit, Sparkles,
} from "lucide-react";
import { agentApi } from "@/lib/agent-api";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
// Multi-language helper
function L(lang: string, texts: Record<string, string>): string {
  return texts[lang] || texts.en;
}

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
                    ? (editing ? (L(lang, { en: "Edit Agent", fr: "Modifier l'agent", es: "Edit Agent", de: "Edit Agent", pt: "Edit Agent" })) : (L(lang, { en: "Create Agent", fr: "Créer un agent", es: "Create Agent", de: "Create Agent", pt: "Create Agent" })))
                    : (L(lang, { en: "Custom Agents", fr: "Agents personnalisés", es: "Custom Agents", de: "Custom Agents", pt: "Custom Agents" }))}
                </h2>
                <p className="text-xs text-muted-foreground">
                  {showEditor
                    ? (L(lang, { en: "Configure parameters", fr: "Configurez les paramètres", es: "Configure parameters", de: "Configure parameters", pt: "Configure parameters" }))
                    : `${agents.length} ${L(lang, { en: "agents", fr: "agents", es: "agents", de: "agents", pt: "agents" })}`}
                </p>
              </div>
            </div>
            <div className="flex gap-2">
              {!showEditor && (
                <Button size="sm" onClick={startNew} className="gap-1.5">
                  <Plus className="w-3.5 h-3.5" />
                  {L(lang, { en: "New", fr: "Nouveau", es: "New", de: "New", pt: "New" })}
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
                    {L(lang, { en: "No agents. Create one!", fr: "Aucun agent. Créez-en un !", es: "No agents. Create one!", de: "No agents. Create one!", pt: "No agents. Create one!" })}
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
                                {L(lang, { en: "Template", fr: "Modèle", es: "Template", de: "Template", pt: "Template" })}
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
                      {L(lang, { en: "Emoji", fr: "Emoji", es: "Emoji", de: "Emoji", pt: "Emoji" })}
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
                      {L(lang, { en: "Color", fr: "Couleur", es: "Color", de: "Color", pt: "Color" })}
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
                    {L(lang, { en: "Name", fr: "Nom", es: "Name", de: "Name", pt: "Name" })} <span className="text-red-400">*</span>
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
                    {L(lang, { en: "Description", fr: "Description", es: "Description", de: "Description", pt: "Description" })}
                  </label>
                  <input
                    value={form.description}
                    onChange={e => setForm(prev => ({ ...prev, description: e.target.value }))}
                    placeholder={L(lang, { en: "Manages my emails", fr: "Gère mes emails", es: "Manages my emails", de: "Manages my emails", pt: "Manages my emails" })}
                    className="w-full bg-background/50 rounded-md px-3 py-2 text-sm outline-none border border-border/50 focus:border-primary/50"
                  />
                </div>

                {/* System Prompt */}
                <div>
                  <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5 block">
                    {L(lang, { en: "System Prompt (persona)", fr: "Prompt système (persona)", es: "System Prompt (persona)", de: "System Prompt (persona)", pt: "System Prompt (persona)" })}
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
                      {L(lang, { en: "LLM Provider", fr: "Fournisseur LLM", es: "LLM Provider", de: "LLM Provider", pt: "LLM Provider" })}
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
                      {L(lang, { en: "Model (empty = default)", fr: "Modèle (vide = défaut)", es: "Model (empty = default)", de: "Model (empty = default)", pt: "Model (empty = default)" })}
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
                      {L(lang, { en: "Temperature", fr: "Température", es: "Temperature", de: "Temperature", pt: "Temperature" })}: {form.temperature}
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
                      {L(lang, { en: "Max tokens", fr: "Max tokens", es: "Max tokens", de: "Max tokens", pt: "Max tokens" })}
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
                      {L(lang, { en: "Memory", fr: "Mémoire", es: "Memory", de: "Memory", pt: "Memory" })}
                    </label>
                    <select
                      value={form.memory_mode}
                      onChange={e => setForm(prev => ({ ...prev, memory_mode: e.target.value }))}
                      className="w-full bg-background/50 rounded-md px-3 py-2 text-sm outline-none border border-border/50"
                    >
                      <option value="none">{L(lang, { en: "None", fr: "Aucune", es: "None", de: "None", pt: "None" })}</option>
                      <option value="conversation">{L(lang, { en: "Conversation", fr: "Conversation", es: "Conversation", de: "Conversation", pt: "Conversation" })}</option>
                      <option value="persistent">{L(lang, { en: "Persistent", fr: "Persistante", es: "Persistent", de: "Persistent", pt: "Persistent" })}</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5 block">
                      {L(lang, { en: "Autonomy", fr: "Autonomie", es: "Autonomy", de: "Autonomy", pt: "Autonomy" })}
                    </label>
                    <select
                      value={form.autonomy_mode}
                      onChange={e => setForm(prev => ({ ...prev, autonomy_mode: e.target.value }))}
                      className="w-full bg-background/50 rounded-md px-3 py-2 text-sm outline-none border border-border/50"
                    >
                      <option value="full">{L(lang, { en: "Full control", fr: "Plein contrôle", es: "Full control", de: "Full control", pt: "Full control" })}</option>
                      <option value="confirmation">{L(lang, { en: "Confirmation required", fr: "Confirmation requise", es: "Confirmation required", de: "Confirmation required", pt: "Confirmation required" })}</option>
                      <option value="readonly">{L(lang, { en: "Read only", fr: "Lecture seule", es: "Read only", de: "Read only", pt: "Read only" })}</option>
                    </select>
                  </div>
                </div>

                {/* Allowed actions */}
                <div>
                  <label className="text-xs font-semibold uppercase tracking-wider text-emerald-400 mb-2 block">
                    {L(lang, { en: "Allowed Actions", fr: "Actions autorisées", es: "Allowed Actions", de: "Allowed Actions", pt: "Allowed Actions" })} ({form.allowed_actions.length})
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
                    {L(lang, { en: "Empty = all actions allowed", fr: "Vide = toutes les actions autorisées", es: "Empty = all actions allowed", de: "Empty = all actions allowed", pt: "Empty = all actions allowed" })}
                  </p>
                </div>

                {/* Blocked actions */}
                <div>
                  <label className="text-xs font-semibold uppercase tracking-wider text-red-400 mb-2 block">
                    {L(lang, { en: "Blocked Actions", fr: "Actions bloquées", es: "Blocked Actions", de: "Blocked Actions", pt: "Blocked Actions" })} ({form.blocked_actions.length})
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
                {L(lang, { en: "Cancel", fr: "Annuler", es: "Cancel", de: "Cancel", pt: "Cancel" })}
              </Button>
              <Button size="sm" onClick={save} disabled={!form.name.trim()} className="gap-1.5">
                <Save className="w-3.5 h-3.5" />
                {editing ? (L(lang, { en: "Update", fr: "Mettre à jour", es: "Update", de: "Update", pt: "Update" })) : (L(lang, { en: "Create", fr: "Créer", es: "Create", de: "Create", pt: "Create" }))}
              </Button>
            </div>
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
