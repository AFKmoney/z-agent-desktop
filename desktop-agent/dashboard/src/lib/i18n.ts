/**
 * Dashboard i18n — multilingual support (EN, FR, ES, DE, PT).
 * Same string catalog as the Python agent (utils/i18n.py).
 * Language is detected from browser locale, stored in localStorage, switchable via the language selector.
 */

export type Lang = "en" | "fr" | "es" | "de" | "pt";

const STRINGS: Record<string, Partial<Record<Lang, string>> & { en: string }> = {
  // Navigation
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
  "label.via": { en: "via", fr: "via", es: "vía", de: "via", pt: "via" },

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
    en: "Describe the task in natural language. Ex: \"Sort my downloads by file type and send me a summary by email\"",
    fr: "Décris la tâche en langage naturel. Ex: « Tri mes téléchargements par type et envoie-moi un résumé par mail »",
    es: "Describe la tarea en lenguaje natural. Ej: \"Organiza mis descargas por tipo de archivo\"",
    de: "Beschreibe die Aufgabe in natürlicher Sprache. Z.B.: \"Sortiere meine Downloads nach Dateityp\"",
    pt: "Descreva a tarefa em linguagem natural. Ex: \"Organize meus downloads por tipo de arquivo\"",
  },
  "dash.send": { en: "Send", fr: "Envoyer", es: "Enviar", de: "Senden", pt: "Enviar" },
  "dash.sending": { en: "Sending...", fr: "Envoi...", es: "Enviando...", de: "Senden...", pt: "Enviando..." },
  "dash.current_task": { en: "Current task", fr: "Tâche en cours", es: "Tarea actual", de: "Aktuelle Aufgabe", pt: "Tarefa atual" },

  // Tabs
  "dash.tasks": { en: "Tasks", fr: "Tâches", es: "Tareas", de: "Aufgaben", pt: "Tarefas" },
  "dash.logs": { en: "Logs", fr: "Logs", es: "Registros", de: "Protokolle", pt: "Logs" },
  "dash.screenshots": { en: "Screenshots", fr: "Captures", es: "Capturas", de: "Screenshots", pt: "Capturas" },

  // Empty states
  "dash.no_tasks": {
    en: "No tasks yet. Submit one above to get started.",
    fr: "Aucune tâche. Soumets-en une ci-dessus pour commencer.",
    es: "Sin tareas. Envía una arriba para empezar.",
    de: "Keine Aufgaben. Reiche oben eine ein um zu beginnen.",
    pt: "Sem tarefas. Envie uma acima para começar.",
  },
  "dash.no_logs": {
    en: "No logs. Connect the Python agent to see real-time logs.",
    fr: "Aucun log. Connectez l'agent Python pour voir les logs en temps réel.",
    es: "Sin registros. Conecta el agente Python para ver registros en tiempo real.",
    de: "Keine Protokolle. Verbinde den Python-Agenten für Echtzeit-Protokolle.",
    pt: "Sem logs. Conecte o agente Python para ver logs em tempo real.",
  },
  "dash.no_screenshots": {
    en: "No screenshots available.",
    fr: "Aucune capture disponible.",
    es: "Sin capturas disponibles.",
    de: "Keine Screenshots verfügbar.",
    pt: "Sem capturas de tela disponíveis.",
  },

  // Quick tasks
  "dash.quick_sort_downloads": { en: "Sort Downloads", fr: "Trier Téléchargements", es: "Ordenar Descargas", de: "Downloads sortieren", pt: "Ordenar Downloads" },
  "dash.quick_read_emails": { en: "Read unread emails", fr: "Lire emails non lus", es: "Leer correos no leídos", de: "Ungelesene E-Mails lesen", pt: "Ler emails não lidos" },
  "dash.quick_events": { en: "Upcoming events", fr: "Prochains événements", es: "Próximos eventos", de: "Anstehende Termine", pt: "Próximos eventos" },
  "dash.quick_describe_screen": { en: "Describe screen", fr: "Décrire l'écran", es: "Describir pantalla", de: "Bildschirm beschreiben", pt: "Descrever tela" },
  "dash.quick_system_info": { en: "System info", fr: "Infos système", es: "Información del sistema", de: "Systeminfo", pt: "Informações do sistema" },
  "dash.quick_screenshot": { en: "Take screenshot", fr: "Capture d'écran", es: "Capturar pantalla", de: "Screenshot machen", pt: "Capturar tela" },

  // Modules
  "dash.modules": { en: "Active modules", fr: "Modules actifs", es: "Módulos activos", de: "Aktive Module", pt: "Módulos ativos" },
  "module.screen": { en: "Screen", fr: "Écran", es: "Pantalla", de: "Bildschirm", pt: "Tela" },
  "module.files": { en: "Files", fr: "Fichiers", es: "Archivos", de: "Dateien", pt: "Arquivos" },
  "module.email": { en: "Email", fr: "Email", es: "Correo", de: "E-Mail", pt: "Email" },
  "module.calendar": { en: "Calendar", fr: "Calendrier", es: "Calendario", de: "Kalender", pt: "Calendário" },
  "module.browser": { en: "Browser", fr: "Navigateur", es: "Navegador", de: "Browser", pt: "Navegador" },
  "module.system": { en: "System", fr: "Système", es: "Sistema", de: "System", pt: "Sistema" },
  "module.windows": { en: "Windows", fr: "Windows", es: "Windows", de: "Windows", pt: "Windows" },
  "module.slack": { en: "Slack", fr: "Slack", es: "Slack", de: "Slack", pt: "Slack" },

  // VLM card
  "dash.vlm_perception": { en: "VLM Perception", fr: "Perception VLM", es: "Percepción VLM", de: "VLM-Wahrnehmung", pt: "Percepção VLM" },
  "dash.vlm_description": {
    en: "GLM-4V analyzes the screen to understand the UI and locate elements.",
    fr: "GLM-4V analyse l'écran pour comprendre l'interface et localiser les éléments.",
    es: "GLM-4V analiza la pantalla para comprender la interfaz y localizar elementos.",
    de: "GLM-4V analysiert den Bildschirm um die UI zu verstehen und Elemente zu finden.",
    pt: "GLM-4V analisa a tela para compreender a interface e localizar elementos.",
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
    pt: "O agente é totalmente autônomo. Você pode enviar tarefas do Telegram quando estiver fora — ele planeja, executa e notifica você.",
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
    pt: "Agente offline ou percepção indisponível",
  },
};

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
