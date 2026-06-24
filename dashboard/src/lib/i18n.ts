export const STRINGS: Record<string, Partial<Record<Lang, string>> & { en: string }> = {
  // Navigation & General
  "nav.dashboard": { en: "Dashboard", fr: "Tableau de bord", es: "Panel de control", de: "Dashboard", pt: "Painel" },
  "nav.settings": { en: "Settings", fr: "Paramètres", es: "Ajustes", de: "Einstellungen", pt: "Configurações" },
  "nav.logs": { en: "System Logs", fr: "Journaux système", es: "Registros del sistema", de: "Systemprotokolle", pt: "Logs do Sistema" },
  "nav.docs": { en: "Documentation", fr: "Documentation", es: "Documentación", de: "Dokumentation", pt: "Documentação" },
  
  // App Header
  "app.title": { en: "Z.AGENT", fr: "Z.AGENT", es: "Z.AGENT", de: "Z.AGENT", pt: "Z.AGENT" },
  "app.subtitle": { en: "Desktop Interface", fr: "Interface de bureau", es: "Interfaz de escritorio", de: "Desktop-Schnittstelle", pt: "Interface de Desktop" },
  "app.status": { en: "Status", fr: "Statut", es: "Estado", de: "Status", pt: "Status" },
  "app.connected": { en: "Connected", fr: "Connecté", es: "Conectado", de: "Verbunden", pt: "Conectado" },
  "app.disconnected": { en: "Disconnected", fr: "Déconnecté", es: "Desconectado", de: "Getrennt", pt: "Desconectado" },

  // States
  "state.idle": { en: "Idle", fr: "En attente", es: "Inactivo", de: "Im Leerlauf", pt: "Inativo" },
  "state.planning": { en: "Planning", fr: "Planification", es: "Planificando", de: "Planung", pt: "Planejando" },
  "state.executing": { en: "Executing", fr: "Exécution", es: "Ejecutando", de: "Ausführen", pt: "Executando" },
  "state.paused": { en: "Paused", fr: "En pause", es: "Pausado", de: "Pausiert", pt: "Pausado" },
  "state.error": { en: "Error", fr: "Erreur", es: "Error", de: "Fehler", pt: "Erro" },
  "state.stopped": { en: "Stopped", fr: "Arrêté", es: "Detenido", de: "Gestoppt", pt: "Parado" },

  // Stats labels
  "label.state": { en: "State", fr: "État", es: "Estado", de: "Zustand", pt: "Estado" },
  "label.queue": { en: "Queue", fr: "File", es: "Cola", de: "Warteschlange", pt: "Fila" },
  "label.uptime": { en: "Uptime", fr: "Uptime", es: "Tiempo de actividad", de: "Betriebszeit", pt: "Tempo de atividade" },
  "label.logs": { en: "Logs", fr: "Logs", es: "Registros", de: "Protokolle", pt: "Logs" },

  // Memory card
  "dash.memory": { en: "Memory", fr: "Mémoire", es: "Memoria", de: "Speicher", pt: "Memória" },
  "dash.facts": { en: "Persistent facts", fr: "Faits persistants", es: "Hechos persistentes", de: "Beständige Fakten", pt: "Fatos persistentes" },
  "dash.preferences": { en: "Preferences", fr: "Préférences", es: "Preferencias", de: "Präferenzen", pt: "Preferências" },
  "dash.shortcuts": { en: "Learned shortcuts", fr: "Raccourcis appris", es: "Atajos aprendidos", de: "Gelernte Verknüpfungen", pt: "Atalhos aprendidos" },
  "dash.recent_tasks": { en: "Recent tasks", fr: "Dernières tâches", es: "Tareas recientes", de: "Aktuelle Aufgaben", pt: "Tarefas recentes" },
  "misc.no_recent_tasks": { en: "No recent tasks", fr: "Aucune tâche récente", es: "Sin tareas recientes", de: "Keine aktuellen Aufgaben", pt: "Nenhuma tarefa recente" },

  // Task submission
  "dash.submit_task": { en: "Submit a task", fr: "Soumettre une tâche", es: "Enviar una tarea", de: "Aufgabe einreichen", pt: "Enviar uma tarefa" },
  "dash.task_placeholder": {
    en: "What should I do? (e.g. 'Organize my downloads', 'Take a screenshot of the browser')",
    fr: "Que dois-je faire ? (ex: 'Organise mes téléchargements')",
    es: "¿Qué debo hacer? (ej. 'Organiza mis descargas', 'Toma una captura del navegador')",
    de: "Was soll ich tun? (z.B. 'Ordne meine Downloads', 'Mach einen Screenshot')",
    pt: "O que devo fazer? (ex: 'Organize meus downloads', 'Tire uma captura de tela')"
  },
  "action.send": { en: "Send", fr: "Envoyer", es: "Enviar", de: "Senden", pt: "Enviar" },
  "action.pause": { en: "Pause agent", fr: "Mettre l'agent en pause", es: "Pausar agente", de: "Agent pausieren", pt: "Pausar agente" },
  "action.resume": { en: "Resume agent", fr: "Reprendre l'agent", es: "Reanudar agente", de: "Agent fortsetzen", pt: "Retomar agente" },
  "action.stop": { en: "Stop task", fr: "Arrêter la tâche", es: "Detener tarea", de: "Aufgabe stoppen", pt: "Parar tarefa" },
  "action.clear_queue": { en: "Clear queue", fr: "Vider la file", es: "Vaciar cola", de: "Warteschlange leeren", pt: "Limpar fila" },

  // Perception card
  "dash.perception": { en: "Perception", fr: "Perception", es: "Percepción", de: "Wahrnehmung", pt: "Percepção" },
  "dash.no_screenshot": {
    en: "No visual data.\n\nGLM-4V needs a screenshot to localize elements.",
    fr: "Aucune donnée visuelle.\n\nGLM-4V a besoin d'une capture pour localiser les éléments.",
    es: "Sin datos visuales.\n\nGLM-4V necesita una captura para localizar elementos.",
    de: "Keine visuellen Daten.\n\nGLM-4V benötigt einen Screenshot.",
    pt: "Sem dados visuais.\n\nGLM-4V precisa de uma captura de tela."
  },
  "dash.analyze_screen": { en: "Analyze screen", fr: "Analyser l'écran", es: "Analizar pantalla", de: "Bildschirm analysieren", pt: "Analisar tela" },
  "dash.capture_now": { en: "Capture now", fr: "Capturer maintenant", es: "Capturar ahora", de: "Jetzt aufnehmen", pt: "Capturar agora" },

  // Tip card
  "misc.tip_title": { en: "Tip", fr: "Astuce", es: "Consejo", de: "Tipp", pt: "Dica" },
  "misc.tip_body": {
    en: "The agent runs in full autonomy. You can send tasks from Telegram when you're away — it plans, executes, and notifies you of the result.",
    fr: "L'agent fonctionne en autonomie complète. Tu peux lui envoyer des tâches depuis Telegram quand tu es absent — il planifie, exécute et te notifie du résultat.",
    es: "El agente se ejecuta con total autonomía. Puedes enviar tareas desde Telegram cuando estés fuera; planifica, ejecuta y te notifica el resultado.",
    de: "Der Agent läuft völlig autonom. Du kannst Aufgaben über Telegram senden — er plant, führt aus und benachrichtigt dich.",
    pt: "O agente é totalmente autônomo. Você pode enviar tarefas do Telegram quando estiver fora — ele planeja, executa e notifica você."
  },

  // Plan detail
  "dash.plan_label": { en: "Plan", fr: "Plan", es: "Plan", de: "Plan", pt: "Plano" },
  "dash.steps_label": { en: "steps", fr: "étapes", es: "pasos", de: "Schritte", pt: "passos" },

  // Toasts
  "toast.task_sent": { en: "Task sent", fr: "Tâche envoyée", es: "Tarea enviada", de: "Aufgabe gesendet", pt: "Tarefa enviada" },
  "toast.command_sent": { en: "Command sent", fr: "Commande envoyée", es: "Comando enviado", de: "Befehl gesendet", pt: "Comando enviado" },
  "toast.captured": { en: "Screenshot captured", fr: "Capture prise", es: "Captura realizada", de: "Screenshot aufgenommen", pt: "Captura salva" },
  "toast.error": { en: "Error", fr: "Erreur", es: "Error", de: "Fehler", pt: "Erro" },
  "toast.agent_offline": {
    en: "Agent offline or perception unavailable",
    fr: "Agent hors-ligne ou perception indisponible",
    es: "Agente desconectado o percepción no disponible",
    de: "Agent offline oder Wahrnehmung nicht verfügbar",
    pt: "Agente offline ou percepção indisponível"
  },
};/**
 * Dashboard i18n — bilingual EN/FR support.
 * Same string catalog as the Python agent (utils/i18n.py).
 * Language is detected from browser locale, stored in localStorage, switchable via the language toggle.
 */

export type Lang = "en" | "fr";

const STRINGS: Record<string, Record<Lang, string>> = {
  // Header
  "dash.title": { en: "Z.AGENT — Desktop Control Center", fr: "Z.AGENT — Centre de contrôle bureau" },
  "dash.subtitle": { en: "Desktop Control Center", fr: "Centre de contrôle bureau" },
  "dash.connected": { en: "WS connected", fr: "WS connecté" },
  "dash.offline": { en: "Offline", fr: "Hors-ligne" },

  // State labels
  "state.idle": { en: "Idle", fr: "En attente" },
  "state.planning": { en: "Planning", fr: "Planification" },
  "state.executing": { en: "Executing", fr: "Exécution" },
  "state.paused": { en: "Paused", fr: "En pause" },
  "state.error": { en: "Error", fr: "Erreur" },
  "state.stopped": { en: "Stopped", fr: "Arrêté" },

  // Stats labels
  "label.state": { en: "State", fr: "État" },
  "label.queue": { en: "Queue", fr: "File" },
  "label.uptime": { en: "Uptime", fr: "Uptime" },
  "label.logs": { en: "Logs", fr: "Logs" },

  // Memory card
  "dash.memory": { en: "Memory", fr: "Mémoire" },
  "dash.facts": { en: "Persistent facts", fr: "Faits persistants" },
  "dash.preferences": { en: "Preferences", fr: "Préférences" },
  "dash.shortcuts": { en: "Learned shortcuts", fr: "Raccourcis appris" },
  "dash.recent_tasks": { en: "Recent tasks", fr: "Dernières tâches" },
  "misc.no_recent_tasks": { en: "No recent tasks", fr: "Aucune tâche récente" },

  // Task submission
  "dash.submit_task": { en: "Submit a task", fr: "Soumettre une tâche" },
  "dash.task_placeholder": {
    en: "Describe the task in natural language. Ex: \"Sort my downloads by file type and send me a summary by email\"",
    fr: "Décris la tâche en langage naturel. Ex: « Tri mes téléchargements par type et envoie-moi un résumé par mail »",
  },
  "dash.send": { en: "Send", fr: "Envoyer" },
  "dash.sending": { en: "Sending...", fr: "Envoi..." },
  "dash.current_task": { en: "Current task", fr: "Tâche en cours" },
  "label.via": { en: "via", fr: "via" },

  // Tabs
  "dash.tasks": { en: "Tasks", fr: "Tâches" },
  "dash.logs": { en: "Logs", fr: "Logs" },
  "dash.screenshots": { en: "Screenshots", fr: "Captures" },

  // Empty states
  "dash.no_tasks": {
    en: "No tasks yet. Submit one above to get started.",
    fr: "Aucune tâche. Soumets-en une ci-dessus pour commencer.",
  },
  "dash.no_logs": {
    en: "No logs. Connect the Python agent to see real-time logs.",
    fr: "Aucun log. Connectez l'agent Python pour voir les logs en temps réel.",
  },
  "dash.no_screenshots": { en: "No screenshots available.", fr: "Aucune capture disponible." },

  // Quick tasks
  "dash.quick_sort_downloads": { en: "Sort Downloads", fr: "Trier Téléchargements" },
  "dash.quick_read_emails": { en: "Read unread emails", fr: "Lire emails non lus" },
  "dash.quick_events": { en: "Upcoming events", fr: "Prochains événements" },
  "dash.quick_describe_screen": { en: "Describe screen", fr: "Décrire l'écran" },
  "dash.quick_system_info": { en: "System info", fr: "Infos système" },
  "dash.quick_screenshot": { en: "Take screenshot", fr: "Capture d'écran" },

  // Modules
  "dash.modules": { en: "Active modules", fr: "Modules actifs" },
  "module.screen": { en: "Screen", fr: "Écran" },
  "module.files": { en: "Files", fr: "Fichiers" },
  "module.email": { en: "Email", fr: "Email" },
  "module.calendar": { en: "Calendar", fr: "Calendrier" },
  "module.browser": { en: "Browser", fr: "Navigateur" },
  "module.system": { en: "System", fr: "Système" },
  "module.windows": { en: "Windows", fr: "Windows" },
  "module.slack": { en: "Slack", fr: "Slack" },

  // VLM card
  "dash.vlm_perception": { en: "VLM Perception", fr: "Perception VLM" },
  "dash.vlm_description": {
    en: "GLM-4V analyzes the screen to understand the UI and locate elements.",
    fr: "GLM-4V analyse l'écran pour comprendre l'interface et localiser les éléments.",
  },
  "dash.analyze_screen": { en: "Analyze screen", fr: "Analyser l'écran" },
  "dash.capture_now": { en: "Capture now", fr: "Capturer maintenant" },

  // Tip card
  "misc.tip_title": { en: "Tip", fr: "Astuce" },
  "misc.tip_body": {
    en: "The agent runs in full autonomy. You can send tasks from Telegram when you're away — it plans, executes, and notifies you of the result.",
    fr: "L'agent fonctionne en autonomie complète. Tu peux lui envoyer des tâches depuis Telegram quand tu es absent — il planifie, exécute et te notifie du résultat.",
  },

  // Plan detail
  "dash.plan_label": { en: "Plan", fr: "Plan" },
  "dash.steps_label": { en: "steps", fr: "étapes" },

  // Toasts
  "toast.task_sent": { en: "Task sent", fr: "Tâche envoyée" },
  "toast.command_sent": { en: "Command sent", fr: "Commande envoyée" },
  "toast.captured": { en: "Screenshot captured", fr: "Capture prise" },
  "toast.error": { en: "Error", fr: "Erreur" },
  "toast.agent_offline": {
    en: "Agent offline or perception unavailable",
    fr: "Agent hors-ligne ou perception indisponible",
  },
export type Lang = "en" | "fr" | "es" | "de" | "pt";

export function detectBrowserLang(): Lang {
  if (typeof window === "undefined") return "en";
  const stored = localStorage.getItem("zda-lang");
  if (stored === "en" || stored === "fr" || stored === "es" || stored === "de" || stored === "pt") {
    return stored as Lang;
  }
  const browser = navigator.language.split("-")[0].toLowerCase();
  if (browser === "fr" || browser === "es" || browser === "de" || browser === "pt") {
    return browser as Lang;
  }
  return "en";
}

export function setStoredLang(lang: Lang) {
  if (typeof window !== "undefined") {
    localStorage.setItem("zda-lang", lang);
  }
}

export function t(key: string, lang: Lang, vars?: Record<string, string | number>): string {
  const entry = STRINGS[key];
  if (!entry) return key;
  let text = entry[lang] || entry.en || key;
  if (vars) {
    for (const [k, v] of Object.entries(vars)) {
      text = text.replace(new RegExp(`\\{${k}\\}`, "g"), String(v));
    }
  }
  return text;
}

export const STATE_LABELS: Record<string, Record<Lang, string>> = {
  idle: { en: "Idle", fr: "En attente", es: "Inactivo", de: "Im Leerlauf", pt: "Inativo" },
  planning: { en: "Planning", fr: "Planification", es: "Planificando", de: "Planung", pt: "Planejando" },
  executing: { en: "Executing", fr: "Exécution", es: "Ejecutando", de: "Ausführen", pt: "Executando" },
  paused: { en: "Paused", fr: "En pause", es: "Pausado", de: "Pausiert", pt: "Pausado" },
  error: { en: "Error", fr: "Erreur", es: "Error", de: "Fehler", pt: "Erro" },
  stopped: { en: "Stopped", fr: "Arrêté", es: "Detenido", de: "Gestoppt", pt: "Parado" },
};

export function stateLabel(state: string, lang: Lang): string {
  return STATE_LABELS[state]?.[lang] || state;
}
