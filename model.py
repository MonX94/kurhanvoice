import socket
import subprocess
import os
import numpy as np
import librosa
from line_packet import receive_one_line, send_one_line
from whisper_online import *
import deepl
import tempfile
from gtts import gTTS
import logging
import signal
import socket
import sys
import traceback

logging.basicConfig(level=logging.INFO)

def signal_handler(sig, frame):
    logging.info('Shutting down server...')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

DEEPL_AUTH_KEY = "38efa020-0aaf-456e-9a9f-91bf35eea0c1:fx"
translator = deepl.Translator(DEEPL_AUTH_KEY)

asr = FasterWhisperASR("auto", "base")
online = OnlineASRProcessor(asr)

def translate_text(text, source_lang, target_lang):
    result = translator.translate_text(text, source_lang=source_lang, target_lang=target_lang)
    return result.text

def text_to_speech(text, lang='en'):
    tts = gTTS(text=text, lang=lang)
    temp_mp3 = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3', dir='audio_files')
    tts.save(temp_mp3.name)
    
    return temp_mp3.name

class Connection:
    '''it wraps conn object'''
    PACKET_SIZE = 65536

    def __init__(self, conn):
        self.conn = conn
        self.last_line = ""
        self.conn.setblocking(True)

    def send(self, line):
        '''it doesn't send the same line twice, because it was problematic in online-text-flow-events'''
        if line == self.last_line:
            return
        send_one_line(self.conn, line)
        self.last_line = line

    def receive_lines(self):
        in_line = receive_one_line(self.conn)
        return in_line

    def non_blocking_receive_audio(self):
        r = self.conn.recv(self.PACKET_SIZE)
        return r

def process_audio(temp_file_name):
    # Convert audio file to desired format using ffmpeg
    converted_file_name = temp_file_name.replace('.wav', '_converted.wav')
    subprocess.run(['ffmpeg', '-i', temp_file_name, '-ar', '16000', '-ac', '1', '-acodec', 'pcm_s16le', converted_file_name], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    
    # Process the converted audio file using librosa
    audio, _ = librosa.load(converted_file_name, sr=16000, dtype=np.float32)
    
    # Clean up the converted file
    os.remove(temp_file_name)
    os.remove(converted_file_name)
    
    return audio

def handle_client(client_socket):
    with client_socket:
        connection = Connection(client_socket)
        message = connection.non_blocking_receive_audio().decode('utf-8')
        if message:
            temp_file_name, source_lang, target_lang = message.split('|')
            a = process_audio(temp_file_name)
            online.insert_audio_chunk(a)
            output_text = online.process_iter()

            if not output_text[0]:
                return
            
            translated_text = translate_text(output_text[2], source_lang, target_lang)
            beg = output_text[0]
            end = output_text[1]
            print("%1.0f %1.0f %s" % (beg, end, translated_text), flush=True, file=sys.stderr)

            tts_mp3_file = text_to_speech(translated_text, lang=target_lang.split('-')[0].lower())
            response = os.path.basename(tts_mp3_file)
            connection.conn.sendall(response.encode('utf-8'))

def main():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.bind(('localhost', 12346))
            server_socket.listen(1)
            logging.info("Server 2 is listening...")

            while True:
                client_socket, client_address = server_socket.accept()
                logging.info("Connected to:", client_address)
                handle_client(client_socket)
    except Exception as e:
        logging.error("Server error: %s", e)
        logging.error(traceback.format_exc())

if __name__ == "__main__":
    main()

