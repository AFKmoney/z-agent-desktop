"""
Telegram bot interface - mixed slash commands + natural language.
The user sends tasks from Telegram, the agent processes them.
"""
import asyncio
import json
import logging
import time
from typing import Optional, Dict, Any, List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

from utils.logger import get_logger
from core.agent import get_agent

log = get_logger("telegram")


# Slash commands reference
HELP_TEXT = """🤖 *Z.AGENT - Assistant de bureau*

*Commandes rapides:*
/start - Démarrer / vérifier le statut
/status - État de l'agent
/help - Cette aide
/queue - File d'attente des tâches
/cancel - Annuler la tâche en cours
/pause - Mettre en pause
/resume - Reprendre
/screenshot - Capture d'écran instantanée
/memory - Mémoire de l'agent

*Modules:*
/files list <path> - Lister des fichiers
/files organize - Trier Téléchargements
/email unread - Lire les emails non lus
/email send <to> | <subject> | <body> - Envoyer un email
/calendar list - Prochains événements
/system processes - Processus en cours
/system info - Infos système
/browser open <url> - Ouvrir un site

*Mode libre:*
Envoie simplement ta demande en langage naturel, l'agent la planifiera et l'exécutera.

Exemples:
• "Tri mes téléchargements par type de fichier"
• "Envoie un mail à alice@example.com pour confirmer la réunion de demain"
• "Capture l'écran et dis-moi ce qu'il y a dessus"
• "Ouvre Gmail dans le navigateur"
• "Liste mes 10 prochains événements de calendrier"
"""


class TelegramInterface:
    """Telegram bot that bridges user messages to the agent."""
    
    def __init__(self, config: dict):
        self.config = config.get("telegram", {})
        self.token = self.config.get("token", "")
        self.allowed_user_ids = self.config.get("allowed_user_ids", [])
        self.natural_language = self.config.get("natural_language", True)
        
        self.app: Optional[Application] = None
        self._task: Optional[asyncio.Task] = None
    
    def _is_allowed(self, update: Update) -> bool:
        if not self.allowed_user_ids or self.allowed_user_ids == [0]:
            return True  # No restriction
        user_id = update.effective_user.id
        return user_id in self.allowed_user_ids
    
    async def start(self):
        """Start the Telegram bot."""
        if not self.token or self.token == "${TELEGRAM_BOT_TOKEN}":
            log.warning("Telegram bot not configured - skipping")
            return
        
        # Reduce PTB logging noise
        logging.getLogger("telegram").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        
        self.app = Application.builder().token(self.token).build()
        
        # Commands
        self.app.add_handler(CommandHandler("start", self._cmd_start))
        self.app.add_handler(CommandHandler("help", self._cmd_help))
        self.app.add_handler(CommandHandler("status", self._cmd_status))
        self.app.add_handler(CommandHandler("queue", self._cmd_queue))
        self.app.add_handler(CommandHandler("pause", self._cmd_pause))
        self.app.add_handler(CommandHandler("resume", self._cmd_resume))
        self.app.add_handler(CommandHandler("cancel", self._cmd_cancel))
        self.app.add_handler(CommandHandler("screenshot", self._cmd_screenshot))
        self.app.add_handler(CommandHandler("memory", self._cmd_memory))
        
        # Module shortcuts
        self.app.add_handler(CommandHandler("files", self._cmd_files))
        self.app.add_handler(CommandHandler("email", self._cmd_email))
        self.app.add_handler(CommandHandler("calendar", self._cmd_calendar))
        self.app.add_handler(CommandHandler("system", self._cmd_system))
        self.app.add_handler(CommandHandler("browser", self._cmd_browser))
        
        # Callback queries (inline buttons)
        self.app.add_handler(CallbackQueryHandler(self._on_callback))
        
        # Free text (natural language)
        if self.natural_language:
            self.app.add_handler(MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self._on_text
            ))

        # Voice messages (transcribe + treat as text)
        self.app.add_handler(MessageHandler(
            filters.VOICE | filters.AUDIO,
            self._on_voice
        ))
        
        # Start polling
        log.info("Telegram bot starting...")
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling(drop_pending_updates=True)
    
    async def stop(self):
        if self.app:
            try:
                await self.app.updater.stop()
                await self.app.stop()
                await self.app.shutdown()
            except Exception as e:
                log.warning(f"Telegram stop error: {e}")
    
    # === Command handlers ===
    
    async def _cmd_start(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._is_allowed(update):
            return
        await update.message.reply_text(
            f"🤖 *Z.AGENT en ligne*\n\n"
            f"Statut: {self._agent_status_text()}\n\n"
            f"Envoie une tâche en langage naturel ou tape /help",
            parse_mode="Markdown"
        )
    
    async def _cmd_help(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._is_allowed(update):
            return
        await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")
    
    async def _cmd_status(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._is_allowed(update):
            return
        agent = get_agent()
        if agent is None:
            await update.message.reply_text("❌ Agent non initialisé")
            return
        status = agent.get_status()
        text = (
            f"🤖 *Statut Agent*\n\n"
            f"État: `{status['state']}`\n"
            f"File: {status['queue_size']} tâche(s)\n"
            f"Tâche courante: {self._fmt_current(status.get('current_task'))}\n\n"
            f"📊 *Mémoire*\n"
            f"- {status['memory']['facts_count']} faits\n"
            f"- {status['memory']['tasks_count']} tâches historisées\n"
            f"- {status['memory']['shortcuts_count']} raccourcis appris\n"
        )
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def _cmd_queue(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._is_allowed(update):
            return
        agent = get_agent()
        if agent is None:
            return
        size = agent.task_queue.qsize()
        await update.message.reply_text(f"📋 File d'attente: {size} tâche(s)")
    
    async def _cmd_pause(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._is_allowed(update):
            return
        agent = get_agent()
        if agent:
            await agent.pause()
            await update.message.reply_text("⏸️ Agent en pause")
    
    async def _cmd_resume(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._is_allowed(update):
            return
        agent = get_agent()
        if agent:
            await agent.resume()
            await update.message.reply_text("▶️ Agent repris")
    
    async def _cmd_cancel(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._is_allowed(update):
            return
        # Drain the queue
        agent = get_agent()
        if agent:
            while not agent.task_queue.empty():
                try:
                    agent.task_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
            await update.message.reply_text("🗑️ File d'attente vidée")
    
    async def _cmd_screenshot(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._is_allowed(update):
            return
        from core.perception import get_perception
        perception = get_perception()
        if perception is None:
            await update.message.reply_text("❌ Perception non disponible")
            return
        path = perception.capture()
        if path:
            with open(path, "rb") as f:
                await update.message.reply_photo(f, caption="📸 Capture d'écran")
        else:
            await update.message.reply_text("❌ Capture impossible")
    
    async def _cmd_memory(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._is_allowed(update):
            return
        from core.memory import get_memory
        memory = get_memory()
        snap = memory.snapshot()
        text = (
            f"🧠 *Mémoire Agent*\n\n"
            f"Faits persistants: {snap['facts_count']}\n"
            f"Préférences: {snap['preferences_count']}\n"
            f"Raccourcis appris: {snap['shortcuts_count']}\n"
            f"Tâches historisées: {snap['tasks_count']}\n\n"
            f"*Dernières tâches:*\n"
        )
        for t in snap["recent_tasks"]:
            text += f"• {t.get('request', '?')[:60]} {'✅' if t.get('success') else '❌'}\n"
        await update.message.reply_text(text, parse_mode="Markdown")
    
    # === Module shortcuts ===
    
    async def _cmd_files(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._is_allowed(update):
            return
        args = ctx.args
        if not args:
            await update.message.reply_text(
                "Usage: /files list <path> | /files organize | /files search <pattern>"
            )
            return
        
        sub = args[0].lower()
        if sub == "list":
            path = " ".join(args[1:]) if len(args) > 1 else None
            request = f"Liste les fichiers du dossier {path or 'Bureau'}"
        elif sub == "organize":
            request = "Organise mon dossier Téléchargements par type de fichier"
        elif sub == "search":
            pattern = " ".join(args[1:])
            request = f"Recherche les fichiers contenant '{pattern}'"
        else:
            await update.message.reply_text(f"Sous-commande inconnue: {sub}")
            return
        
        await self._submit_request(update, request)
    
    async def _cmd_email(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._is_allowed(update):
            return
        args = ctx.args
        if not args:
            await update.message.reply_text(
                "Usage:\n"
                "/email unread - Lire non lus\n"
                "/email send <to> | <subject> | <body> - Envoyer\n"
                "/email search <query> - Rechercher"
            )
            return
        
        sub = args[0].lower()
        if sub == "unread":
            request = "Lis mes 5 derniers emails non lus et fais-moi un résumé"
        elif sub == "send":
            full = " ".join(args[1:])
            parts = [p.strip() for p in full.split("|")]
            if len(parts) < 3:
                await update.message.reply_text("Format: /email send to@x.com | Sujet | Corps")
                return
            request = f"Envoie un email à {parts[0]} avec le sujet '{parts[1]}' et le corps: {parts[2]}"
        elif sub == "search":
            query = " ".join(args[1:])
            request = f"Recherche mes emails contenant '{query}'"
        else:
            await update.message.reply_text(f"Sous-commande inconnue: {sub}")
            return
        
        await self._submit_request(update, request)
    
    async def _cmd_calendar(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._is_allowed(update):
            return
        args = ctx.args
        if not args or args[0].lower() == "list":
            request = "Liste mes 10 prochains événements de calendrier"
        elif args[0].lower() == "create":
            full = " ".join(args[1:])
            request = f"Crée un événement: {full}"
        else:
            await update.message.reply_text("Usage: /calendar list | /calendar create ...")
            return
        await self._submit_request(update, request)
    
    async def _cmd_system(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._is_allowed(update):
            return
        args = ctx.args
        if not args:
            await update.message.reply_text("Usage: /system processes | /system info | /system notify <msg>")
            return
        sub = args[0].lower()
        if sub == "processes":
            request = "Liste les 20 processus utilisant le plus de mémoire"
        elif sub == "info":
            request = "Donne-moi les informations système (CPU, RAM, disque)"
        elif sub == "notify":
            msg = " ".join(args[1:])
            request = f"Affiche une notification système: {msg}"
        else:
            await update.message.reply_text(f"Sous-commande inconnue: {sub}")
            return
        await self._submit_request(update, request)
    
    async def _cmd_browser(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._is_allowed(update):
            return
        args = ctx.args
        if not args or args[0].lower() != "open":
            await update.message.reply_text("Usage: /browser open <url>")
            return
        url = " ".join(args[1:])
        request = f"Ouvre le site {url} dans le navigateur"
        await self._submit_request(update, request)
    
    async def _on_callback(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if not self._is_allowed(update):
            return
        action = query.data
        if action == "confirm_yes":
            await query.edit_message_text("✅ Tâche confirmée, exécution en cours...")
        elif action == "confirm_no":
            await query.edit_message_text("❌ Tâche annulée")
    
    async def _on_text(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        """Handle free-form text messages as natural language requests."""
        if not self._is_allowed(update):
            await update.message.reply_text("❌ Vous n'êtes pas autorisé à utiliser cet agent.")
            return

        text = update.message.text.strip()
        if not text:
            return

        await self._submit_request(update, text)

    async def _on_voice(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        """Handle voice/audio messages — transcribe then treat as text."""
        if not self._is_allowed(update):
            return

        # Get the voice file
        message = update.message
        if message.voice:
            file_obj = await message.voice.get_file()
            ext = ".ogg"
        elif message.audio:
            file_obj = await message.audio.get_file()
            ext = os.path.splitext(message.audio.file_name or "")[1] or ".mp3"
        else:
            return

        # Download to temp file
        import tempfile
        import os as _os
        tmp_path = tempfile.NamedTemporaryFile(suffix=ext, delete=False).name
        try:
            await file_obj.download_to_drive(tmp_path)
        except Exception as e:
            await message.reply_text(f"❌ Download failed: {e}")
            return

        # Transcribe
        await message.reply_text("🎙️ Transcription en cours...")
        try:
            from modules.voice_control import VoiceControlModule
            from utils.config import load_config
            config = load_config()
            voice_mod = VoiceControlModule(config)
            result = await voice_mod.transcribe_audio(tmp_path)
        except Exception as e:
            await message.reply_text(f"❌ Voice module error: {e}")
            _os.unlink(tmp_path)
            return
        finally:
            try:
                _os.unlink(tmp_path)
            except Exception:
                pass

        if not result.get("success"):
            await message.reply_text(f"❌ Transcription failed: {result.get('error', 'unknown')}")
            return

        text = result.get("text", "").strip()
        if not text:
            await message.reply_text("❌ Empty transcript")
            return

        # Reply with transcript + submit
        duration = result.get("duration_s", 0)
        await message.reply_text(
            f"🎙️ Transcription ({duration:.1f}s):\n\n\"{text}\"\n\n⏳ Processing..."
        )
        await self._submit_request(update, text)
    
    async def _submit_request(self, update: Update, request: str):
        """Submit a request to the agent and notify the user."""
        agent = get_agent()
        if agent is None:
            await update.message.reply_text("❌ Agent non initialisé")
            return
        
        task_id = await agent.submit_task(request, source="telegram")
        
        # Confirmation
        await update.message.reply_text(
            f"✅ Tâche reçue\n"
            f"ID: `{task_id}`\n"
            f"Demande: {request[:80]}{'...' if len(request) > 80 else ''}\n\n"
            f"⏳ Exécution en cours...",
            parse_mode="Markdown"
        )
        
        # Subscribe to completion to send result
        async def on_complete(event):
            if event.get("event") == "task_end" and event.get("task_id") == task_id:
                result = event.get("result", {})
                summary = self._format_result(result)
                try:
                    await update.message.reply_text(summary, parse_mode="Markdown")
                except Exception:
                    await update.message.reply_text(summary)
        
        agent.subscribe_progress(on_complete)
    
    def _format_result(self, result: Dict) -> str:
        if not result:
            return "❌ Aucun résultat"
        
        success = result.get("success", False)
        total = result.get("total_steps", 0)
        ok = result.get("succeeded", 0)
        failed = result.get("failed", 0)
        
        emoji = "✅" if success else "⚠️" if ok > 0 else "❌"
        text = f"{emoji} *Tâche terminée*\n\n"
        text += f"Étapes: {ok}/{total} réussies"
        if failed:
            text += f" ({failed} échouées)"
        text += "\n"
        
        # Show first failure if any
        for r in result.get("results", []):
            if not r.get("success", False):
                text += f"\n❌ Échec étape {r.get('step')}: {r.get('error', '?')[:100]}"
                break
        
        return text
    
    def _fmt_current(self, task: Optional[Dict]) -> str:
        if not task:
            return "aucune"
        return task.get("request", "?")[:50]
    
    def _agent_status_text(self) -> str:
        agent = get_agent()
        if agent is None:
            return "non initialisé"
        return agent.state.value


# Global instance
_interface: Optional[TelegramInterface] = None


def init_telegram(config: dict) -> Optional[TelegramInterface]:
    global _interface
    tg_cfg = config.get("telegram", {})
    if not tg_cfg.get("token") or tg_cfg.get("token") == "${TELEGRAM_BOT_TOKEN}":
        log.warning("Telegram disabled - no token")
        return None
    _interface = TelegramInterface(config)
    return _interface


def get_telegram() -> Optional[TelegramInterface]:
    return _interface
