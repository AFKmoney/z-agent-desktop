"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Cpu, Sparkles, FileText, Zap, Brain, Check, X,
  ChevronRight, Plus, Trash2, Lightbulb,
} from "lucide-react";
import { agentApi } from "@/lib/agent-api";
import { Button } from "@/components/ui/button";

// ============ LLM Provider Switcher ============
export function LLMProviderSwitcher() {
  const [providers, setProviders] = useState<Array<Record<string, unknown>>>([]);
  const [testing, setTesting] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<Record<string, string>>({});

  useEffect(() => {
    const load = async () => {
      try {
        const r = await agentApi.llmProviders();
        setProviders(r.providers || []);
      } catch {}
    };
    load();
    const i = setInterval(load, 30000);
    return () => clearInterval(i);
  }, []);

  const setPrimary = async (id: string) => {
    try {
      await agentApi.llmSetPrimary(id);
      const r = await agentApi.llmProviders();
      setProviders(r.providers || []);
    } catch {}
  };

  const test = async (id: string) => {
    setTesting(id);
    try {
      const r = await agentApi.llmTest(id);
      setTestResult(prev => ({
        ...prev,
        [id]: r.success ? `✓ ${r.response || "OK"} (${r.elapsed_s}s)` : `✗ ${r.error}`,
      }));
    } catch (e) {
      setTestResult(prev => ({ ...prev, [id]: `✗ ${e}` }));
    }
    setTesting(null);
  };

  return (
    <div>
      <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3 flex items-center gap-2">
        <Cpu className="w-3.5 h-3.5" />
        LLM Providers
      </h4>
      <div className="space-y-1.5 max-h-64 overflow-y-auto pr-1">
        {providers.length === 0 ? (
          <p className="text-xs text-muted-foreground text-center py-3">No providers configured</p>
        ) : (
          providers.map((p, i) => {
            const id = String(p.id);
            const available = Boolean(p.available);
            const isPrimary = Boolean(p.is_primary);
            return (
              <motion.div
                key={id}
                className={`glass rounded-lg p-2 ${isPrimary ? "border-primary/50 bg-primary/5" : ""}`}
                initial={{ opacity: 0, x: -5 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.03 }}
              >
                <div className="flex items-center gap-2">
                  <div className={`w-1.5 h-1.5 rounded-full ${available ? "bg-emerald-500" : "bg-zinc-600"}`} />
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-medium truncate">{String(p.name)}</div>
                    <div className="text-[9px] text-muted-foreground font-mono truncate">
                      {String(p.default_model)}
                    </div>
                  </div>
                  {isPrimary && (
                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-primary/20 text-primary border border-primary/30 font-mono uppercase">
                      Primary
                    </span>
                  )}
                </div>
                <div className="flex gap-1 mt-1.5">
                  {available && !isPrimary && (
                    <button
                      onClick={() => setPrimary(id)}
                      className="text-[9px] px-1.5 py-0.5 rounded bg-muted/40 hover:bg-primary/20 hover:text-primary transition-all"
                    >
                      Set primary
                    </button>
                  )}
                  {available && (
                    <button
                      onClick={() => test(id)}
                      disabled={testing === id}
                      className="text-[9px] px-1.5 py-0.5 rounded bg-muted/40 hover:bg-accent/40 transition-all"
                    >
                      {testing === id ? "Testing..." : "Test"}
                    </button>
                  )}
                </div>
                {testResult[id] && (
                  <div className={`text-[9px] mt-1 font-mono ${testResult[id].startsWith("✓") ? "text-emerald-400" : "text-red-400"}`}>
                    {testResult[id]}
                  </div>
                )}
              </motion.div>
            );
          })
        )}
      </div>
    </div>
  );
}

// ============ Smart Suggestions ============
export function SmartSuggestionsPanel({
  currentRequest,
  onPick,
}: {
  currentRequest: string;
  onPick: (suggestion: string) => void;
}) {
  const [suggestions, setSuggestions] = useState<Array<Record<string, unknown>>>([]);

  useEffect(() => {
    const load = async () => {
      try {
        const r = await agentApi.suggestions(currentRequest || undefined, 5);
        setSuggestions(r.suggestions || []);
      } catch {}
    };
    load();
    const i = setInterval(load, 10000);
    return () => clearInterval(i);
  }, [currentRequest]);

  if (suggestions.length === 0) return null;

  return (
    <div className="mb-2">
      <div className="text-[9px] text-muted-foreground uppercase tracking-wider mb-1 flex items-center gap-1">
        <Lightbulb className="w-2.5 h-2.5" />
        Suggestions
      </div>
      <div className="flex flex-wrap gap-1">
        {suggestions.map((s, i) => (
          <motion.button
            key={i}
            onClick={() => onPick(String(s.text))}
            className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 hover:bg-amber-500/20 transition-all"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: i * 0.05 }}
            title={String(s.reason || "")}
          >
            {String(s.text).slice(0, 40)}
            {String(s.text).length > 40 && "..."}
          </motion.button>
        ))}
      </div>
    </div>
  );
}

// ============ Prompt Templates Panel ============
export function PromptTemplatesPanel({
  onUse,
}: {
  onUse: (template: string) => void;
}) {
  const [templates, setTemplates] = useState<Array<Record<string, unknown>>>([]);
  const [category, setCategory] = useState<string | undefined>(undefined);
  const [showCreate, setShowCreate] = useState(false);
  const [newTpl, setNewTpl] = useState({ name: "", template: "", category: "general" });

  const load = async () => {
    try {
      const r = await agentApi.templatesList({ category });
      setTemplates(r.templates || []);
    } catch {}
  };

  useEffect(() => {
    let cancelled = false;
    const doLoad = async () => {
      await load();
      if (cancelled) return;
    };
    doLoad();
    return () => { cancelled = true; };
  }, [category]);

  const create = async () => {
    if (!newTpl.name || !newTpl.template) return;
    try {
      await agentApi.templatesCreate(newTpl);
      setNewTpl({ name: "", template: "", category: "general" });
      setShowCreate(false);
      load();
    } catch {}
  };

  const remove = async (id: string) => {
    try {
      await agentApi.templatesDelete(id);
      load();
    } catch {}
  };

  const categories = ["", "general", "documents", "files", "email", "work", "development", "research"];

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
          <FileText className="w-3.5 h-3.5" />
          Prompt Templates
        </h4>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="text-[10px] px-1.5 py-0.5 rounded bg-primary/15 text-primary border border-primary/30 hover:bg-primary/25 transition-all flex items-center gap-1"
        >
          <Plus className="w-2.5 h-2.5" />
          New
        </button>
      </div>

      {/* Category filter */}
      <div className="flex gap-1 mb-2 overflow-x-auto no-scrollbar">
        {categories.map(c => (
          <button
            key={c}
            onClick={() => setCategory(c || undefined)}
            className={`text-[9px] px-1.5 py-0.5 rounded font-mono uppercase whitespace-nowrap transition-all ${
              category === (c || undefined)
                ? "bg-primary/20 text-primary border border-primary/40"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {c || "All"}
          </button>
        ))}
      </div>

      <AnimatePresence>
        {showCreate && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden mb-3"
          >
            <div className="glass rounded-lg p-3 space-y-2">
              <input
                placeholder="Template name"
                value={newTpl.name}
                onChange={e => setNewTpl({ ...newTpl, name: e.target.value })}
                className="w-full bg-background/50 rounded px-2 py-1 text-xs outline-none border border-border/50 focus:border-primary/50"
              />
              <textarea
                placeholder="Template with {variables}..."
                value={newTpl.template}
                onChange={e => setNewTpl({ ...newTpl, template: e.target.value })}
                rows={2}
                className="w-full bg-background/50 rounded px-2 py-1 text-xs outline-none border border-border/50 focus:border-primary/50 resize-none"
              />
              <div className="flex gap-2">
                <select
                  value={newTpl.category}
                  onChange={e => setNewTpl({ ...newTpl, category: e.target.value })}
                  className="bg-background/50 rounded px-2 py-1 text-xs outline-none border border-border/50"
                >
                  {categories.slice(1).map(c => <option key={c} value={c}>{c}</option>)}
                </select>
                <button
                  onClick={create}
                  className="flex-1 bg-primary/20 text-primary border border-primary/40 rounded py-1 text-xs hover:bg-primary/30"
                >
                  Create
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="space-y-1.5 max-h-64 overflow-y-auto pr-1">
        {templates.length === 0 ? (
          <p className="text-xs text-muted-foreground text-center py-3">No templates</p>
        ) : (
          templates.map((t, i) => {
            const id = String(t.id);
            const isBuiltin = id.startsWith("builtin_");
            const variables = (t.variables as string[]) || [];
            return (
              <motion.div
                key={id}
                className="glass rounded-lg p-2"
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.02 }}
              >
                <div className="flex items-center gap-2">
                  <FileText className="w-3 h-3 text-primary flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="text-xs truncate">{String(t.name)}</div>
                    <div className="text-[9px] text-muted-foreground truncate">
                      {String(t.description || "")}
                    </div>
                  </div>
                  {isBuiltin && (
                    <span className="text-[8px] px-1 py-0.5 rounded bg-muted/40 font-mono uppercase">Built-in</span>
                  )}
                </div>
                {variables.length > 0 && (
                  <div className="flex flex-wrap gap-0.5 mt-1">
                    {variables.map(v => (
                      <span key={v} className="text-[8px] px-1 py-0.5 rounded bg-cyan-500/10 text-cyan-400 font-mono">
                        {`{${v}}`}
                      </span>
                    ))}
                  </div>
                )}
                <div className="flex gap-1 mt-1.5">
                  <button
                    onClick={() => onUse(String(t.template))}
                    className="text-[9px] px-1.5 py-0.5 rounded bg-primary/15 text-primary hover:bg-primary/25 transition-all"
                  >
                    Use
                  </button>
                  {!isBuiltin && (
                    <button
                      onClick={() => remove(id)}
                      className="text-[9px] px-1.5 py-0.5 rounded bg-muted/40 hover:bg-red-500/20 hover:text-red-400 transition-all"
                    >
                      <Trash2 className="w-2.5 h-2.5" />
                    </button>
                  )}
                </div>
              </motion.div>
            );
          })
        )}
      </div>
    </div>
  );
}

// ============ Backup Panel ============
export function BackupPanel() {
  const [backups, setBackups] = useState<Array<Record<string, unknown>>>([]);
  const [creating, setCreating] = useState(false);

  const load = async () => {
    try {
      const r = await agentApi.backupsList();
      setBackups(r.backups || []);
    } catch {}
  };

  useEffect(() => {
    let cancelled = false;
    const doLoad = async () => {
      await load();
      if (cancelled) return;
    };
    doLoad();
    return () => { cancelled = true; };
  }, []);

  const create = async () => {
    setCreating(true);
    try {
      await agentApi.backupCreate();
      load();
    } catch {}
    setCreating(false);
  };

  const remove = async (name: string) => {
    try {
      await agentApi.backupsDelete(name);
      load();
    } catch {}
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
          <Sparkles className="w-3.5 h-3.5" />
          Backups
        </h4>
        <button
          onClick={create}
          disabled={creating}
          className="text-[10px] px-1.5 py-0.5 rounded bg-primary/15 text-primary border border-primary/30 hover:bg-primary/25 transition-all flex items-center gap-1"
        >
          <Plus className="w-2.5 h-2.5" />
          {creating ? "Creating..." : "New"}
        </button>
      </div>
      <div className="space-y-1.5 max-h-40 overflow-y-auto pr-1">
        {backups.length === 0 ? (
          <p className="text-xs text-muted-foreground text-center py-3">No backups yet</p>
        ) : (
          backups.map((b, i) => (
            <motion.div
              key={i}
              className="glass rounded-lg p-2 flex items-center gap-2"
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <div className="flex-1 min-w-0">
                <div className="text-[10px] truncate font-mono">{String(b.name)}</div>
                <div className="text-[9px] text-muted-foreground">
                  {String(b.created_at_human || "")} · {String(b.size_kb || "0")} KB
                </div>
              </div>
              <button
                onClick={() => remove(String(b.name))}
                className="text-muted-foreground hover:text-red-400 transition-colors"
              >
                <Trash2 className="w-3 h-3" />
              </button>
            </motion.div>
          ))
        )}
      </div>
    </div>
  );
}
