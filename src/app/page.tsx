"use client";

import { useState, useEffect, useCallback } from "react";
import dynamic from "next/dynamic";
import { Menu, X, Send } from "lucide-react";
import { useAgent } from "@/hooks/use-agent";
import { agentApi } from "@/lib/agent-api";
import { detectBrowserLang, setStoredLang, type Lang } from "@/lib/i18n";
import { LanguageSelector } from "@/components/LanguageSelector";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";
import { type SectionId } from "@/components/agent/sidebar";

const ParticleBackground = dynamic(() => import("@/components/agent").then(m => m.ParticleBackground), { ssr: false });
const Sidebar = dynamic(() => import("@/components/agent/sidebar").then(m => m.Sidebar), { ssr: false });
const OverviewSection = dynamic(() => import("@/components/agent/sections").then(m => m.OverviewSection), { ssr: false });
const ChatSection = dynamic(() => import("@/components/agent/sections").then(m => m.ChatSection), { ssr: false });
const TasksSection = dynamic(() => import("@/components/agent/sections").then(m => m.TasksSection), { ssr: false });
const MonitorSection = dynamic(() => import("@/components/agent/sections").then(m => m.MonitorSection), { ssr: false });
const AnalyticsSection = dynamic(() => import("@/components/agent/sections").then(m => m.AnalyticsSection), { ssr: false });
const AutomationSection = dynamic(() => import("@/components/agent/sections").then(m => m.AutomationSection), { ssr: false });
const KnowledgeSection = dynamic(() => import("@/components/agent/sections").then(m => m.KnowledgeSection), { ssr: false });
const AgentsSection = dynamic(() => import("@/components/agent/sections").then(m => m.AgentsSection), { ssr: false });
const SettingsSection = dynamic(() => import("@/components/agent/sections").then(m => m.SettingsSection), { ssr: false });

function L(lang: string, texts: Record<string, string>): string {
  return texts[lang] || texts.en;
}

export default function Dashboard() {
  const [lang, setLang] = useState<Lang>("en");
  const [section, setSection] = useState<SectionId>("overview");
  const [mobileSidebar, setMobileSidebar] = useState(false);
  const [quickTask, setQuickTask] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    const detected = detectBrowserLang();
    if (detected !== "en") setLang(detected); // eslint-disable-line react-hooks/set-state-in-effect
  }, []);

  const { status, connected } = useAgent();
  const state = status?.state ?? "stopped";

  const navigateTo = useCallback((s: string) => {
    setSection(s as SectionId);
    setMobileSidebar(false);
  }, []);

  const submitQuickTask = () => {
    if (!quickTask.trim()) return;
    setSubmitting(true);
    agentApi.submitTask(quickTask, "dashboard")
      .then(() => {
        toast({ title: L(lang, { en: "Task sent", fr: "Tâche envoyée", es: "Tarea enviada", de: "Aufgabe gesendet", pt: "Tarefa enviada" }) });
        setQuickTask("");
        setSection("tasks");
      })
      .catch(() => {
        toast({ title: L(lang, { en: "Backend offline", fr: "Backend hors-ligne", es: "Backend desconectado", de: "Backend offline", pt: "Backend offline" }), variant: "destructive" });
      })
      .finally(() => setSubmitting(false));
  };

  return (
    <div className="min-h-screen bg-background flex">
      <ParticleBackground />

      {mobileSidebar && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={() => setMobileSidebar(false)}
        />
      )}

      <div className={cn(
        "fixed lg:sticky top-0 left-0 h-screen z-50 lg:z-30 transition-transform duration-300",
        mobileSidebar ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
      )}>
        <div className="glass-strong h-full">
          <Sidebar
            active={section}
            onSelect={navigateTo}
            lang={lang}
            agentState={state}
            connected={connected}
          />
        </div>
      </div>

      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar with quick task input — replaces the broken Command palette */}
        <header className="sticky top-0 z-30 glass-strong border-b border-border/50">
          <div className="flex items-center gap-2 px-4 py-2.5">
            <button
              onClick={() => setMobileSidebar(!mobileSidebar)}
              className="lg:hidden w-8 h-8 rounded-lg hover:bg-accent/30 flex items-center justify-center flex-shrink-0"
            >
              {mobileSidebar ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
            </button>

            <div className="lg:hidden flex items-center gap-2 flex-shrink-0">
              <span className="text-sm font-bold">Z.AGENT</span>
            </div>

            {/* Quick task input — always visible, no modal, no overlay */}
            <div className="flex-1 flex gap-2 max-w-2xl mx-auto">
              <input
                type="text"
                placeholder={L(lang, {
                  en: "Quick task... (e.g. 'Sort my downloads')",
                  fr: "Tâche rapide... (ex: 'Trie mes téléchargements')",
                  es: "Tarea rápida... (ej: 'Ordena mis descargas')",
                  de: "Schnellaufgabe... (z.B. 'Sortiere meine Downloads')",
                  pt: "Tarefa rápida... (ex: 'Ordene meus downloads')",
                })}
                value={quickTask}
                onChange={e => setQuickTask(e.target.value)}
                onKeyDown={e => { if (e.key === "Enter") submitQuickTask(); }}
                className="flex-1 bg-background/50 rounded-lg px-3 py-1.5 text-sm outline-none border border-border/50 focus:border-primary/50"
              />
              <Button
                size="sm"
                onClick={submitQuickTask}
                disabled={!quickTask.trim() || submitting}
                className="flex-shrink-0 gap-1.5"
              >
                <Send className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">{L(lang, { en: "Send", fr: "Envoyer", es: "Enviar", de: "Senden", pt: "Enviar" })}</span>
              </Button>
            </div>

            <LanguageSelector
              currentLang={lang}
              onLanguageChange={(l) => { setLang(l); setStoredLang(l); }}
            />
          </div>
        </header>

        {/* Section content */}
        <main className="flex-1 overflow-y-auto p-6">
          {section === "overview" && <OverviewSection lang={lang} onNavigate={navigateTo} />}
          {section === "chat" && <ChatSection lang={lang} />}
          {section === "tasks" && <TasksSection lang={lang} />}
          {section === "monitor" && <MonitorSection lang={lang} />}
          {section === "analytics" && <AnalyticsSection lang={lang} />}
          {section === "automation" && <AutomationSection lang={lang} />}
          {section === "knowledge" && <KnowledgeSection lang={lang} />}
          {section === "agents" && <AgentsSection lang={lang} />}
          {section === "settings" && <SettingsSection lang={lang} />}
        </main>

        <footer className="border-t border-border/50 py-3 px-6">
          <div className="flex justify-between items-center text-[10px] text-muted-foreground font-mono">
            <span>Z.AGENT v4.0 · {L(lang, { en: "powered by z.ai GLM", fr: "propulsé par z.ai GLM", es: "impulsado por z.ai GLM", de: "betrieben durch z.ai GLM", pt: "powered by z.ai GLM" })}</span>
            <span className="flex items-center gap-1.5">
              <span className={cn("w-1.5 h-1.5 rounded-full", connected ? "bg-emerald-500" : "bg-red-500")} />
              {state}
            </span>
          </div>
        </footer>
      </div>
    </div>
  );
}
