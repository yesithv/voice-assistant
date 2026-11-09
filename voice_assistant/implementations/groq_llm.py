from groq import Groq

from voice_assistant.engines import LanguageModelEngine

DEFAULT_MODEL = 'llama-3.3-70b-versatile'


class GroqLanguageModel(LanguageModelEngine):
    """Hosted LLM inference through the Groq API (Llama 3.3 70B by default)."""

    def __init__(self, api_key: str | None, model: str = DEFAULT_MODEL, max_tokens: int = 200):
        self._client = Groq(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    def generate(self, messages: list[dict[str, str]]) -> str:
        response = self._client.chat.completions.create(
            model       = self._model,
            messages    = messages,
            max_tokens  = self._max_tokens,
            temperature = 0.7
        )
        return (response.choices[0].message.content or '').strip()
