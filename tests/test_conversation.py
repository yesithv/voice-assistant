import unittest

from voice_assistant.conversation import SYSTEM_PROMPT, Conversation
from voice_assistant.engines import LanguageModelEngine


class EchoLanguageModel(LanguageModelEngine):
    def __init__(self):
        self.calls = []

    def generate(self, messages: list[dict[str, str]]) -> str:
        self.calls.append(messages)
        return f"echo: {messages[-1]['content']}"


class TestConversation(unittest.TestCase):
    def setUp(self):
        self.engine = EchoLanguageModel()

    def test_first_message_includes_system_prompt(self):
        Conversation(self.engine).reply('Hi')
        self.assertEqual(self.engine.calls[0], [
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': 'Hi'},
        ])

    def test_reply_updates_history(self):
        conversation = Conversation(self.engine)
        reply = conversation.reply('Hi')
        self.assertEqual(reply, 'echo: Hi')
        self.assertEqual(conversation.history, [
            {'role': 'user', 'content': 'Hi'},
            {'role': 'assistant', 'content': 'echo: Hi'},
        ])

    def test_history_is_sent_as_context(self):
        conversation = Conversation(self.engine)
        conversation.reply('One')
        conversation.reply('Two')
        self.assertEqual([m['content'] for m in self.engine.calls[-1]],
                         [SYSTEM_PROMPT, 'One', 'echo: One', 'Two'])

    def test_history_is_truncated(self):
        conversation = Conversation(self.engine, max_history_messages=4)
        for text in ('1', '2', '3'):
            conversation.reply(text)
        self.assertEqual([m['content'] for m in conversation.history],
                         ['2', 'echo: 2', '3', 'echo: 3'])

    def test_existing_history_is_truncated_on_load(self):
        history = [{'role': 'user', 'content': str(i)} for i in range(10)]
        conversation = Conversation(self.engine, history, max_history_messages=6)
        self.assertEqual(len(conversation.history), 6)
        self.assertEqual(conversation.history[0]['content'], '4')


if __name__ == '__main__':
    unittest.main()
