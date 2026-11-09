import base64
import unittest

from app import MAX_MESSAGE_LENGTH, create_app
from voice_assistant.engines import LanguageModelEngine, ProviderError, SpeechToTextEngine, TextToSpeechEngine


class FakeSpeechToText(SpeechToTextEngine):
    def __init__(self, text="What's the weather like?"):
        self.text = text

    def transcribe(self, audio: bytes) -> str:
        return self.text


class FakeLanguageModel(LanguageModelEngine):
    def __init__(self, error: Exception | None = None):
        self.error = error
        self.calls = []

    def generate(self, messages: list[dict[str, str]]) -> str:
        if self.error:
            raise self.error
        self.calls.append(messages)
        return 'Hello there!'


class FakeTextToSpeech(TextToSpeechEngine):
    def synthesize(self, text: str) -> bytes:
        return b'RIFF-fake-wav'


class TestApp(unittest.TestCase):
    def setUp(self):
        self.stt = FakeSpeechToText()
        self.llm = FakeLanguageModel()
        self.client = create_app(self.stt, self.llm, FakeTextToSpeech()).test_client()

    def test_home_renders_ui(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'AI Voice Assistant', response.data)

    def test_speech_to_text_returns_transcription(self):
        response = self.client.post('/speech-to-text', data=b'audio-bytes')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'text': "What's the weather like?"})

    def test_speech_to_text_rejects_empty_audio(self):
        response = self.client.post('/speech-to-text', data=b'')
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.get_json())

    def test_speech_to_text_reports_unintelligible_audio(self):
        self.stt.text = ''
        response = self.client.post('/speech-to-text', data=b'audio-bytes')
        self.assertEqual(response.status_code, 422)

    def test_process_message_returns_text_and_speech(self):
        response = self.client.post('/process-message', json={'userMessage': 'Hi'})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['aiResponseText'], 'Hello there!')
        self.assertEqual(base64.b64decode(data['aiResponseSpeech']), b'RIFF-fake-wav')

    def test_history_is_kept_per_session(self):
        self.client.post('/process-message', json={'userMessage': 'Hi'})
        self.client.post('/process-message', json={'userMessage': 'Again'})
        self.assertEqual(
            [m['content'] for m in self.llm.calls[-1][1:]],
            ['Hi', 'Hello there!', 'Again']
        )

        other_client = self.client.application.test_client()
        other_client.post('/process-message', json={'userMessage': 'New user'})
        self.assertEqual(len(self.llm.calls[-1]), 2)  # system prompt + new message only

    def test_rejects_invalid_messages(self):
        bodies = ({}, {'userMessage': ''}, {'userMessage': '   '}, {'userMessage': 123},
                  {'userMessage': 'x' * (MAX_MESSAGE_LENGTH + 1)})
        for body in bodies:
            with self.subTest(body=body):
                response = self.client.post('/process-message', json=body)
                self.assertEqual(response.status_code, 400)
                self.assertIn('error', response.get_json())
        self.assertEqual(self.llm.calls, [])

    def test_rejects_non_json_body(self):
        response = self.client.post('/process-message', data='hello')
        self.assertEqual(response.status_code, 400)

    def test_provider_overload_returns_503(self):
        self.llm.error = ProviderError(429, 'rate limited')
        with self.assertLogs('app', level='ERROR'):
            response = self.client.post('/process-message', json={'userMessage': 'Hi'})
        self.assertEqual(response.status_code, 503)
        self.assertIn('error', response.get_json())

    def test_provider_rejection_returns_502(self):
        self.llm.error = ProviderError(403, 'forbidden')
        with self.assertLogs('app', level='ERROR'):
            response = self.client.post('/process-message', json={'userMessage': 'Hi'})
        self.assertEqual(response.status_code, 502)
        self.assertIn('API key', response.get_json()['error'])

    def test_unexpected_error_returns_500_without_details(self):
        self.llm.error = RuntimeError('secret internal detail')
        with self.assertLogs('app', level='ERROR'):
            response = self.client.post('/process-message', json={'userMessage': 'Hi'})
        self.assertEqual(response.status_code, 500)
        self.assertNotIn('secret internal detail', response.get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()
