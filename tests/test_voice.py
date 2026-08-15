import io
import wave
import pytest
import numpy as np
from fastapi.testclient import TestClient
from app.main import app
from app.rag.memory import ConversationMemory, conversation_memory
from app.retrieval.audio_stt import get_stt_provider, SpeechToTextProvider
from app.rag.audio_tts import get_tts_provider, TextToSpeechProvider
from app.rag.pipeline import RAGPipeline

client = TestClient(app)

def create_dummy_wav() -> io.BytesIO:
    """Generates 1 second of dummy PCM mono 16kHz WAV silence for testing."""
    audio_io = io.BytesIO()
    with wave.open(audio_io, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        # 16000 samples of silence
        data = np.zeros(16000, dtype=np.int16)
        wav_file.writeframes(data.tobytes())
    audio_io.seek(0)
    return audio_io

def test_conversation_memory():
    mem = ConversationMemory(window_size=2)
    assert len(mem.history) == 0
    
    mem.add_turn("What is photosyntesis?", "Photosynthesis is light conversion.")
    assert len(mem.history) == 2
    assert "User: What is photosyntesis?" in mem.get_formatted_history()
    
    mem.add_turn("Where does it occur?", "It occurs in chloroplasts.")
    mem.add_turn("Tell me more.", "It creates glucose.")
    # Max turns is 2 (4 entries: 2 user + 2 assistant) due to window_size=2
    assert len(mem.history) == 4
    
    mem.clear()
    assert len(mem.history) == 0

def test_stt_provider_mock(monkeypatch):
    class MockSTT(SpeechToTextProvider):
        def transcribe(self, audio_data):
            return "what is photosynthesis"
            
    monkeypatch.setattr("app.rag.pipeline.rag_pipeline_service.stt_provider", MockSTT())
    
    dummy_audio = create_dummy_wav()
    pipeline = RAGPipeline()
    pipeline.stt_provider = MockSTT()
    
    res = pipeline.stt_provider.transcribe(dummy_audio)
    assert res == "what is photosynthesis"

def test_tts_provider_mock(monkeypatch):
    class MockTTS(TextToSpeechProvider):
        def synthesize(self, text):
            return b"dummy_audio_bytes"
            
    monkeypatch.setattr("app.rag.pipeline.rag_pipeline_service.tts_provider", MockTTS())
    
    pipeline = RAGPipeline()
    pipeline.tts_provider = MockTTS()
    
    res = pipeline.tts_provider.synthesize("test text")
    assert res == b"dummy_audio_bytes"

def test_ask_voice_endpoint_mock(monkeypatch):
    # Mock STT and TTS inside pipeline service for API test consistency
    class MockSTT(SpeechToTextProvider):
        def transcribe(self, audio_data):
            return "What is Python?"
            
    class MockTTS(TextToSpeechProvider):
        def synthesize(self, text):
            return b"synthetic_voice_data"

    from app.rag.pipeline import rag_pipeline_service
    from app.rag.answer_generator import MockGroundedLLMProvider
    
    monkeypatch.setattr(rag_pipeline_service, "stt_provider", MockSTT())
    monkeypatch.setattr(rag_pipeline_service, "tts_provider", MockTTS())
    monkeypatch.setattr(rag_pipeline_service, "llm_provider", MockGroundedLLMProvider())
    
    dummy_audio = create_dummy_wav()
    files = {"file": ("query.wav", dummy_audio, "audio/wav")}
    
    response = client.post("/api/ask-voice?top_k=2", files=files)
    assert response.status_code == 200
    data = response.json()
    
    assert data["transcript"] == "What is Python?"
    assert "answer" in data
    assert "audio" in data
    assert data["audio"].startswith("data:audio/mp3;base64,")

def test_clear_memory_endpoint():
    response = client.post("/api/memory/clear")
    assert response.status_code == 200
    assert response.json()["message"] == "Conversation memory cleared successfully."
