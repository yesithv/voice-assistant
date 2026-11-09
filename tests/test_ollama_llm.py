import json
import unittest

import httpx

from voice_assistant.engines import ProviderError
from voice_assistant.implementations.ollama_llm import OllamaLanguageModel

MESSAGES = [{'role': 'user', 'content': 'Hi'}]


def make_engine(handler) -> OllamaLanguageModel:
    client = httpx.Client(base_url='http://ollama.test', transport=httpx.MockTransport(handler))
    return OllamaLanguageModel(model='llama3.2', max_tokens=50, client=client)


class TestOllamaLanguageModel(unittest.TestCase):
    def test_sends_chat_request_and_returns_reply(self):
        requests = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(200, json={'message': {'role': 'assistant', 'content': ' Hello! '}})

        reply = make_engine(handler).generate(MESSAGES)

        self.assertEqual(reply, 'Hello!')
        self.assertEqual(requests[0].url.path, '/api/chat')
        body = json.loads(requests[0].content)
        self.assertEqual(body['model'], 'llama3.2')
        self.assertEqual(body['messages'], MESSAGES)
        self.assertFalse(body['stream'])
        self.assertEqual(body['options']['num_predict'], 50)

    def test_http_error_raises_provider_error_with_status(self):
        engine = make_engine(lambda request: httpx.Response(404, json={'error': "model 'llama3.2' not found"}))
        with self.assertRaises(ProviderError) as context:
            engine.generate(MESSAGES)
        self.assertEqual(context.exception.status_code, 404)
        self.assertIn('not found', str(context.exception))

    def test_unreachable_server_raises_503(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError('connection refused', request=request)

        with self.assertRaises(ProviderError) as context:
            make_engine(handler).generate(MESSAGES)
        self.assertEqual(context.exception.status_code, 503)


if __name__ == '__main__':
    unittest.main()
