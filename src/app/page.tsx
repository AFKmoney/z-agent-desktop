"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Command, MessageCircle, Users, Settings as SettingsIcon, Menu, X } from "lucide-react";
import { useAgent } from "@/hooks/use-agent";
import { detectBrowserLang, setStoredLang, type Lang } from "@/lib/i18n";
import { LanguageSelector } from "@/components/LanguageSelector";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Sidebar, type SectionId } from "@/components/agent/sidebar";
import {
  OverviewSection, TasksSection, MonitorSection, AnalyticsSection,
  AutomationSection, KnowledgeSection,
} from "@/components/agent/sections";
import { SettingsModal } from "@/components/agent/settings-modal";
import { ChatInterface } from "@/components/agent/chat-interface";
import { AgentCreatorModal } from "@/components/agent/agent-creator";
import { CommandPalette } from "@/components/agent";
import { ParticleBackground } from "@/components/agent";

export default function Dashboard() {
  const [lang, setLang] = useState<Lang>(() => typeof window !== "undefined" ? detectBrowserLang() : "en");
  const [section, setSection] = useState<SectionId>("overview");
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [agentsOpen, setAgentsOpen] = useState(false);
  const [mobileSidebar, setMobileSidebar] = useState(false);

  const { status, connected, refresh } = useAgent();
  const state = status?.state ?? "stopped";

  // Cmd+K shortcut
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

  const navigateTo = (s: string) => {
    setSection(s as SectionId);
    setMobileSidebar(false);
  };

  return (
    <div className="min-h-screen bg-background flex">
      <ParticleBackground />

      {/* Mobile sidebar overlay */}
      {mobileSidebar && (
        <div className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden" onClick={() => setMobileSidebar(false)} />
      )}

      {/* Sidebar — fixed on desktop, drawer on mobile */}
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

      {/* Main content area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header className="sticky top-0 z-30 glass-strong border-b border-border/50">
          <div className="flex items-center justify-between px-4 py-3">
            {/* Mobile menu button */}
            <button
              onClick={() => setMobileSidebar(!mobileSidebar)}
              className="lg:hidden w-8 h-8 rounded-lg hover:bg-accent/30 flex items-center justify-center"
            >
              {mobileSidebar ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
            </button>

            {/* Mobile logo */}
            <div className="lg:hidden flex items-center gap-2">
              <span className="text-sm font-bold">Z.AGENT</span>
            </div>

            {/* Right actions */}
            <div className="flex items-center gap-1.5 ml-auto">
              <Button size="sm" variant="ghost" onClick={() => setPaletteOpen(true)} className="gap-2 text-xs">
                <Command className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">{lang === "fr" ? "Commande" : "Command"}</span>
                <kbd className="text-[9px] font-mono bg-muted/60 px-1 py-0.5 rounded">⌘K</kbd>
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setChatOpen(true)} className="gap-1.5 text-xs px-2" title="Chat">
                <MessageCircle className="w-3.5 h-3.5" />
                <span className="hidden md:inline">{lang === "fr" ? "Chat" : "Chat"}</span>
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setAgentsOpen(true)} className="gap-1.5 text-xs px-2" title="Agents">
                <Users className="w-3.5 h-3.5" />
                <span className="hidden md:inline">{lang === "fr" ? "Agents" : "Agents"}</span>
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setSection("settings")} className="gap-1.5 text-xs px-2" title={lang === "fr" ? "Paramètres" : "Settings"}>
                <SettingsIcon className="w-3.5 h-3.5" />
                <span className="hidden md:inline">{lang === "fr" ? "Paramètres" : "Settings"}</span>
              </Button>
              <LanguageSelector
                currentLang={lang}
                onLanguageChange={(l) => { setLang(l); setStoredLang(l); }}
              />
            </div>
          </div>
        </header>

        {/* Section content */}
        <main className="flex-1 overflow-y-auto p-6">
          <motion.div
            key={section}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
          >
            {section === "overview" && <OverviewSection lang={lang} onNavigate={navigateTo} />}
            {section === "tasks" && <TasksSection lang={lang} />}
            {section === "monitor" && <MonitorSection lang={lang} />}
            {section === "analytics" && <AnalyticsSection lang={lang} />}
            {section === "automation" && <AutomationSection lang={lang} />}
            {section === "knowledge" && <KnowledgeSection lang={lang} />}
            {section === "chat" && (
              <div className="max-w-5xl mx-auto">
                <ChatInterface open={true} onClose={() => setSection("overview")} lang={lang} />
              </div>
            )}
            {section === "agents" && (
              <div className="max-w-3xl mx-auto">
                <AgentCreatorModal open={true} onClose={() => setSection("overview")} lang={lang} />
              </div>
            )}
            {section === "settings" && (
              <div className="max-w-3xl mx-auto">
                <SettingsModal open={true} onClose={() => setSection("overview")} lang={lang} />
              </div>
            )}
          </motion.div>
        </main>

        {/* Footer */}
        <footer className="border-t border-border/50 py-3 px-6">
          <div className="flex justify-between items-center text-[10px] text-muted-foreground font-mono">
            <span>Z.AGENT v4.0 · {lang === "fr" ? "propulsé par z.ai GLM" : "powered by z.ai GLM"}</span>
            <span className="flex items-center gap-1.5">
              <span className={cn("w-1.5 h-1.5 rounded-full", connected ? "bg-emerald-500" : "bg-red-500")} />
              {state}
            </span>
          </div>
        </footer>
      </div>

      {/* Modals */}
      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} onSubmit={(text) => { setSection("tasks"); }} />
      <SettingsModal open={settingsOpen} onClose={() => setSettingsOpen(false)} lang={lang} />
      <ChatInterface open={chatOpen} onClose={() => setChatOpen(false)} lang={lang} />
      <AgentCreatorModal open={agentsOpen} onClose={() => setAgentsOpen(false)} lang={lang} />
    </div>
  );
}
