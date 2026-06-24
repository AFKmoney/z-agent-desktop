"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  MessageSquare, Plus, Send, Trash2, Pin, Archive, Search,
  Loader2, Bot, User, Copy, RefreshCw, ChevronDown,
} from "lucide-react";
import { agentApi } from "@/lib/agent-api";
import { cn } from "@/lib/utils";

interface ChatMessage {
  id: string;
  role: string;
  content: string;
  timestamp: number;
  datetime: string;
  metadata?: Record<string, unknown>;
}

interface Conversation {
  id: string;
  title: string;
  agent_id?: string;
  created_at: number;
  updated_at: number;
  pinned: boolean;
  archived: boolean;
  message_count: number;
  messages?: ChatMessage[];
}

interface CustomAgent {
  id: string;
  name: string;
  emoji: string;
  color: string;
  description: string;
}

export function ChatInterface({
  open,
  onClose,
  lang,
}: {
  open: boolean;
  onClose: () => void;
  lang: "en" | "fr";
}) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConv, setActiveConv] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [search, setSearch] = useState("");
  const [agents, setAgents] = useState<CustomAgent[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<string | undefined>(undefined);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const loadConversations = useCallback(async () => {
    try {
      const r = await agentApi.chatList();
      setConversations(r.conversations as Conversation[]);
    } catch {}
  }, []);

  const loadAgents = useCallback(async () => {
    try {
      const r = await agentApi.agentsList();
      setAgents(r.agents as CustomAgent[]);
    } catch {}
  }, []);

  useEffect(() => {
    if (open) {
      loadConversations();
      loadAgents();
    }
  }, [open, loadConversations, loadAgents]);

  // Poll conversations every 10s
  useEffect(() => {
    if (!open) return;
    const i = setInterval(loadConversations, 10000);
    return () => clearInterval(i);
  }, [open, loadConversations]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  const openConversation = async (conv: Conversation) => {
    try {
      const r = await agentApi.chatGet(conv.id);
      const fullConv = r as unknown as Conversation;
      setActiveConv(fullConv);
      setMessages(fullConv.messages || []);
      setSelectedAgentId(fullConv.agent_id);
    } catch {}
  };

  const createConversation = async () => {
    try {
      const r = await agentApi.chatCreate({ agent_id: selectedAgentId });
      const newConv = r as unknown as Conversation;
      setActiveConv(newConv);
      setMessages([]);
      loadConversations();
    } catch {}
  };

  const deleteConversation = async (convId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await agentApi.chatDelete(convId);
      if (activeConv?.id === convId) {
        setActiveConv(null);
        setMessages([]);
      }
      loadConversations();
    } catch {}
  };

  const pinConversation = async (convId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const conv = conversations.find(c => c.id === convId);
      await agentApi.chatUpdate(convId, { pinned: !conv?.pinned });
      loadConversations();
    } catch {}
  };

  const sendMessage = async () => {
    if (!input.trim() || !activeConv) return;

    // Optimistically add user message
    const userMsg: ChatMessage = {
      id: `temp_${Date.now()}`,
      role: "user",
      content: input,
      timestamp: Date.now() / 1000,
      datetime: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMsg]);
    const messageText = input;
    setInput("");
    setSending(true);

    try {
      const r = await agentApi.chatSend(activeConv.id, messageText);
      if (r.success) {
        const assistantMsg: ChatMessage = {
          id: `resp_${Date.now()}`,
          role: "assistant",
          content: r.response,
          timestamp: Date.now() / 1000,
          datetime: new Date().toISOString(),
          metadata: r.metadata,
        };
        setMessages(prev => [...prev, assistantMsg]);
      } else {
        setMessages(prev => [...prev, {
          id: `err_${Date.now()}`,
          role: "assistant",
          content: `❌ ${r.response}`,
          timestamp: Date.now() / 1000,
          datetime: new Date().toISOString(),
        }]);
      }
      loadConversations();
    } catch (e) {
      setMessages(prev => [...prev, {
        id: `err_${Date.now()}`,
        role: "assistant",
        content: `❌ Error: ${e instanceof Error ? e.message : "unknown"}`,
        timestamp: Date.now() / 1000,
        datetime: new Date().toISOString(),
      }]);
    }
    setSending(false);
  };

  const filteredConversations = conversations.filter(c =>
    !search || c.title.toLowerCase().includes(search.toLowerCase())
  );

  if (!open) return null;

  return (
    <AnimatePresence>
      <motion.div
        className="fixed inset-0 z-50 flex"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
      >
        <div className="absolute inset-0 bg-black/70 backdrop-blur-md" onClick={onClose} />

        <motion.div
          className="glass-strong w-full max-w-5xl mx-auto my-4 rounded-2xl flex flex-col overflow-hidden glow-primary"
          style={{ height: "calc(100vh - 2rem)" }}
          initial={{ scale: 0.95, y: 20 }}
          animate={{ scale: 1, y: 0 }}
          exit={{ scale: 0.95, y: 20 }}
          transition={{ type: "spring", damping: 25 }}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-border/50">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-primary/15 border border-primary/30 flex items-center justify-center">
                <MessageSquare className="w-4 h-4 text-primary" />
              </div>
              <div>
                <h2 className="text-base font-bold">
                  {lang === "fr" ? "Chat" : "Chat"}
                </h2>
                <p className="text-xs text-muted-foreground">
                  {conversations.length} {lang === "fr" ? "conversations" : "conversations"}
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-lg hover:bg-accent/30 flex items-center justify-center transition-colors text-muted-foreground"
            >
              ✕
            </button>
          </div>

          {/* Body: sidebar + messages */}
          <div className="flex-1 flex overflow-hidden">
            {/* Sidebar — conversation list */}
            <div className="w-64 border-r border-border/50 flex flex-col">
              {/* New chat button */}
              <div className="p-3">
                <button
                  onClick={createConversation}
                  className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-primary/15 text-primary border border-primary/30 hover:bg-primary/25 transition-all text-sm font-medium"
                >
                  <Plus className="w-4 h-4" />
                  {lang === "fr" ? "Nouveau chat" : "New chat"}
                </button>
              </div>

              {/* Agent selector */}
              <div className="px-3 pb-2">
                <select
                  value={selectedAgentId || ""}
                  onChange={e => setSelectedAgentId(e.target.value || undefined)}
                  className="w-full bg-background/50 rounded-md px-2 py-1.5 text-xs outline-none border border-border/50 focus:border-primary/50"
                >
                  <option value="">{lang === "fr" ? "Agent par défaut" : "Default agent"}</option>
                  {agents.map(a => (
                    <option key={a.id} value={a.id}>{a.emoji} {a.name}</option>
                  ))}
                </select>
              </div>

              {/* Search */}
              <div className="px-3 pb-2 relative">
                <Search className="absolute left-5 top-1/2 -translate-y-1/2 w-3 h-3 text-muted-foreground" />
                <input
                  placeholder={lang === "fr" ? "Rechercher..." : "Search..."}
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  className="w-full bg-background/50 rounded-md pl-7 pr-2 py-1.5 text-xs outline-none border border-border/50 focus:border-primary/50"
                />
              </div>

              {/* Conversation list */}
              <div className="flex-1 overflow-y-auto px-2 pb-2 space-y-0.5">
                {filteredConversations.length === 0 ? (
                  <p className="text-xs text-muted-foreground text-center py-4">
                    {lang === "fr" ? "Aucune conversation" : "No conversations"}
                  </p>
                ) : (
                  filteredConversations.map(conv => (
                    <div
                      key={conv.id}
                      onClick={() => openConversation(conv)}
                      className={cn(
                        "group flex items-center gap-2 px-2 py-2 rounded-lg cursor-pointer transition-all",
                        activeConv?.id === conv.id ? "bg-primary/15 border border-primary/30" : "hover:bg-accent/20"
                      )}
                    >
                      {conv.pinned && <Pin className="w-2.5 h-2.5 text-amber-400 flex-shrink-0" />}
                      <div className="flex-1 min-w-0">
                        <p className="text-xs truncate">{conv.title || (lang === "fr" ? "Sans titre" : "Untitled")}</p>
                        <p className="text-[9px] text-muted-foreground">
                          {conv.message_count} {lang === "fr" ? "messages" : "messages"}
                        </p>
                      </div>
                      <button
                        onClick={(e) => pinConversation(conv.id, e)}
                        className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-amber-400 transition-all"
                      >
                        <Pin className="w-3 h-3" />
                      </button>
                      <button
                        onClick={(e) => deleteConversation(conv.id, e)}
                        className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-red-400 transition-all"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Messages area */}
            <div className="flex-1 flex flex-col">
              {activeConv ? (
                <>
                  {/* Messages */}
                  <div className="flex-1 overflow-y-auto p-4 space-y-3">
                    {messages.length === 0 ? (
                      <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
                        <Bot className="w-12 h-12 mb-3 opacity-30" />
                        <p className="text-sm">
                          {lang === "fr" ? "Démarrez la conversation" : "Start the conversation"}
                        </p>
                      </div>
                    ) : (
                      messages.map((msg, i) => (
                        <motion.div
                          key={msg.id || i}
                          className={cn(
                            "flex gap-3",
                            msg.role === "user" ? "flex-row-reverse" : "flex-row"
                          )}
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ duration: 0.2 }}
                        >
                          {/* Avatar */}
                          <div
                            className={cn(
                              "w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0",
                              msg.role === "user"
                                ? "bg-cyan-500/15 border border-cyan-500/30"
                                : "bg-primary/15 border border-primary/30"
                            )}
                          >
                            {msg.role === "user" ? (
                              <User className="w-3.5 h-3.5 text-cyan-400" />
                            ) : (
                              <Bot className="w-3.5 h-3.5 text-primary" />
                            )}
                          </div>

                          {/* Bubble */}
                          <div
                            className={cn(
                              "max-w-[75%] rounded-xl px-3 py-2",
                              msg.role === "user"
                                ? "bg-cyan-500/10 border border-cyan-500/20"
                                : "glass"
                            )}
                          >
                            <p className="text-sm whitespace-pre-wrap break-words">{msg.content}</p>
                            {msg.metadata && (
                              <div className="flex gap-2 mt-1 text-[9px] text-muted-foreground font-mono">
                                {msg.metadata.model && <span>{String(msg.metadata.model)}</span>}
                                {msg.metadata.elapsed_s && <span>{Number(msg.metadata.elapsed_s).toFixed(1)}s</span>}
                                {msg.metadata.tokens_out && <span>{msg.metadata.tokens_out} tok</span>}
                              </div>
                            )}
                          </div>
                        </motion.div>
                      ))
                    )}
                    {sending && (
                      <div className="flex gap-3">
                        <div className="w-7 h-7 rounded-lg bg-primary/15 border border-primary/30 flex items-center justify-center flex-shrink-0">
                          <Loader2 className="w-3.5 h-3.5 text-primary animate-spin" />
                        </div>
                        <div className="glass rounded-xl px-3 py-2">
                          <div className="flex gap-1">
                            {[0, 1, 2].map(i => (
                              <motion.div
                                key={i}
                                className="w-1.5 h-1.5 rounded-full bg-primary"
                                animate={{ scale: [1, 1.5, 1], opacity: [0.4, 1, 0.4] }}
                                transition={{ duration: 0.8, repeat: Infinity, delay: i * 0.15 }}
                              />
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                    <div ref={messagesEndRef} />
                  </div>

                  {/* Input */}
                  <div className="p-3 border-t border-border/50">
                    <div className="flex gap-2 items-end">
                      <textarea
                        placeholder={lang === "fr" ? "Tapez votre message..." : "Type your message..."}
                        value={input}
                        onChange={e => setInput(e.target.value)}
                        onKeyDown={e => {
                          if (e.key === "Enter" && !e.shiftKey) {
                            e.preventDefault();
                            sendMessage();
                          }
                        }}
                        rows={1}
                        className="flex-1 glass rounded-xl px-3 py-2 text-sm outline-none resize-none focus:border-primary/50"
                        style={{ maxHeight: "120px" }}
                      />
                      <button
                        onClick={sendMessage}
                        disabled={!input.trim() || sending}
                        className="w-9 h-9 rounded-xl bg-primary/20 text-primary border border-primary/30 hover:bg-primary/30 disabled:opacity-30 transition-all flex items-center justify-center flex-shrink-0"
                      >
                        <Send className="w-4 h-4" />
                      </button>
                    </div>
                    <p className="text-[9px] text-muted-foreground mt-1.5 text-center">
                      {lang === "fr" ? "Entrée pour envoyer · Maj+Entrée pour nouvelle ligne" : "Enter to send · Shift+Enter for new line"}
                    </p>
                  </div>
                </>
              ) : (
                <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground">
                  <Bot className="w-16 h-16 mb-4 opacity-20" />
                  <p className="text-sm mb-1">
                    {lang === "fr" ? "Sélectionnez ou créez une conversation" : "Select or create a conversation"}
                  </p>
                  <p className="text-xs">
                    {lang === "fr" ? "Choisissez un agent personnalisé pour des réponses spécialisées" : "Choose a custom agent for specialized responses"}
                  </p>
                </div>
              )}
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
