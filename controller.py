from flask import Flask, request, send_file, render_template, jsonify
import requests
import json
from flask_cors import CORS
import os
import tempfile
import logging

app = Flask(__name__, static_url_path="/static", static_folder='/home/monx94/Downloads/kurhanvoice/static')
CORS(app, resources={r"/upload": {"origins": "*"}})  # Allow requests from all origins
SERVER_2_ADDRESS = ('localhost', 12346)
PACKET_SIZE = 65536

@app.route('/', methods=['GET'])
def index():
    return app.send_static_file('index.html')

@app.route('/upload', methods=['POST'])
def upload_audio():
    try:
        if 'audio' not in request.files or 'sourceLang' not in request.form or 'targetLang' not in request.form:
            return {'error': 'Invalid request'}, 400
        
        file = request.files['audio']
        source_lang = request.form['sourceLang']
        target_lang = request.form['targetLang']
        settings = request.form.get('settings')
    
        if settings:
            settings = json.loads(settings)
        
        if file.filename == '':
            return {'error': 'No selected file'}, 400

        # Save the file to a temporary location
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        file.save(temp_file.name)

        # Send the temporary file name and language info to Server 2

        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(SERVER_2_ADDRESS)
            message = f"{temp_file.name}|{source_lang}|{target_lang}"
            print(message)
            s.sendall(message.encode('utf-8'))
            response = s.recv(PACKET_SIZE).decode('utf-8')
        """

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

        # Log the request info
        logger.info(f'Request received: audio={temp_file.name}, sourceLang={source_lang}, targetLang={target_lang}, settings={settings}')
        response = requests.post('http://localhost:12346/', data={'audio': temp_file.name, 'sourceLang': source_lang, 'targetLang': target_lang, 'settings': settings})

        if response.status_code == 202: # Accepted; Data still processing
            return {}, 202

        # Clean up the temporary file
        #os.remove(temp_file.name)

        # Send the filename back to the frontend
        logger.info(f'Response sent: {response.json()}')
        return response.json(), 200
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/audio/<filename>', methods=['GET'])
def get_audio(filename):
    return send_file(os.path.join('audio_files', filename), mimetype='audio/mpeg')

if __name__ == "__main__":
    app.run(debug=True, port=5000, host='127.0.0.1', ssl_context="adhoc")  # Bind to localhost

