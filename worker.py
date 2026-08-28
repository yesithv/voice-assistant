import io
import os
import tempfile
import wave

from faster_whisper import WhisperModel
from piper import PiperVoice
from groq import Groq

groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))

# Models are loaded once at startup to avoid reloading on every request
_whisper = WhisperModel(
    os.getenv('WHISPER_MODEL', 'small'),
    device='cpu',
    compute_type='int8'
)
_piper_voice = PiperVoice.load(
    os.getenv('PIPER_MODEL_PATH', 'models/tts/en_US-lessac-medium.onnx')
)


def speech_to_text(audio_binary):
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
        tmp.write(audio_binary)
        tmp_path = tmp.name
    try:
        segments, _ = _whisper.transcribe(tmp_path)
        text = ' '.join(s.text for s in segments).strip()
        print('Recognised text: ', text)
    finally:
        os.unlink(tmp_path)
    return text or None


def text_to_speech(text, voice=''):
    audio_buffer = io.BytesIO()
    with wave.open(audio_buffer, 'wb') as wav_out:
        _piper_voice.synthesize_wav(text, wav_out)
    print('text to speech: generated', len(audio_buffer.getvalue()), 'bytes')
    return audio_buffer.getvalue()

def process_message(user_message):
    prompt = 'Act like a personal assistant. You can respond to questions, translate sentences, summarize news and give recommendations. Keep responses concise - 2 to 3 sentences maximum'

    response = groq_client.chat.completions.create(
        model=os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile'),
        messages=[
            {'role': 'system', 'content': prompt},
            {'role': 'user',   'content': user_message}
        ]
    )
    ai_text = response.choices[0].message.content
    print('Groq response text:', ai_text)
    return ai_text
