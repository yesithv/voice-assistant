import io
import wave

from piper import PiperVoice

from voice_assistant.engines import TextToSpeechEngine

DEFAULT_MODEL_PATH = 'models/tts/en_US-lessac-medium.onnx'


class PiperTextToSpeech(TextToSpeechEngine):
    """Local neural text-to-speech with Piper (VITS voices exported to ONNX)."""

    def __init__(self, model_path: str = DEFAULT_MODEL_PATH):
        self._voice = PiperVoice.load(model_path)

    def synthesize(self, text: str) -> bytes:
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav_file:
            self._voice.synthesize_wav(text, wav_file)
        return buffer.getvalue()
