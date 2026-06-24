"""
Voice Control module — speech-to-text via Whisper + voice message support.

Lets the user send voice messages to the Telegram bot. The agent:
  1. Downloads the voice message (.ogg file)
  2. Converts it to .wav via ffmpeg
  3. Transcribes it with Whisper (OpenAI API or local whisper.cpp)
  4. Treats the transcript as a normal text request

Also exposes text-to-speech for replies — the agent can respond with
voice messages for hands-free usage.

Two backends:
  - 'api': OpenAI Whisper API (requires OPENAI_API_KEY or ZAI_API_KEY)
  - 'local': local whisper model (requires `pip install openai-whisper`)
"""
import os
import asyncio
import subprocess
import tempfile
import time
from typing import Dict, Any, Optional, List
from pathlib import Path

from utils.logger import get_logger
from utils.config import get_data_dir

log = get_logger("voice")

# Optional deps
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import whisper  # type: ignore
    LOCAL_WHISPER_AVAILABLE = True
except ImportError:
    LOCAL_WHISPER_AVAILABLE = False


def register(executor, config: dict):
    mod = VoiceControlModule(config)
    executor.register_handler("voice.transcribe", mod.transcribe_audio)
    executor.register_handler("voice.speak", mod.text_to_speech)
    executor.register_handler("voice.list_voices", mod.list_voices)
    log.info(f"Voice module registered: 3 actions "
             f"(STT: {mod.stt_backend}, TTS: {mod.tts_backend})")


class VoiceControlModule:
    """Speech-to-text and text-to-speech."""

    def __init__(self, config: dict):
        self.config = config.get("voice", {})
        self.stt_backend = self.config.get("stt_backend", "api")  # 'api' or 'local'
        self.tts_backend = self.config.get("tts_backend", "api")  # 'api' or 'local'
        self.whisper_model = self.config.get("whisper_model", "whisper-1")
        self.tts_voice = self.config.get("tts_voice", "alloy")
        self.tts_speed = self.config.get("tts_speed", 1.0)
        self.language = self.config.get("language", "auto")  # 'auto', 'fr', 'en'

        # API client (uses z.ai key as fallback)
        self.api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("ZAI_API_KEY", "")
        self._api_client = None
        self._local_model = None

        # Working directory
        self.voice_dir = os.path.join(get_data_dir(), "voice")
        Path(self.voice_dir).mkdir(parents=True, exist_ok=True)

    def _get_api_client(self):
        if not OPENAI_AVAILABLE or not self.api_key:
            return None
        if self._api_client is None:
            self._api_client = OpenAI(api_key=self.api_key)
        return self._api_client

    def _get_local_model(self):
        if not LOCAL_WHISPER_AVAILABLE:
            return None
        if self._local_model is None:
            model_name = self.config.get("local_model_size", "base")
            log.info(f"Loading local Whisper model: {model_name}")
            self._local_model = whisper.load_model(model_name)
        return self._local_model

    async def transcribe_audio(
        self,
        audio_path: str,
        language: Optional[str] = None,
        prompt: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Transcribe an audio file to text.

        Args:
            audio_path: Path to audio file (.wav, .mp3, .ogg, .m4a).
            language: Language hint ('fr', 'en', or None for auto-detect).
            prompt: Optional context prompt to improve accuracy.

        Returns:
            Dict with 'text', 'language', 'duration_s'.
        """
        if not os.path.exists(audio_path):
            return {"success": False, "error": "Audio file not found"}

        # Convert to wav if needed (Whisper API accepts mp3/wav/m4a/webm)
        # Local whisper needs wav
        wav_path = audio_path
        temp_wav = None
        if not audio_path.lower().endswith(".wav"):
            temp_wav = await self._convert_to_wav(audio_path)
            if temp_wav:
                wav_path = temp_wav

        try:
            # Get duration
            duration = await self._get_duration(wav_path)

            # Try API first
            if self.stt_backend == "api":
                client = self._get_api_client()
                if client:
                    try:
                        with open(wav_path, "rb") as f:
                            kwargs_api = {"model": self.whisper_model, "file": f}
                            if language or self.language != "auto":
                                kwargs_api["language"] = language or self.language
                            if prompt:
                                kwargs_api["prompt"] = prompt
                            result = client.audio.transcriptions.create(**kwargs_api)
                        return {
                                "success": True,
                                "text": result.text.strip(),
                                "language": language or self.language,
                                "duration_s": duration,
                                "backend": "api",
                            }
                    except Exception as e:
                        log.warning(f"API STT failed: {e}, trying local")

            # Try local whisper
            if LOCAL_WHISPER_AVAILABLE:
                model = self._get_local_model()
                if model:
                    # Run in thread to avoid blocking
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(
                        None,
                        lambda: model.transcribe(
                            wav_path,
                            language=language if language and language != "auto" else None,
                            initial_prompt=prompt,
                        )
                    )
                    return {
                        "success": True,
                        "text": result.get("text", "").strip(),
                        "language": result.get("language", language or "auto"),
                        "duration_s": duration,
                        "backend": "local",
                    }

            return {"success": False, "error": "No STT backend available (need OPENAI_API_KEY or pip install openai-whisper)"}
        finally:
            if temp_wav and os.path.exists(temp_wav):
                try:
                    os.unlink(temp_wav)
                except Exception:
                    pass

    async def text_to_speech(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: Optional[float] = None,
        output_path: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Convert text to speech audio.

        Args:
            text: Text to synthesize.
            voice: Voice name ('alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer').
            speed: Speed multiplier (0.25 to 4.0).
            output_path: Output file path. If None, auto-generated.

        Returns:
            Dict with 'path' to the generated audio file.
        """
        if not output_path:
            output_path = os.path.join(self.voice_dir, f"tts_{int(time.time() * 1000)}.mp3")

        # Try API
        if self.tts_backend == "api":
            client = self._get_api_client()
            if client:
                try:
                    response = client.audio.speech.create(
                        model="tts-1",
                        voice=voice or self.tts_voice,
                        input=text,
                        speed=speed or self.tts_speed,
                    )
                    response.stream_to_file(output_path)
                    return {
                        "success": True,
                        "path": output_path,
                        "voice": voice or self.tts_voice,
                        "text_length": len(text),
                        "backend": "api",
                    }
                except Exception as e:
                    log.warning(f"API TTS failed: {e}")

        # Try local TTS (espeak or pico2wave)
        try:
            cmd = ["espeak", "-v", "fr" if self.language == "fr" else "en",
                   "-s", str(int((speed or self.tts_speed) * 175)),
                   "-w", output_path.replace(".mp3", ".wav"), text]
            result = subprocess.run(cmd, capture_output=True, timeout=10)
            if result.returncode == 0:
                wav_path = output_path.replace(".mp3", ".wav")
                return {
                    "success": True,
                    "path": wav_path,
                    "voice": "espeak",
                    "text_length": len(text),
                    "backend": "local-espeak",
                }
        except FileNotFoundError:
            pass
        except Exception as e:
            log.debug(f"espeak failed: {e}")

        return {"success": False, "error": "No TTS backend available"}

    async def list_voices(self, **kwargs) -> Dict[str, Any]:
        """List available TTS voices."""
        voices = [
            {"name": "alloy", "description": "Neutral, balanced (API)"},
            {"name": "echo", "description": "Male, warm (API)"},
            {"name": "fable", "description": "Neutral, storytelling (API)"},
            {"name": "onyx", "description": "Deep male, authoritative (API)"},
            {"name": "nova", "description": "Female, clear (API)"},
            {"name": "shimmer", "description": "Female, soft (API)"},
        ]
        return {"success": True, "voices": voices, "backend": self.tts_backend}

    async def _convert_to_wav(self, audio_path: str) -> Optional[str]:
        """Convert any audio format to 16kHz mono wav via ffmpeg."""
        output = os.path.join(self.voice_dir, f"converted_{int(time.time() * 1000)}.wav")
        try:
            result = subprocess.run(
                ["ffmpeg", "-i", audio_path, "-ar", "16000", "-ac", "1",
                 "-y", output],
                capture_output=True, timeout=30,
            )
            if result.returncode == 0:
                return output
            log.warning(f"ffmpeg conversion failed: {result.stderr.decode()[:200]}")
        except FileNotFoundError:
            log.error("ffmpeg not installed — required for voice conversion")
        except Exception as e:
            log.error(f"Audio conversion error: {e}")
        return None

    async def _get_duration(self, audio_path: str) -> float:
        """Get audio duration in seconds."""
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
                capture_output=True, text=True, timeout=10,
            )
            return float(result.stdout.strip()) if result.returncode == 0 else 0
        except Exception:
            return 0
