import base64
import logging
import os
import secrets

from flask import Flask, jsonify, render_template, request, session
from flask_cors import CORS

from voice_assistant.conversation import Conversation
from voice_assistant.engines import LanguageModelEngine, SpeechToTextEngine, TextToSpeechEngine

MAX_MESSAGE_LENGTH = 500
MAX_AUDIO_BYTES = 10 * 1024 * 1024
RETRYABLE_STATUS_CODES = {429, 503}  # rate limited / provider overloaded
REJECTED_STATUS_CODES = {401, 403}  # invalid API key or blocked by a network proxy

logger = logging.getLogger(__name__)


def create_app(stt: SpeechToTextEngine, llm: LanguageModelEngine, tts: TextToSpeechEngine) -> Flask:
    app = Flask(__name__)
    # Signs the session cookie that stores each user's conversation history
    app.secret_key = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    app.config['MAX_CONTENT_LENGTH'] = MAX_AUDIO_BYTES
    CORS(app)

    @app.get('/')
    def home():
        return render_template('index.html')

    @app.post('/speech-to-text')
    def speech_to_text():
        audio = request.get_data()
        if not audio:
            return jsonify(error='No audio received. Please try recording again.'), 400

        try:
            text = stt.transcribe(audio)
        except Exception:
            logger.exception('Speech recognition failed')
            return jsonify(error='Could not process the recording. Please try again.'), 400

        if not text:
            return jsonify(error="Sorry, I couldn't understand the audio. Please try again."), 422
        return jsonify(text=text)

    @app.post('/process-message')
    def process_message():
        data = request.get_json(silent=True) or {}
        message = data.get('userMessage')

        if not isinstance(message, str) or not message.strip():
            return jsonify(error='Invalid message! Please type or record something.'), 400
        if len(message) > MAX_MESSAGE_LENGTH:
            return jsonify(error=f'Message too long! Maximum {MAX_MESSAGE_LENGTH} characters.'), 400

        conversation = Conversation(llm, session.get('history'))
        try:
            reply = conversation.reply(message.strip())
            speech = tts.synthesize(reply)
        except Exception as error:
            status_code = getattr(error, 'status_code', None)
            if status_code is None:
                logger.exception('Failed to generate the assistant reply')
                return jsonify(error='An unexpected error occurred. Please try again.'), 500

            # Provider error bodies can be whole HTML pages (e.g. proxies), so the log is truncated
            logger.error('AI provider returned HTTP %s: %s', status_code, ' '.join(str(error).split())[:200])
            if status_code in RETRYABLE_STATUS_CODES:
                return jsonify(error='The AI service is unavailable or busy. Please try again in a few seconds.'), 503
            if status_code in REJECTED_STATUS_CODES:
                return jsonify(error='The AI service rejected the request. Check the API key or your network/proxy settings.'), 502
            return jsonify(error='The AI service returned an error. Please try again.'), 502

        session['history'] = conversation.history
        return jsonify(
            aiResponseText   = reply,
            aiResponseSpeech = base64.b64encode(speech).decode('ascii')
        )

    @app.errorhandler(413)
    def payload_too_large(_error):
        return jsonify(error='The recording is too long. Please keep it under a minute.'), 413

    return app


def create_language_model() -> LanguageModelEngine:
    """Picks the LLM engine from LLM_PROVIDER: 'groq' (hosted, default) or 'ollama' (local)."""
    provider = os.getenv('LLM_PROVIDER', 'groq').strip().lower()

    if provider == 'ollama':
        from voice_assistant.implementations.ollama_llm import DEFAULT_HOST, DEFAULT_MODEL, OllamaLanguageModel
        return OllamaLanguageModel(os.getenv('OLLAMA_HOST', DEFAULT_HOST), os.getenv('OLLAMA_MODEL', DEFAULT_MODEL))

    if provider == 'groq':
        from voice_assistant.implementations.groq_llm import DEFAULT_MODEL, GroqLanguageModel
        return GroqLanguageModel(os.getenv('GROQ_API_KEY'), os.getenv('GROQ_MODEL', DEFAULT_MODEL))

    raise ValueError(f"Unknown LLM_PROVIDER '{provider}'. Use 'groq' or 'ollama'.")


def create_default_app() -> Flask:
    """Builds the app with the real models. Used by `python app.py` and by gunicorn in Docker."""
    from dotenv import load_dotenv
    load_dotenv()

    try:
        import truststore
        truststore.inject_into_ssl()  # use system CA certificates to work behind corporate proxies
    except ImportError:
        pass

    from voice_assistant.implementations.piper_tts import DEFAULT_MODEL_PATH as DEFAULT_VOICE, PiperTextToSpeech
    from voice_assistant.implementations.whisper_stt import DEFAULT_MODEL as DEFAULT_STT, WhisperSpeechToText

    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
    for noisy_logger in ('httpx', 'httpx2'):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)

    llm = create_language_model()
    logger.info('Language model engine: %s', type(llm).__name__)

    # Models are loaded once at startup instead of on every request
    return create_app(
        stt = WhisperSpeechToText(os.getenv('WHISPER_MODEL', DEFAULT_STT)),
        llm = llm,
        tts = PiperTextToSpeech(os.getenv('PIPER_MODEL_PATH', DEFAULT_VOICE))
    )


if __name__ == '__main__':
    create_default_app().run(host=os.getenv('HOST', '127.0.0.1'), port=int(os.getenv('PORT', '8000')))
