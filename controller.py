import time
import uuid
from flask import Flask, request, send_file
from flask_socketio import SocketIO, emit
import requests
import json
# from flask_cors import CORS
import os
import tempfile
import logging
import base64

app = Flask(__name__, static_url_path="/static", static_folder='/home/monx94/Downloads/kurhanvoice/static')
socketio = SocketIO(app, cors_allowed_origins="*")

# CORS(app, resources={r"/upload": {"origins": "*"}})  # Allow requests from all origins
SERVER_2_ADDRESS = ('localhost', 12346)
PACKET_SIZE = 65536

AUDIO_FOLDER = 'audio_files'
if not os.path.exists(AUDIO_FOLDER):
    os.makedirs(AUDIO_FOLDER)

# Create a logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create a file handler and set the log level
file_handler = logging.FileHandler('controller_requests.log')
file_handler.setLevel(logging.INFO)

# Create a log formatter
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

# Add the file handler to the logger
logger.addHandler(file_handler)

@app.route('/', methods=['GET'])
def index():
    return app.send_static_file('index.html')

@socketio.on('upload_audio')
def upload_audio(data):
    try:
        if 'audio' not in data or 'sourceLang' not in data or 'targetLang' not in data:
            emit('error', {'error': 'Missing required fields'})
            return
        
        file = data.get('audio') # base64
        source_lang = data.get('sourceLang')
        target_lang = data.get('targetLang')
        settings = data.get('settings', '{}')
    
        if settings:
            settings = json.loads(settings)
        
        # Save the file to a temporary location
        # temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        # file.save(temp_file.name)

        audio_data = base64.b64decode(file.split(',')[1])
        temp_file = f"audio_{int(time.time())}_{uuid.uuid4().hex}.wav"
        file_path = os.path.join(AUDIO_FOLDER, temp_file)
        with open(file_path, 'wb') as f:
            f.write(audio_data)

        # Send the temporary file name and language info to Server 2

        # Log the request info
        # logger.info(f'Request received: audio={temp_file.name}, sourceLang={source_lang}, targetLang={target_lang}, settings={settings}')
        response = requests.post('http://localhost:12346/', json={
            'audio': temp_file,
            'sourceLang': source_lang,
            'targetLang': target_lang,
            'settings': settings
        })

        emit('audio_processed', response.json())

        # Clean up the temporary file
        #os.remove(temp_file.name)

        # Send the filename back to the frontend
        logger.info(f'Response sent: {response.json()}')
    except Exception as e:
        emit('error', {'error': str(e)})
        return
    
@socketio.on('restart')
def restart():
    response = requests.post('http://localhost:12346/restart')
    emit('restart_response', response.json())

@app.route('/audio/<filename>', methods=['GET'])
def get_audio(filename):
    return send_file(os.path.join(AUDIO_FOLDER, filename), mimetype='audio/mpeg')

if __name__ == "__main__":
    socketio.run(app, debug=True, port=5000, host='127.0.0.1', ssl_context="adhoc")  # Bind to localhost


