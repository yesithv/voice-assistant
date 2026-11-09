import httpx

from voice_assistant.engines import LanguageModelEngine, ProviderError

DEFAULT_HOST = 'http://localhost:11434'
DEFAULT_MODEL = 'llama3.2'


class OllamaLanguageModel(LanguageModelEngine):
    """Local LLM inference through an Ollama server (Llama 3.2 3B by default)."""

    def __init__(self, host: str = DEFAULT_HOST, model: str = DEFAULT_MODEL, max_tokens: int = 200,
                 client: httpx.Client | None = None):
        # trust_env=False keeps calls to the local server away from corporate HTTP proxies
        self._client = client or httpx.Client(base_url=host, timeout=120, trust_env=False)
        self._model = model
        self._max_tokens = max_tokens

    def generate(self, messages: list[dict[str, str]]) -> str:
        try:
            response = self._client.post('/api/chat', json={
                'model'   : self._model,
                'messages': messages,
                'stream'  : False,
                'options' : {'temperature': 0.7, 'num_predict': self._max_tokens}
            })
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise ProviderError(error.response.status_code, f'Ollama error: {error.response.text}') from error
        except httpx.TransportError as error:
            raise ProviderError(503, f'Ollama is not reachable at {self._client.base_url}: {error}') from error

        return response.json()['message']['content'].strip()
