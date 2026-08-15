import io
import base64
import logging
import requests
from app.config import config

logger = logging.getLogger(__name__)

class TextToSpeechProvider:
    def synthesize(self, text: str) -> bytes:
        """Synthesize text into speech bytes (MP3 format)."""
        raise NotImplementedError

class GTTSProvider(TextToSpeechProvider):
    """Free online Google Text-to-Speech provider using gTTS."""
    def synthesize(self, text: str) -> bytes:
        if not text or not text.strip():
            return b""
            
        try:
            from gtts import gTTS
        except ImportError:
            logger.error("gTTS package not installed.")
            raise RuntimeError("gTTS package not installed.")

        try:
            tts = gTTS(text=text, lang="en", slow=False)
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            fp.seek(0)
            logger.info("gTTS speech synthesis complete.")
            return fp.read()
        except Exception as e:
            logger.error(f"gTTS speech synthesis failed: {e}", exc_info=True)
            raise RuntimeError(f"Speech synthesis failed: {str(e)}")

class OpenAITTSProvider(TextToSpeechProvider):
    """OpenAI Text-to-Speech provider."""
    def __init__(self, api_key: str = None, model: str = "tts-1", voice: str = "alloy"):
        self.api_key = api_key or config.LLM_API_KEY
        self.model = model
        self.voice = voice

    def synthesize(self, text: str) -> bytes:
        if not self.api_key:
            logger.warning("OpenAI API key missing for TTS. Falling back to gTTS.")
            return GTTSProvider().synthesize(text)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "input": text,
            "voice": self.voice,
            "response_format": "mp3"
        }

        try:
            resp = requests.post(
                "https://api.openai.com/v1/audio/speech",
                headers=headers,
                json=payload,
                timeout=15
            )
            resp.raise_for_status()
            logger.info("OpenAI TTS speech synthesis complete.")
            return resp.content
        except Exception as e:
            logger.error(f"OpenAI TTS synthesis failed: {e}")
            raise RuntimeError(f"OpenAI TTS synthesis failed: {str(e)}")

def get_tts_provider(provider_name: str = None) -> TextToSpeechProvider:
    provider_name = (provider_name or config.TTS_PROVIDER).lower()
    if provider_name == "openai" and config.LLM_API_KEY:
        return OpenAITTSProvider()
    return GTTSProvider()
