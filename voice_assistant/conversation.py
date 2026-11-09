from voice_assistant.engines import LanguageModelEngine

SYSTEM_PROMPT = (
    'Act like a personal assistant. You can respond to questions, translate sentences, '
    'summarize news and give recommendations. Your answers are read aloud, so use plain '
    'text without markdown or lists. Keep responses concise - 2 to 3 sentences maximum.'
)
MAX_HISTORY_MESSAGES = 6  # 3 user/assistant exchanges


class Conversation:
    """Keeps a short rolling history and builds the messages sent to the language model."""

    def __init__(self, engine: LanguageModelEngine, history: list[dict[str, str]] | None = None,
                 max_history_messages: int = MAX_HISTORY_MESSAGES):
        self._engine = engine
        self._max_history_messages = max_history_messages
        self.history = list(history or [])[-max_history_messages:]

    def build_messages(self, user_input: str) -> list[dict[str, str]]:
        return [
            {'role': 'system', 'content': SYSTEM_PROMPT},
            *self.history,
            {'role': 'user', 'content': user_input},
        ]

    def reply(self, user_input: str) -> str:
        response = self._engine.generate(self.build_messages(user_input))
        self.history = [
            *self.history,
            {'role': 'user', 'content': user_input},
            {'role': 'assistant', 'content': response},
        ][-self._max_history_messages:]
        return response
