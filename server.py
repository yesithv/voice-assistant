import base64
import json
import os
from dotenv import load_dotenv

load_dotenv()  # must run before worker import so API keys are available

try:
    import truststore
    truststore.inject_into_ssl()  # use system CA certificates to trust corporate proxies
except ImportError:
    pass

from flask import Flask, render_template, request
from flask_cors import CORS
from worker import speech_to_text, text_to_speech, process_message

app = Flask(__name__)
cors = CORS(app, resources={r"/*": {"origins": "*"}})

@app.route('/', methods = ['GET'])
def index():
    return render_template('index.html')

@app.route('/speech-to-text', methods = ['POST'])
def speech_to_text_route():
    print(' ...... Start processing speech_to_text_route() ......')

    # Get yhe user's speech from their request
    audio_binary = request.data
    # Call to transcribe the speech
    text = speech_to_text(audio_binary)

    # Return the response back to the user in JSON format
    response = app.response_class(
        response = json.dumps({'text': text}),
        status   = 200,
        mimetype = 'application/json'
    )
    print('Response speech_to_text_route(): ', response)
    return response

@app.route('/process-message', methods = ['POST'])
def process_prompt_route():
    # Get user's message from their request
    user_message = request.json['userMessage']
    print('...... Start processing process_prompt_route() ......', user_message)

    # Get user's preferred voice from their request
    voice = request.json['voice']
    print('voice', voice)

    try:
        ai_response_text = process_message(user_message)
        ai_response_text = os.linesep.join([s for s in ai_response_text.splitlines() if s])

        ai_response_speech = text_to_speech(ai_response_text, voice)
        ai_response_speech = base64.b64encode(ai_response_speech).decode('utf-8')

        response = app.response_class(
            response = json.dumps(
                {'aiResponseText'  : ai_response_text,
                 'aiResponseSpeech': ai_response_speech}),
            status   = 200,
            mimetype = 'application/json'
        )
    except Exception as e:
        import traceback
        print('Unexpected error type:', type(e).__name__)
        print('Unexpected error detail:', e)
        print(traceback.format_exc())
        msg = str(e)
        status = 503 if 'overloaded' in msg.lower() or 'rate limit' in msg.lower() else 500
        error_text = 'The AI service is currently overloaded. Please try again in a few seconds.' if status == 503 else 'An unexpected error occurred. Please try again.'
        response = app.response_class(
            response = json.dumps({'error': error_text}),
            status   = status,
            mimetype = 'application/json'
        )

    print('response process_prompt_route(): ', response)
    return response

if __name__ == '__main__':
    app.run(
        port = 8000,
        host = '0.0.0.0')
