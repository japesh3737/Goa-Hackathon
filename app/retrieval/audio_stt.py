import io
import logging
import requests
from typing import BinaryIO
from app.config import config

logger = logging.getLogger(__name__)

class SpeechToTextProvider:
    def transcribe(self, audio_data: io.BytesIO) -> str:
        """Transcribe audio bytes to text string."""
        raise NotImplementedError

class GoogleSTTProvider(SpeechToTextProvider):
    """Free online Google Speech-to-Text provider (using SpeechRecognition)."""
    def transcribe(self, audio_data: io.BytesIO) -> str:
        try:
            import speech_recognition as sr
        except ImportError:
            logger.error("SpeechRecognition package not installed.")
            raise RuntimeError("SpeechRecognition package not installed.")

        recognizer = sr.Recognizer()
        
        # Audio data is expected to be WAV PCM bytes
        try:
            with sr.AudioFile(audio_data) as source:
                audio = recognizer.record(source)
            text = recognizer.recognize_google(audio, language="en-US")
            logger.info(f"Google STT transcribed successfully: '{text}'")
            return text
        except sr.UnknownValueError:
            logger.warning("Google STT could not understand audio.")
            raise ValueError("Google STT could not understand the spoken query.")
        except sr.RequestError as e:
            logger.error(f"Google STT request failed: {e}")
            raise RuntimeError(f"Speech recognition service unavailable: {e}")
        except Exception as e:
            logger.error(f"Error during Google STT transcription: {e}", exc_info=True)
            raise RuntimeError(f"Transcription failed: {str(e)}")

class OpenAISTTProvider(SpeechToTextProvider):
    """OpenAI Whisper Speech-to-Text provider."""
    def __init__(self, api_key: str = None):
        self.api_key = api_key or config.LLM_API_KEY

    def transcribe(self, audio_data: io.BytesIO) -> str:
        if not self.api_key:
            logger.warning("OpenAI API key missing for STT. Falling back to Google STT.")
            return GoogleSTTProvider().transcribe(audio_data)

        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # Whisper endpoint requires files parameter in multipart format
        audio_data.seek(0)
        files = {
            "file": ("query.wav", audio_data, "audio/wav"),
            "model": (None, "whisper-1"),
            "language": (None, "en")
        }

        try:
            resp = requests.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers=headers,
                files=files,
                timeout=20
            )
            resp.raise_for_status()
            text = resp.json().get("text", "").strip()
            logger.info(f"OpenAI Whisper transcribed: '{text}'")
            return text
        except Exception as e:
            logger.error(f"OpenAI STT transcription failed: {e}")
            raise RuntimeError(f"OpenAI Whisper transcription failed: {str(e)}")

class ElevenLabsSTTProvider(SpeechToTextProvider):
    """ElevenLabs Speech-to-Text provider."""
    def __init__(self, api_key: str = None):
        self.api_key = api_key or config.ELEVENLABS_API_KEY

    def transcribe(self, audio_data: io.BytesIO) -> str:
        if not self.api_key:
            logger.warning("ElevenLabs API key missing for STT. Falling back to Google STT.")
            return GoogleSTTProvider().transcribe(audio_data)

        headers = {
            "xi-api-key": self.api_key
        }
        
        audio_data.seek(0)
        files = {
            "file": ("query.wav", audio_data, "audio/wav"),
            "model_id": (None, "scribe_v2")
        }

        try:
            resp = requests.post(
                "https://api.elevenlabs.io/v1/speech-to-text",
                headers=headers,
                files=files,
                timeout=20
            )
            resp.raise_for_status()
            text = resp.json().get("text", "").strip()
            logger.info(f"ElevenLabs transcribed: '{text}'")
            return text
        except Exception as e:
            logger.error(f"ElevenLabs STT transcription failed: {e}")
            raise RuntimeError(f"ElevenLabs STT transcription failed: {str(e)}")

class SarvamSTTProvider(SpeechToTextProvider):
    """Sarvam AI Speech-to-Text provider."""
    def __init__(self, api_key: str = None):
        self.api_key = api_key or config.SARVAM_API_KEY

    def transcribe(self, audio_data: io.BytesIO) -> str:
        if not self.api_key:
            logger.warning("Sarvam API key missing for STT. Falling back to Google STT.")
            return GoogleSTTProvider().transcribe(audio_data)

        headers = {
            "api-subscription-key": self.api_key
        }
        
        audio_data.seek(0)
        files = {
            "file": ("query.wav", audio_data, "audio/wav"),
            "model": (None, "saaras:v3")
        }

        try:
            resp = requests.post(
                "https://api.sarvam.ai/speech-to-text",
                headers=headers,
                files=files,
                timeout=20
            )
            resp.raise_for_status()
            resp_data = resp.json()
            text = resp_data.get("transcript", resp_data.get("text", "")).strip()
            logger.info(f"Sarvam transcribed: '{text}'")
            return text
        except Exception as e:
            logger.error(f"Sarvam STT transcription failed: {e}")
            raise RuntimeError(f"Sarvam STT transcription failed: {str(e)}")

def get_stt_provider(provider_name: str = None) -> SpeechToTextProvider:
    provider_name = (provider_name or config.STT_PROVIDER).lower()
    if provider_name == "openai" and config.LLM_API_KEY:
        return OpenAISTTProvider()
    elif provider_name == "elevenlabs":
        return ElevenLabsSTTProvider()
    elif provider_name == "sarvam":
        return SarvamSTTProvider()
    return GoogleSTTProvider()
