/**
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
};

export function detectBrowserLang(): Lang {
  if (typeof window === "undefined") return "en";
  const stored = localStorage.getItem("zda-lang");
  if (stored === "en" || stored === "fr") return stored;
  const browser = (navigator.language || "en").slice(0, 2).toLowerCase();
  return browser === "fr" ? "fr" : "en";
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
  idle: { en: "Idle", fr: "En attente" },
  planning: { en: "Planning", fr: "Planification" },
  executing: { en: "Executing", fr: "Exécution" },
  paused: { en: "Paused", fr: "En pause" },
  error: { en: "Error", fr: "Erreur" },
  stopped: { en: "Stopped", fr: "Arrêté" },
};

export function stateLabel(state: string, lang: Lang): string {
  return STATE_LABELS[state]?.[lang] || state;
}
