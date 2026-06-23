"""
Internationalization (i18n) — bilingual EN/FR support.

Detects user language from:
  1. config.yaml agent.language
  2. Telegram user language_code
  3. First message language (heuristic)
  4. System locale (fallback)

Exposes get_text(key, lang?) -> str for all UI strings.
"""
import os
import locale
from typing import Optional, Dict

from utils.logger import get_logger

log = get_logger("i18n")


# === String catalog ===
# Each key has an 'en' and 'fr' variant.
# To add a new language: copy the 'en' dict, translate values, add the lang code.
STRINGS: Dict[str, Dict[str, str]] = {
    # === Agent states ===
    "state.idle": {
        "en": "Idle",
        "fr": "En attente",
    },
    "state.planning": {
        "en": "Planning",
        "fr": "Planification",
    },
    "state.executing": {
        "en": "Executing",
        "fr": "Exécution",
    },
    "state.paused": {
        "en": "Paused",
        "fr": "En pause",
    },
    "state.error": {
        "en": "Error",
        "fr": "Erreur",
    },
    "state.stopped": {
        "en": "Stopped",
        "fr": "Arrêté",
    },

    # === Telegram bot messages ===
    "tg.welcome": {
        "en": "🤖 *Z.AGENT online*\n\nStatus: {status}\n\nSend a task in natural language or type /help",
        "fr": "🤖 *Z.AGENT en ligne*\n\nStatut: {status}\n\nEnvoie une tâche en langage naturel ou tape /help",
    },
    "tg.task_received": {
        "en": "✅ Task received\nID: `{task_id}`\nRequest: {request}\n\n⏳ Processing...",
        "fr": "✅ Tâche reçue\nID: `{task_id}`\nDemande: {request}\n\n⏳ Traitement...",
    },
    "tg.task_complete": {
        "en": "{emoji} *Task completed*\n\nSteps: {ok}/{total} succeeded",
        "fr": "{emoji} *Tâche terminée*\n\nÉtapes: {ok}/{total} réussies",
    },
    "tg.task_failed_step": {
        "en": "❌ Failed step {step}: {error}",
        "fr": "❌ Échec étape {step}: {error}",
    },
    "tg.not_authorized": {
        "en": "❌ You are not authorized to use this agent.",
        "fr": "❌ Vous n'êtes pas autorisé à utiliser cet agent.",
    },
    "tg.agent_not_initialized": {
        "en": "❌ Agent not initialized",
        "fr": "❌ Agent non initialisé",
    },
    "tg.queue_empty": {
        "en": "🗑️ Queue cleared",
        "fr": "🗑️ File vidée",
    },
    "tg.paused": {
        "en": "⏸️ Agent paused",
        "fr": "⏸️ Agent en pause",
    },
    "tg.resumed": {
        "en": "▶️ Agent resumed",
        "fr": "▶️ Agent repris",
    },
    "tg.screenshot_caption": {
        "en": "📸 Screenshot",
        "fr": "📸 Capture d'écran",
    },
    "tg.screenshot_failed": {
        "en": "❌ Screenshot failed",
        "fr": "❌ Capture impossible",
    },

    # === Help text ===
    "tg.help.title": {
        "en": "🤖 *Z.AGENT — Desktop Assistant*",
        "fr": "🤖 *Z.AGENT — Assistant de bureau*",
    },
    "tg.help.commands": {
        "en": "*Quick commands:*",
        "fr": "*Commandes rapides:*",
    },
    "tg.help.modules": {
        "en": "*Modules:*",
        "fr": "*Modules:*",
    },
    "tg.help.free_text": {
        "en": "*Free text:*\nJust send your request in natural language, the agent will plan and execute it.",
        "fr": "*Mode libre:*\nEnvoie simplement ta demande en langage naturel, l'agent la planifiera et l'exécutera.",
    },
    "tg.help.examples": {
        "en": "*Examples:*\n• \"Sort my downloads by file type\"\n• \"Send an email to alice@example.com to confirm tomorrow's meeting\"\n• \"Take a screenshot and tell me what's on screen\"\n• \"Open Gmail in the browser\"",
        "fr": "*Exemples:*\n• \"Tri mes téléchargements par type de fichier\"\n• \"Envoie un mail à alice@example.com pour confirmer la réunion de demain\"\n• \"Capture l'écran et dis-moi ce qu'il y a dessus\"\n• \"Ouvre Gmail dans le navigateur\"",
    },

    # === CLI ===
    "cli.welcome": {
        "en": "🤖 Z.AGENT — CLI mode\nType your request in natural language, or 'quit' to exit.\n",
        "fr": "🤖 Z.AGENT — Mode CLI\nTape ta demande en langage naturel, ou 'quit' pour quitter.\n",
    },
    "cli.prompt": {
        "en": "👤> ",
        "fr": "👤> ",
    },
    "cli.goodbye": {
        "en": "👋 Goodbye!",
        "fr": "👋 Au revoir!",
    },
    "cli.task_submitted": {
        "en": "✅ Task {task_id} submitted, processing...",
        "fr": "✅ Tâche {task_id} soumise, traitement...",
    },
    "cli.result_header": {
        "en": "📊 Result:",
        "fr": "📊 Résultat:",
    },
    "cli.steps_label": {
        "en": "   Steps: {ok}/{total}",
        "fr": "   Étapes: {ok}/{total}",
    },
    "cli.waiting": {
        "en": "⏳ Task {task_id} submitted, waiting for completion...",
        "fr": "⏳ Tâche {task_id} soumise, attente du résultat...",
    },
    "cli.timeout": {
        "en": "⏱️ Task timed out after 120s",
        "fr": "⏱️ Tâche expirée après 120s",
    },

    # === Notifications (proactive push to Telegram) ===
    "notif.task_started": {
        "en": "🚀 *Task started*: {request}",
        "fr": "🚀 *Tâche démarrée*: {request}",
    },
    "notif.task_completed": {
        "en": "✅ *Task completed*: {request}\nResult: {ok}/{total} steps succeeded",
        "fr": "✅ *Tâche terminée*: {request}\nRésultat: {ok}/{total} étapes réussies",
    },
    "notif.task_failed": {
        "en": "❌ *Task failed*: {request}\nError: {error}",
        "fr": "❌ *Tâche échouée*: {request}\nErreur: {error}",
    },
    "notif.calendar_reminder": {
        "en": "🔔 *Reminder*: {title}\n📅 In {minutes} minutes\n📍 {location}",
        "fr": "🔔 *Rappel*: {title}\n📅 Dans {minutes} minutes\n📍 {location}",
    },
    "notif.system_alert": {
        "en": "⚠️ *System alert*: {message}",
        "fr": "⚠️ *Alerte système*: {message}",
    },
    "notif.email_received": {
        "en": "📧 *New email from* {sender}\nSubject: {subject}",
        "fr": "📧 *Nouvel email de* {sender}\nSujet: {subject}",
    },
    "notif.error": {
        "en": "❌ *Error*: {message}",
        "fr": "❌ *Erreur*: {message}",
    },
    "notif.disk_full": {
        "en": "💾 *Disk almost full*: {pct}% used on {drive}",
        "fr": "💾 *Disque presque plein*: {pct}% utilisé sur {drive}",
    },
    "notif.high_cpu": {
        "en": "🔥 *High CPU*: {pct}% for {minutes} min — top process: {proc}",
        "fr": "🔥 *CPU élevé*: {pct}% pendant {minutes} min — processus: {proc}",
    },

    # === Dashboard labels ===
    "dash.title": {
        "en": "Z.AGENT — Desktop Control Center",
        "fr": "Z.AGENT — Centre de contrôle bureau",
    },
    "dash.subtitle": {
        "en": "Desktop Control Center",
        "fr": "Centre de contrôle bureau",
    },
    "dash.connected": {
        "en": "WS connected",
        "fr": "WS connecté",
    },
    "dash.offline": {
        "en": "Offline",
        "fr": "Hors-ligne",
    },
    "dash.submit_task": {
        "en": "Submit a task",
        "fr": "Soumettre une tâche",
    },
    "dash.task_placeholder": {
        "en": "Describe the task in natural language. Ex: \"Sort my downloads by file type and send me a summary by email\"",
        "fr": "Décris la tâche en langage naturel. Ex: « Tri mes téléchargements par type et envoie-moi un résumé par mail »",
    },
    "dash.send": {
        "en": "Send",
        "fr": "Envoyer",
    },
    "dash.sending": {
        "en": "Sending...",
        "fr": "Envoi...",
    },
    "dash.current_task": {
        "en": "Current task",
        "fr": "Tâche en cours",
    },
    "dash.tasks": {
        "en": "Tasks",
        "fr": "Tâches",
    },
    "dash.logs": {
        "en": "Logs",
        "fr": "Logs",
    },
    "dash.screenshots": {
        "en": "Screenshots",
        "fr": "Captures",
    },
    "dash.memory": {
        "en": "Memory",
        "fr": "Mémoire",
    },
    "dash.facts": {
        "en": "Persistent facts",
        "fr": "Faits persistants",
    },
    "dash.preferences": {
        "en": "Preferences",
        "fr": "Préférences",
    },
    "dash.shortcuts": {
        "en": "Learned shortcuts",
        "fr": "Raccourcis appris",
    },
    "dash.recent_tasks": {
        "en": "Recent tasks",
        "fr": "Dernières tâches",
    },
    "dash.no_tasks": {
        "en": "No tasks yet. Submit one above to get started.",
        "fr": "Aucune tâche. Soumets-en une ci-dessus pour commencer.",
    },
    "dash.no_logs": {
        "en": "No logs. Connect the Python agent to see real-time logs.",
        "fr": "Aucun log. Connectez l'agent Python pour voir les logs en temps réel.",
    },
    "dash.no_screenshots": {
        "en": "No screenshots available.",
        "fr": "Aucune capture disponible.",
    },
    "dash.modules": {
        "en": "Active modules",
        "fr": "Modules actifs",
    },
    "dash.vlm_perception": {
        "en": "VLM Perception",
        "fr": "Perception VLM",
    },
    "dash.vlm_description": {
        "en": "GLM-4V analyzes the screen to understand the UI and locate elements.",
        "fr": "GLM-4V analyse l'écran pour comprendre l'interface et localiser les éléments.",
    },
    "dash.analyze_screen": {
        "en": "Analyze screen",
        "fr": "Analyser l'écran",
    },
    "dash.capture_now": {
        "en": "Capture now",
        "fr": "Capturer maintenant",
    },
    "dash.quick_tasks": {
        "en": "Sort Downloads",
        "fr": "Trier Téléchargements",
    },
    "dash.quick_read_emails": {
        "en": "Read unread emails",
        "fr": "Lire emails non lus",
    },
    "dash.quick_events": {
        "en": "Upcoming events",
        "fr": "Prochains événements",
    },
    "dash.quick_describe_screen": {
        "en": "Describe screen",
        "fr": "Décrire l'écran",
    },
    "dash.quick_system_info": {
        "en": "System info",
        "fr": "Infos système",
    },
    "dash.quick_screenshot": {
        "en": "Take screenshot",
        "fr": "Capture d'écran",
    },

    # === Module names ===
    "module.screen": {"en": "Screen", "fr": "Écran"},
    "module.files": {"en": "Files", "fr": "Fichiers"},
    "module.email": {"en": "Email", "fr": "Email"},
    "module.calendar": {"en": "Calendar", "fr": "Calendrier"},
    "module.browser": {"en": "Browser", "fr": "Navigateur"},
    "module.system": {"en": "System", "fr": "Système"},
    "module.slack": {"en": "Slack", "fr": "Slack"},

    # === State labels ===
    "label.state": {"en": "State", "fr": "État"},
    "label.queue": {"en": "Queue", "fr": "File"},
    "label.uptime": {"en": "Uptime", "fr": "Uptime"},
    "label.via": {"en": "via", "fr": "via"},

    # === Misc ===
    "misc.no_recent_tasks": {
        "en": "No recent tasks",
        "fr": "Aucune tâche récente",
    },
    "misc.tip_title": {
        "en": "Tip",
        "fr": "Astuce",
    },
    "misc.tip_body": {
        "en": "The agent runs in full autonomy. You can send tasks from Telegram when you're away — it plans, executes, and notifies you of the result.",
        "fr": "L'agent fonctionne en autonomie complète. Tu peux lui envoyer des tâches depuis Telegram quand tu es absent — il planifie, exécute et te notifie du résultat.",
    },
}


# === Language detection ===

def _detect_system_lang() -> str:
    """Detect system locale language."""
    try:
        loc = locale.getlocale()[0] or locale.getdefaultlocale()[0] or "en"
        lang = loc.split("_")[0].lower()
        return "fr" if lang == "fr" else "en"
    except Exception:
        return "en"


def _detect_text_lang(text: str) -> str:
    """Heuristic: detect if text is French or English based on common words."""
    text_lower = text.lower()
    french_markers = [" le ", " la ", " les ", " un ", " une ", " et ", " ou ", " mon ", " ma ",
                      " mes ", " tu ", " vous ", " je ", " il ", " elle ", " nous ", " ils ",
                      "avec", "pour", "dans", "sur", "que", "qui", "comment", "où", "quand",
                      "merci", "bonjour", "salut", "svp", "s'il", "plait", "é", "è", "à", "ç"]
    english_markers = [" the ", " a ", " an ", " and ", " or ", " my ", " your ", " you ",
                       " i ", " he ", " she ", " we ", " they ", "with", "for", "in", "on",
                       "that", "who", "how", "where", "when", "thanks", "hello", "hi",
                       "please", "what", "why"]

    fr_count = sum(1 for m in french_markers if m in text_lower)
    en_count = sum(1 for m in english_markers if m in text_lower)

    if fr_count > en_count:
        return "fr"
    return "en"


# === Global config ===
_default_lang: str = "en"


def init_i18n(config: dict):
    """Initialize i18n from config."""
    global _default_lang
    lang = config.get("agent", {}).get("language", "auto").lower()
    if lang == "auto" or lang not in ("en", "fr"):
        lang = _detect_system_lang()
    _default_lang = lang
    log.info(f"i18n initialized — default language: {_default_lang}")


def get_default_lang() -> str:
    return _default_lang


def set_default_lang(lang: str):
    global _default_lang
    if lang in ("en", "fr"):
        _default_lang = lang


def detect_lang(text: str, fallback: Optional[str] = None) -> str:
    """Detect language of a user message."""
    if not text or len(text) < 5:
        return fallback or _default_lang
    detected = _detect_text_lang(text)
    return detected


def get_text(key: str, lang: Optional[str] = None, **kwargs) -> str:
    """Get a translated string.

    Args:
        key: String key (e.g. "tg.welcome")
        lang: Language code ('en' or 'fr'). Defaults to global default.
        **kwargs: Format variables for the string.

    Returns:
        Translated and formatted string. Falls back to English if key/lang missing.
    """
    if lang is None:
        lang = _default_lang

    entry = STRINGS.get(key)
    if not entry:
        log.warning(f"Missing i18n key: {key}")
        return key

    text = entry.get(lang) or entry.get("en") or key

    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError) as e:
            log.warning(f"i18n format error for key '{key}': {e}")

    return text


def t(key: str, lang: Optional[str] = None, **kwargs) -> str:
    """Alias for get_text."""
    return get_text(key, lang, **kwargs)
