"use client";

import { useEffect, useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  X, Eye, EyeOff, Check, AlertCircle, Loader2, Save,
  Trash2, Zap, RefreshCw, Settings as SettingsIcon,
} from "lucide-react";
import { agentApi } from "@/lib/agent-api";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
// Multi-language helper
function L(lang: string, texts: Record<string, string>): string {
  return texts[lang] || texts.en;
}

interface EnvVar {
  key: string;
  label: string;
  description: string;
  category: string;
  required: boolean;
  sensitive: boolean;
  placeholder: string;
  value: string;
  is_set: boolean;
  is_from_file: boolean;
  is_from_env: boolean;
}

interface TestResult {
  [key: string]: { success: boolean; message: string; loading: boolean };
}

export function SettingsModal({
  open,
  onClose,
  lang,
}: {
  open: boolean;
  onClose: () => void;
  lang: "en" | "fr";
}) {
  const [variables, setVariables] = useState<EnvVar[]>([]);
  const [categories, setCategories] = useState<Array<Record<string, unknown>>>([]);
  const [status, setStatus] = useState<Record<string, unknown>>({});
  const [editValues, setEditValues] = useState<Record<string, string>>({});
  const [showValues, setShowValues] = useState<Record<string, boolean>>({});
  const [testResults, setTestResults] = useState<TestResult>({});
  const [saving, setSaving] = useState(false);
  const [savedMessage, setSavedMessage] = useState("");

  const load = async () => {
    try {
      const [listRes, statusRes] = await Promise.all([
        agentApi.envList(),
        agentApi.envStatus(),
      ]);
      setVariables(listRes.variables as EnvVar[]);
      setCategories(listRes.categories);
      setStatus(statusRes);
      // Initialize edit values from current values (only if set from file)
      const initial: Record<string, string> = {};
      for (const v of listRes.variables as EnvVar[]) {
        // Only pre-fill if the value is set (we get masked values for sensitive ones)
        // For non-sensitive, we get the actual value
        if (v.is_set && !v.sensitive) {
          initial[v.key] = v.value;
        } else if (v.is_set && v.sensitive) {
          // For sensitive values, show empty (user must re-enter to change)
          initial[v.key] = "";
        } else {
          initial[v.key] = "";
        }
      }
      setEditValues(initial);
    } catch (e) {
      // Agent offline
    }
  };

  useEffect(() => {
    if (open) {
      load();
      setSavedMessage("");
      setTestResults({});
    }
  }, [open]);

  // Group variables by category
  const grouped = useMemo(() => {
    const g: Record<string, EnvVar[]> = {};
    for (const v of variables) {
      if (!g[v.category]) g[v.category] = [];
      g[v.category].push(v);
    }
    return g;
  }, [variables]);

  const dirty = useMemo(() => {
    return variables.some(v => {
      const editVal = editValues[v.key] || "";
      // For sensitive values that are set, dirty only if user typed something new
      if (v.sensitive && v.is_set) {
        return editVal.length > 0;
      }
      // For non-sensitive, compare
      const currentVal = v.is_set ? v.value : "";
      return editVal !== currentVal;
    });
  }, [variables, editValues]);

  const saveAll = async () => {
    setSaving(true);
    try {
      // Build updates — only changed values
      const updates: Record<string, string> = {};
      for (const v of variables) {
        const editVal = editValues[v.key] || "";
        if (v.sensitive && v.is_set) {
          // Only update if user typed a new value
          if (editVal.length > 0) {
            updates[v.key] = editVal;
          }
        } else {
          const currentVal = v.is_set ? v.value : "";
          if (editVal !== currentVal) {
            if (editVal) {
              updates[v.key] = editVal;
            }
            // If clearing, we need to explicitly delete
          }
        }
      }

      if (Object.keys(updates).length === 0) {
        setSavedMessage(L(lang, { en: "No changes", fr: "Aucun changement", es: "No changes", de: "No changes", pt: "No changes" }));
        setSaving(false);
        return;
      }

      const result = await agentApi.envBatchSet(updates);
      if (result.success) {
        setSavedMessage(
          L(lang, { en: `✅ ${result.count} variables updated. Restart the agent.`, fr: `✅ ${result.count} variables mises à jour. Redémarrez l'agent.`, es: `✅ ${result.count} variables actualizadas. Reinicia el agente.`, de: `✅ ${result.count} Variablen aktualisiert. Agent neu starten.`, pt: `✅ ${result.count} variáveis atualizadas. Reinicie o agente.` })
        );
        // Reload to show new state
        setTimeout(load, 500);
      } else {
        setSavedMessage(
          L(lang, { en: "❌ Error saving", fr: "❌ Erreur lors de la sauvegarde", es: "❌ Error saving", de: "❌ Error saving", pt: "❌ Error saving" })
        );
      }
    } catch (e) {
      setSavedMessage(`❌ ${e instanceof Error ? e.message : "Error"}`);
    }
    setSaving(false);
  };

  const clearVar = async (key: string) => {
    try {
      await agentApi.envDelete(key);
      setEditValues(prev => ({ ...prev, [key]: "" }));
      setSavedMessage(
        L(lang, { en: `✅ ${key} cleared. Restart the agent.`, fr: `✅ ${key} supprimé. Redémarrez l'agent.`, es: `✅ ${key} eliminado. Reinicia el agente.`, de: `✅ ${key} gelöscht. Agent neu starten.`, pt: `✅ ${key} removido. Reinicie o agente.` })
      );
      setTimeout(load, 500);
    } catch {}
  };

  const testVar = async (key: string) => {
    setTestResults(prev => ({ ...prev, [key]: { success: false, message: "", loading: true } }));
    try {
      const result = await agentApi.envTest(key);
      setTestResults(prev => ({
        ...prev,
        [key]: {
          success: result.success as boolean,
          message: (result.message as string) || (result.error as string) || "",
          loading: false,
        },
      }));
    } catch (e) {
      setTestResults(prev => ({
        ...prev,
        [key]: { success: false, message: String(e), loading: false },
      }));
    }
  };

  const toggleShow = (key: string) => {
    setShowValues(prev => ({ ...prev, [key]: !prev[key] }));
  };

  if (!open) return null;

  const requiredMissing = (status.required_missing as string[]) || [];
  const envFileExists = status.env_file_exists as boolean;

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
          className="glass-strong rounded-2xl w-full max-w-4xl max-h-[90vh] flex flex-col glow-primary"
          initial={{ scale: 0.95, y: 20 }}
          animate={{ scale: 1, y: 0 }}
          exit={{ scale: 0.95, y: 20 }}
          transition={{ type: "spring", damping: 25 }}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-5 border-b border-border/50">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-primary/15 border border-primary/30 flex items-center justify-center">
                <SettingsIcon className="w-5 h-5 text-primary" />
              </div>
              <div>
                <h2 className="text-base font-bold">
                  {L(lang, { en: "Settings", fr: "Paramètres", es: "Settings", de: "Settings", pt: "Settings" })}
                </h2>
                <p className="text-xs text-muted-foreground">
                  {L(lang, { en: "Configure your API keys and tokens directly", fr: "Configurez vos clés API et tokens directement", es: "Configure your API keys and tokens directly", de: "Configure your API keys and tokens directly", pt: "Configure your API keys and tokens directly" })}
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-lg hover:bg-accent/30 flex items-center justify-center transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Status bar */}
          <div className="px-5 py-3 border-b border-border/50 flex items-center gap-4 text-xs">
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground">
                {L(lang, { en: "Configured:", fr: "Configuré:", es: "Configured:", de: "Configured:", pt: "Configured:" })}
              </span>
              <span className="font-mono text-emerald-400">
                {String(status.set || 0)}/{String(status.total || 0)}
              </span>
            </div>
            {requiredMissing.length > 0 && (
              <div className="flex items-center gap-1.5 text-amber-400">
                <AlertCircle className="w-3 h-3" />
                <span>
                  {L(lang, { en: `${requiredMissing.length} required missing: ${requiredMissing.join(", ")}`, fr: `${requiredMissing.length} requis manquant(s): ${requiredMissing.join(", ")}`, es: `${requiredMissing.length} requeridos faltantes: ${requiredMissing.join(", ")}`, de: `${requiredMissing.length} erforderlich, fehlen: ${requiredMissing.join(", ")}`, pt: `${requiredMissing.length} obrigatórios faltando: ${requiredMissing.join(", ")}` })}
                </span>
              </div>
            )}
            {!envFileExists && (
              <div className="flex items-center gap-1.5 text-amber-400">
                <AlertCircle className="w-3 h-3" />
                <span>{L(lang, { en: ".env file not found", fr: "Fichier .env introuvable", es: ".env file not found", de: ".env file not found", pt: ".env file not found" })}</span>
              </div>
            )}
          </div>

          {/* Scrollable content */}
          <div className="flex-1 overflow-y-auto p-5 space-y-6">
            {categories.map(cat => {
              const catId = cat.id as string;
              const catLabel = cat.label as string;
              const vars = grouped[catId] || [];
              if (vars.length === 0) return null;

              return (
                <div key={catId}>
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
                    {catLabel}
                  </h3>
                  <div className="space-y-3">
                    {vars.map(v => {
                      const isShown = showValues[v.key];
                      const editVal = editValues[v.key] || "";
                      const isDirty = v.sensitive && v.is_set
                        ? editVal.length > 0
                        : editVal !== (v.is_set ? v.value : "");
                      const testResult = testResults[v.key];

                      return (
                        <div
                          key={v.key}
                          className={cn(
                            "glass rounded-lg p-3 transition-all",
                            v.required && !v.is_set && "border-amber-500/40",
                            isDirty && "border-primary/50 bg-primary/5"
                          )}
                        >
                          <div className="flex items-start justify-between mb-2">
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2">
                                <span className="text-sm font-medium">{v.label}</span>
                                {v.required && (
                                  <span className="text-[9px] px-1 py-0.5 rounded bg-red-500/20 text-red-400 font-mono uppercase">
                                    {L(lang, { en: "Required", fr: "Requis", es: "Required", de: "Required", pt: "Required" })}
                                  </span>
                                )}
                                {v.is_set && (
                                  <span className="flex items-center gap-0.5 text-[9px] px-1 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-mono uppercase">
                                    <Check className="w-2 h-2" />
                                    {L(lang, { en: "Set", fr: "Configuré", es: "Set", de: "Set", pt: "Set" })}
                                  </span>
                                )}
                                {v.sensitive && (
                                  <span className="text-[9px] text-muted-foreground font-mono">🔒</span>
                                )}
                              </div>
                              <p className="text-[10px] text-muted-foreground mt-0.5">
                                {v.description}
                              </p>
                              <p className="text-[9px] text-muted-foreground font-mono mt-0.5">
                                {v.key}
                                {v.is_from_file && " (.env)"}
                                {v.is_from_env && " (env)"}
                              </p>
                            </div>
                          </div>

                          <div className="flex gap-2">
                            <div className="flex-1 relative">
                              <input
                                type={v.sensitive && !isShown ? "password" : "text"}
                                placeholder={v.is_set && v.sensitive ? "•••••••• (enter new value to change)" : v.placeholder}
                                value={editVal}
                                onChange={e => setEditValues(prev => ({ ...prev, [v.key]: e.target.value }))}
                                className="w-full bg-background/50 rounded-md px-2.5 py-1.5 text-xs font-mono outline-none border border-border/50 focus:border-primary/50 transition-colors"
                              />
                              {v.sensitive && (
                                <button
                                  onClick={() => toggleShow(v.key)}
                                  className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                                >
                                  {isShown ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                                </button>
                              )}
                            </div>

                            {/* Test button for LLM providers */}
                            {v.is_set && v.key.includes("API_KEY") && v.key !== "ZAI_API_KEY" && (
                              <button
                                onClick={() => testVar(v.key)}
                                disabled={testResult?.loading}
                                className="px-2 py-1.5 rounded-md text-[10px] bg-cyan-500/15 text-cyan-400 border border-cyan-500/30 hover:bg-cyan-500/25 transition-all flex items-center gap-1 whitespace-nowrap"
                                title="Test connection"
                              >
                                {testResult?.loading ? (
                                  <Loader2 className="w-3 h-3 animate-spin" />
                                ) : (
                                  <Zap className="w-3 h-3" />
                                )}
                                Test
                              </button>
                            )}

                            {/* Clear button */}
                            {v.is_set && (
                              <button
                                onClick={() => clearVar(v.key)}
                                className="px-2 py-1.5 rounded-md text-[10px] bg-muted/40 text-muted-foreground hover:bg-red-500/20 hover:text-red-400 transition-all"
                                title={L(lang, { en: "Clear", fr: "Supprimer", es: "Clear", de: "Clear", pt: "Clear" })}
                              >
                                <Trash2 className="w-3 h-3" />
                              </button>
                            )}
                          </div>

                          {/* Test result */}
                          {testResult && !testResult.loading && (
                            <div className={cn(
                              "text-[10px] mt-1.5 font-mono",
                              testResult.success ? "text-emerald-400" : "text-red-400"
                            )}>
                              {testResult.message}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Footer */}
          <div className="p-5 border-t border-border/50 flex items-center justify-between gap-3">
            <div className="flex-1 min-w-0">
              {savedMessage && (
                <motion.p
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  className={cn(
                    "text-xs",
                    savedMessage.startsWith("✅") ? "text-emerald-400" : "text-red-400"
                  )}
                >
                  {savedMessage}
                </motion.p>
              )}
              {!savedMessage && dirty && (
                <p className="text-xs text-amber-400 flex items-center gap-1">
                  <AlertCircle className="w-3 h-3" />
                  {L(lang, { en: "Unsaved changes", fr: "Modifications non sauvegardées", es: "Unsaved changes", de: "Unsaved changes", pt: "Unsaved changes" })}
                </p>
              )}
            </div>
            <div className="flex gap-2 flex-shrink-0">
              <Button size="sm" variant="ghost" onClick={load} disabled={saving}>
                <RefreshCw className="w-3.5 h-3.5 mr-1.5" />
                {L(lang, { en: "Refresh", fr: "Actualiser", es: "Refresh", de: "Refresh", pt: "Refresh" })}
              </Button>
              <Button
                size="sm"
                onClick={saveAll}
                disabled={saving || !dirty}
                className="gap-1.5"
              >
                {saving ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Save className="w-3.5 h-3.5" />
                )}
                {L(lang, { en: "Save", fr: "Sauvegarder", es: "Save", de: "Save", pt: "Save" })}
              </Button>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
