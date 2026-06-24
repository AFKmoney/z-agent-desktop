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
    "state.idle": {
        "en": "Idle",
        "fr": "En attente",
        "es": "Inactivo",
        "de": "Im Leerlauf",
        "pt": "Inativo",
    },
    "state.planning": {
        "en": "Planning",
        "fr": "Planification",
        "es": "Planificando",
        "de": "Planung",
        "pt": "Planejando",
    },
    "state.executing": {
        "en": "Executing",
        "fr": "Exécution",
        "es": "Ejecutando",
        "de": "Ausführen",
        "pt": "Executando",
    },
    "state.paused": {
        "en": "Paused",
        "fr": "En pause",
        "es": "Pausado",
        "de": "Pausiert",
        "pt": "Pausado",
    },
    "state.error": {
        "en": "Error",
        "fr": "Erreur",
        "es": "Error",
        "de": "Fehler",
        "pt": "Erro",
    },
    "state.stopped": {
        "en": "Stopped",
        "fr": "Arrêté",
        "es": "Detenido",
        "de": "Gestoppt",
        "pt": "Parado",
    },
    "tg.welcome": {
        "en": "🤖 *Z.AGENT online*\n\nStatus: {status}\n\nSend a task in natural language or type /help",
        "fr": "🤖 *Z.AGENT en ligne*\n\nStatut: {status}\n\nEnvoie une tâche en langage naturel ou tape /help",
        "es": "🤖 *Z.AGENT en línea*\n\nEstado: {status}\n\nEnvía una tarea en lenguaje natural o escribe /help",
        "de": "🤖 *Z.AGENT online*\n\nStatus: {status}\n\nSende eine Aufgabe in natürlicher Sprache oder tippe /help",
        "pt": "🤖 *Z.AGENT online*\n\nStatus: {status}\n\nEnvie uma tarefa em linguagem natural ou digite /help",
    },
    "tg.task_received": {
        "en": "✅ Task received\nID: `{task_id}`\nRequest: {request}\n\n⏳ Processing...",
        "fr": "✅ Tâche reçue\nID: `{task_id}`\nDemande: {request}\n\n⏳ Traitement...",
        "es": "✅ Tarea recibida\nID: `{task_id}`\nSolicitud: {request}\n\n⏳ Procesando...",
        "de": "✅ Aufgabe empfangen\nID: `{task_id}`\nAnfrage: {request}\n\n⏳ Verarbeitung...",
        "pt": "✅ Tarefa recebida\nID: `{task_id}`\nSolicitação: {request}\n\n⏳ Processando...",
    },
    "tg.task_complete": {
        "en": "{emoji} *Task completed*\n\nSteps: {ok}/{total} succeeded",
        "fr": "{emoji} *Tâche terminée*\n\nÉtapes: {ok}/{total} réussies",
        "es": "{emoji} *Tarea completada*\n\nPasos: {ok}/{total} exitosos",
        "de": "{emoji} *Aufgabe abgeschlossen*\n\nSchritte: {ok}/{total} erfolgreich",
        "pt": "{emoji} *Tarefa concluída*\n\nPassos: {ok}/{total} bem-sucedidos",
    },
    "tg.task_failed_step": {
        "en": "❌ Failed step {step}: {error}",
        "fr": "❌ Échec étape {step}: {error}",
        "es": "❌ Falló el paso {step}: {error}",
        "de": "❌ Fehler bei Schritt {step}: {error}",
        "pt": "❌ Falha no passo {step}: {error}",
    },
    "tg.not_authorized": {
        "en": "❌ You are not authorized to use this agent.",
        "fr": "❌ Vous n'êtes pas autorisé à utiliser cet agent.",
        "es": "❌ No estás autorizado para usar este agente.",
        "de": "❌ Sie sind nicht berechtigt, diesen Agenten zu verwenden.",
        "pt": "❌ Você não está autorizado a usar este agente.",
    },
    "tg.agent_not_initialized": {
        "en": "❌ Agent not initialized",
        "fr": "❌ Agent non initialisé",
        "es": "❌ Agente no inicializado",
        "de": "❌ Agent nicht initialisiert",
        "pt": "❌ Agente não inicializado",
    },
    "tg.queue_empty": {
        "en": "🗑️ Queue cleared",
        "fr": "🗑️ File vidée",
        "es": "🗑️ Cola vaciada",
        "de": "🗑️ Warteschlange geleert",
        "pt": "🗑️ Fila limpa",
    },
    "tg.paused": {
        "en": "⏸️ Agent paused",
        "fr": "⏸️ Agent en pause",
        "es": "⏸️ Agente pausado",
        "de": "⏸️ Agent pausiert",
        "pt": "⏸️ Agente pausado",
    },
    "tg.resumed": {
        "en": "▶️ Agent resumed",
        "fr": "▶️ Agent repris",
        "es": "▶️ Agente reanudado",
        "de": "▶️ Agent fortgesetzt",
        "pt": "▶️ Agente retomado",
    },
    "tg.screenshot_caption": {
        "en": "📸 Screenshot taken at {time}",
        "fr": "📸 Capture prise à {time}",
        "es": "📸 Captura de pantalla tomada a las {time}",
        "de": "📸 Screenshot aufgenommen um {time}",
        "pt": "📸 Captura de tela tirada às {time}",
    },
    "tg.screenshot_failed": {
        "en": "❌ Failed to take screenshot: {error}",
        "fr": "❌ Échec de la capture d'écran: {error}",
        "es": "❌ Error al tomar captura de pantalla: {error}",
        "de": "❌ Screenshot fehlgeschlagen: {error}",
        "pt": "❌ Falha ao tirar captura de tela: {error}",
    },
    "tg.help.title": {
        "en": "🤖 *Z.AGENT — Desktop Assistant*",
        "fr": "🤖 *Z.AGENT — Assistant de bureau*",
        "es": "🤖 *Z.AGENT — Asistente de escritorio*",
        "de": "🤖 *Z.AGENT — Desktop-Assistent*",
        "pt": "🤖 *Z.AGENT — Assistente de Desktop*",
    },
    "tg.help.commands": {
        "en": "*Quick commands:*",
        "fr": "*Commandes rapides:*",
        "es": "*Comandos rápidos:*",
        "de": "*Schnellbefehle:*",
        "pt": "*Comandos rápidos:*",
    },
    "tg.help.modules": {
        "en": "*Available modules:*",
        "fr": "*Modules disponibles:*",
        "es": "*Módulos disponibles:*",
        "de": "*Verfügbare Module:*",
        "pt": "*Módulos disponíveis:*",
    },
    "tg.help.free_text": {
        "en": "*Free mode:*\nJust send your request in natural language, the agent will plan and execute it.",
        "fr": "*Mode libre:*\nEnvoie simplement ta demande en langage naturel, l'agent la planifiera et l'exécutera.",
        "es": "*Modo libre:*\nSimplemente envía tu solicitud en lenguaje natural, el agente la planificará y ejecutará.",
        "de": "*Freier Modus:*\nSende einfach deine Anfrage in natürlicher Sprache, der Agent plant und führt sie aus.",
        "pt": "*Modo livre:*\nBasta enviar sua solicitação em linguagem natural, o agente irá planejar e executá-la.",
    },
    "tg.help.examples": {
        "en": "*Examples:*\n• \"Sort my downloads by file type\"\n• \"Send an email to alice@example.com to confirm tomorrow's meeting\"\n• \"Take a screenshot and tell me what's on screen\"\n• \"Open Gmail in the browser\"",
        "fr": "*Exemples:*\n• \"Tri mes téléchargements par type de fichier\"\n• \"Envoie un mail à alice@example.com pour confirmer la réunion de demain\"\n• \"Capture l'écran et dis-moi ce qu'il y a dessus\"\n• \"Ouvre Gmail dans le navigateur\"",
        "es": "*Ejemplos:*\n• \"Ordena mis descargas por tipo de archivo\"\n• \"Envía un correo a alice@example.com para confirmar la reunión de mañana\"\n• \"Toma una captura de pantalla y dime qué hay en ella\"\n• \"Abre Gmail en el navegador\"",
        "de": "*Beispiele:*\n• \"Sortiere meine Downloads nach Dateityp\"\n• \"Sende eine E-Mail an alice@example.com, um das morgige Meeting zu bestätigen\"\n• \"Mach einen Screenshot und sag mir, was auf dem Bildschirm ist\"\n• \"Öffne Gmail im Browser\"",
        "pt": "*Exemplos:*\n• \"Organize meus downloads por tipo de arquivo\"\n• \"Envie um e-mail para alice@example.com para confirmar a reunião de amanhã\"\n• \"Tire uma captura de tela e me diga o que está na tela\"\n• \"Abra o Gmail no navegador\"",
    },
    "cli.welcome": {
        "en": "🤖 Z.AGENT — CLI mode\nType your request in natural language, or 'quit' to exit.\n",
        "fr": "🤖 Z.AGENT — Mode CLI\nTape ta demande en langage naturel, ou 'quit' pour quitter.\n",
        "es": "🤖 Z.AGENT — Modo CLI\nEscribe tu solicitud en lenguaje natural, o 'quit' para salir.\n",
        "de": "🤖 Z.AGENT — CLI-Modus\nTippe deine Anfrage in natürlicher Sprache ein oder 'quit' zum Beenden.\n",
        "pt": "🤖 Z.AGENT — Modo CLI\nDigite sua solicitação em linguagem natural, ou 'quit' para sair.\n",
    },
    "cli.prompt": {
        "en": "\n> ",
        "fr": "\n> ",
        "es": "\n> ",
        "de": "\n> ",
        "pt": "\n> ",
    },
    "cli.goodbye": {
        "en": "Goodbye!",
        "fr": "Au revoir!",
        "es": "¡Adiós!",
        "de": "Auf Wiedersehen!",
        "pt": "Adeus!",
    },
    "cli.confirm_action": {
        "en": "⚠️ Agent wants to: {action}\nAllow? (y/n): ",
        "fr": "⚠️ L'agent veut: {action}\nAutoriser? (o/n): ",
        "es": "⚠️ El agente quiere: {action}\n¿Permitir? (s/n): ",
        "de": "⚠️ Agent möchte: {action}\nErlauben? (j/n): ",
        "pt": "⚠️ O agente quer: {action}\nPermitir? (s/n): ",
    },
    "cli.action_denied": {
        "en": "Action denied by user.",
        "fr": "Action refusée par l'utilisateur.",
        "es": "Acción denegada por el usuario.",
        "de": "Aktion vom Benutzer verweigert.",
        "pt": "Ação negada pelo usuário.",
    },
    "cli.status_update": {
        "en": "⏳ [{state}] {details}",
        "fr": "⏳ [{state}] {details}",
        "es": "⏳ [{state}] {details}",
        "de": "⏳ [{state}] {details}",
        "pt": "⏳ [{state}] {details}",
    },
    "error.invalid_config": {
        "en": "Invalid configuration: {details}",
        "fr": "Configuration invalide: {details}",
        "es": "Configuración inválida: {details}",
        "de": "Ungültige Konfiguration: {details}",
        "pt": "Configuração inválida: {details}",
    },
    "error.model_failure": {
        "en": "Model API failed: {error}",
        "fr": "Erreur API du modèle: {error}",
        "es": "Fallo en la API del modelo: {error}",
        "de": "Modell-API fehlgeschlagen: {error}",
        "pt": "Falha na API do modelo: {error}",
    },
    "error.vision_required": {
        "en": "This task requires vision capabilities, but no vision model is configured.",
        "fr": "Cette tâche nécessite la vision, mais aucun modèle de vision n'est configuré.",
        "es": "Esta tarea requiere capacidades de visión, pero no hay ningún modelo de visión configurado.",
        "de": "Diese Aufgabe erfordert Vision-Fähigkeiten, aber es ist kein Vision-Modell konfiguriert.",
        "pt": "Esta tarefa requer capacidades de visão, mas nenhum modelo de visão está configurado.",
    },
    "error.tool_execution_failed": {
        "en": "Tool '{tool}' failed: {error}",
        "fr": "L'outil '{tool}' a échoué: {error}",
        "es": "La herramienta '{tool}' falló: {error}",
        "de": "Werkzeug '{tool}' fehlgeschlagen: {error}",
        "pt": "A ferramenta '{tool}' falhou: {error}",
    },
    "log.agent_started": {
        "en": "Agent started successfully.",
        "fr": "Agent démarré avec succès.",
        "es": "Agente iniciado correctamente.",
        "de": "Agent erfolgreich gestartet.",
        "pt": "Agente iniciado com sucesso.",
    },
    "log.agent_stopped": {
        "en": "Agent stopped.",
        "fr": "Agent arrêté.",
        "es": "Agente detenido.",
        "de": "Agent gestoppt.",
        "pt": "Agente parado.",
    },
    "log.task_added": {
        "en": "Added task {task_id} to queue.",
        "fr": "Tâche {task_id} ajoutée à la file.",
        "es": "Se agregó la tarea {task_id} a la cola.",
        "de": "Aufgabe {task_id} zur Warteschlange hinzugefügt.",
        "pt": "Tarefa {task_id} adicionada à fila.",
    },
    "log.task_completed": {
        "en": "Completed task {task_id}.",
        "fr": "Tâche {task_id} terminée.",
        "es": "Tarea completada {task_id}.",
        "de": "Aufgabe {task_id} abgeschlossen.",
        "pt": "Tarefa concluída {task_id}.",
    },
    "log.planning_started": {
        "en": "Planning steps for task {task_id}...",
        "fr": "Planification des étapes pour la tâche {task_id}...",
        "es": "Planificando pasos para la tarea {task_id}...",
        "de": "Planung der Schritte für Aufgabe {task_id}...",
        "pt": "Planejando passos para a tarefa {task_id}...",
    },
    "log.executing_step": {
        "en": "Executing step {step_num}: {description}",
        "fr": "Exécution de l'étape {step_num}: {description}",
        "es": "Ejecutando paso {step_num}: {description}",
        "de": "Ausführen von Schritt {step_num}: {description}",
        "pt": "Executando passo {step_num}: {description}",
    },
}


# === Language detection ===

def _detect_system_lang() -> str:
    """Detect system locale language."""
    try:
        loc = locale.getlocale()[0] or locale.getdefaultlocale()[0] or "en"
        lang = loc.split("_")[0].lower()
        if lang in ("fr", "es", "de", "pt"):
            return lang
        return "en"
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
    if lang == "auto" or lang not in ("en", "fr", "es", "de", "pt"):
        lang = _detect_system_lang()
    _default_lang = lang
    log.info(f"i18n initialized — default language: {_default_lang}")

def get_default_lang() -> str:
    return _default_lang

def set_default_lang(lang: str):
    global _default_lang
    if lang in ("en", "fr", "es", "de", "pt"):
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
