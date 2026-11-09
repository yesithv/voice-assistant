"""Downloads the Piper voice and pre-caches the Whisper model so the app can start offline."""
import os
import urllib.request
from pathlib import Path

try:
    import truststore
    truststore.inject_into_ssl()  # use system CA certificates to work behind corporate proxies
except ImportError:
    pass

from faster_whisper import download_model

PIPER_VOICES_URL = 'https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium'
PIPER_FILES = ('en_US-lessac-medium.onnx', 'en_US-lessac-medium.onnx.json')
TTS_DIR = Path(__file__).resolve().parent.parent / 'models' / 'tts'


def download_piper_voice():
    TTS_DIR.mkdir(parents=True, exist_ok=True)
    for filename in PIPER_FILES:
        target = TTS_DIR / filename
        if target.exists():
            print(f'Piper: {filename} already present')
            continue
        print(f'Piper: downloading {filename}...')
        urllib.request.urlretrieve(f'{PIPER_VOICES_URL}/{filename}', target)


def download_whisper_model():
    model_size = os.getenv('WHISPER_MODEL', 'small')
    print(f'Whisper: caching "{model_size}" model...')
    download_model(model_size)


if __name__ == '__main__':
    download_piper_voice()
    download_whisper_model()
    print('Models ready.')
