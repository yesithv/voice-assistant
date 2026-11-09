from abc import ABC, abstractmethod


class ProviderError(Exception):
    """Raised by an engine when its model service fails; status_code follows HTTP semantics."""

    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code


class SpeechToTextEngine(ABC):
    """Common interface for any model that turns recorded audio into text."""

    @abstractmethod
    def transcribe(self, audio: bytes) -> str:
        """Return the transcribed text, or an empty string if nothing was recognised."""


class LanguageModelEngine(ABC):
    """Common interface for any chat model that produces the assistant reply."""

    @abstractmethod
    def generate(self, messages: list[dict[str, str]]) -> str:
        """Return the reply for OpenAI-style messages ({'role': ..., 'content': ...})."""


class TextToSpeechEngine(ABC):
    """Common interface for any model that turns text into speech."""

    @abstractmethod
    def synthesize(self, text: str) -> bytes:
        """Return the spoken text as WAV bytes."""
