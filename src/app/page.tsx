"use client";

import { useState, useEffect, useCallback } from "react";
import dynamic from "next/dynamic";
import { Command, Menu, X, Loader2 } from "lucide-react";
import { useAgent } from "@/hooks/use-agent";
import { agentApi } from "@/lib/agent-api";
import { detectBrowserLang, setStoredLang, type Lang } from "@/lib/i18n";
import { LanguageSelector } from "@/components/LanguageSelector";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { type SectionId } from "@/components/agent/sidebar";
import { CommandPalette } from "@/components/agent";

// Dynamically import heavy components with SSR disabled to prevent hydration mismatch
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
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [mobileSidebar, setMobileSidebar] = useState(false);

  useEffect(() => {
    const detected = detectBrowserLang();
    if (detected !== "en") setLang(detected); // eslint-disable-line react-hooks/set-state-in-effect
  }, []);

  const { status, connected } = useAgent();
  const state = status?.state ?? "stopped";

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setPaletteOpen(true);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  const navigateTo = useCallback((s: string) => {
    setSection(s as SectionId);
    setMobileSidebar(false);
  }, []);

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
        <header className="sticky top-0 z-30 glass-strong border-b border-border/50">
          <div className="flex items-center justify-between px-4 py-3">
            <button
              onClick={() => setMobileSidebar(!mobileSidebar)}
              className="lg:hidden w-8 h-8 rounded-lg hover:bg-accent/30 flex items-center justify-center"
            >
              {mobileSidebar ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
            </button>

            <div className="lg:hidden flex items-center gap-2">
              <span className="text-sm font-bold">Z.AGENT</span>
            </div>

            <div className="flex items-center gap-1.5 ml-auto">
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setPaletteOpen(true)}
                className="gap-2 text-xs"
              >
                <Command className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">{L(lang, { en: "Command", fr: "Commande", es: "Comando", de: "Befehl", pt: "Comando" })}</span>
                <kbd className="text-[9px] font-mono bg-muted/60 px-1 py-0.5 rounded">⌘K</kbd>
              </Button>
              <LanguageSelector
                currentLang={lang}
                onLanguageChange={(l) => { setLang(l); setStoredLang(l); }}
              />
            </div>
          </div>
        </header>

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

      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        onSubmit={(text) => {
          setPaletteOpen(false);
          setSection("overview");
          agentApi.submitTask(text, "dashboard").catch(() => {});
        }}
      />
    </div>
  );
}
