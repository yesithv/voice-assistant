import io

from faster_whisper import WhisperModel

from voice_assistant.engines import SpeechToTextEngine

DEFAULT_MODEL = 'small'


class WhisperSpeechToText(SpeechToTextEngine):
    """Local speech recognition with Faster-Whisper (CTranslate2 implementation of OpenAI Whisper)."""

    def __init__(self, model_size: str = DEFAULT_MODEL):
        # Downloaded once from Hugging Face and cached; int8 keeps CPU inference fast and light
        self._model = WhisperModel(model_size, device='cpu', compute_type='int8')

    def transcribe(self, audio: bytes) -> str:
        # PyAV decodes any browser container (webm/ogg/wav) straight from memory
        segments, _ = self._model.transcribe(io.BytesIO(audio), vad_filter=True)
        return ' '.join(segment.text for segment in segments).strip()
