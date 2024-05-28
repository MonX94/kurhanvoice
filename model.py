import subprocess
import os
import numpy as np
import librosa
from flask import Flask, request, jsonify
from whisper_online import *
import deepl
import tempfile
from gtts import gTTS
import logging
import signal
import sys
app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

# Create a logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create a file handler and set the log level
file_handler = logging.FileHandler('model_requests.log')
file_handler.setLevel(logging.INFO)

# Create a log formatter
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

# Add the file handler to the logger
logger.addHandler(file_handler)

def signal_handler(sig, frame):
    logging.info('Shutting down server...')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

DEEPL_AUTH_KEY = os.environ.get("DEEPL_AUTH_KEY")
if DEEPL_AUTH_KEY is None:
    raise ValueError("DEEPL_AUTH_KEY environment variable is not set")

translator = deepl.Translator(DEEPL_AUTH_KEY)

asr = FasterWhisperASR("en", "base")
online = OnlineASRProcessor(asr, buffer_trimming=("segment", 15)) # Use sentence instead of segment to split output by sentence

coqui_models = {
    "bg": "tts_models/bg/cv/vits",
    "cs": "tts_models/cs/cv/vits",
    "da": "tts_models/da/cv/vits",
    "et": "tts_models/et/cv/vits",
    "ga": "tts_models/ga/cv/vits",
    "en": "tts_models/en/ljspeech/tacotron2-DDC",
    "es": "tts_models/es/mai/tacotron2-DDC",
    "fr": "tts_models/fr/mai/tacotron2-DDC",
    "uk": "tts_models/uk/mai/vits",
    "zh-CN": "tts_models/zh-CN/baker/tacotron2-DDC-GST",
    "nl": "tts_models/nl/mai/tacotron2-DDC",
    "de": "tts_models/de/thorsten/tacotron2-DCA",
    "ja": "tts_models/ja/kokoro/tacotron2-DDC",
    "tr": "tts_models/tr/common-voice/glow-tts",
    "it": "tts_models/it/mai_female/glow-tts",
    "ewe": "tts_models/ewe/openbible/vits",
    "hau": "tts_models/hau/openbible/vits",
    "lin": "tts_models/lin/openbible/vits",
    "tw_akuapem": "tts_models/tw_akuapem/openbible/vits",
    "tw_asante": "tts_models/tw_asante/openbible/vits",
    "yor": "tts_models/yor/openbible/vits",
    "hu": "tts_models/hu/css10/vits",
    "el": "tts_models/el/cv/vits",
    "fi": "tts_models/fi/css10/vits",
    "hr": "tts_models/hr/cv/vits",
    "lt": "tts_models/lt/cv/vits",
    "lv": "tts_models/lv/cv/vits",
    "mt": "tts_models/mt/cv/vits",
    "pl": "tts_models/pl/mai_female/vits",
    "pt": "tts_models/pt/cv/vits",
    "ro": "tts_models/ro/cv/vits",
    "sk": "tts_models/sk/cv/vits",
    "sl": "tts_models/sl/cv/vits",
    "sv": "tts_models/sv/cv/vits",
    "ca": "tts_models/ca/custom/vits",
    "fa": "tts_models/fa/custom/glow-tts",
    "bn": "tts_models/bn/custom/vits-male",
    "be": "tts_models/be/common-voice/glow-tts"
}

"""
Unsupported by Coqui TTS:
    Arabic (AR)
    Indonesian (ID)
    Korean (KO)
    Norwegian Bokmål (NB)
    Russian (RU)
"""


def translate_text(text, source_lang, target_lang, glossary):
    glossary_languages = ["DA", "DE", "EN", "ES", "FR", "IT", "JA", "KO", "NB", "NL", "PL", "PT", "RU", "SV", "ZH"]
    if glossary and source_lang in glossary_languages and target_lang in glossary_languages:
        # Delete old glossaries
        #translator.delete_glossaries()
        
        # Create a new glossary
        glossary_name = "my_glossary"
        glossary_object = translator.create_glossary(glossary_name,
                                   source_lang=source_lang,
                                   target_lang=target_lang,
                                   entries=glossary)
        
        # Translate text with the glossary
        result = translator.translate_text(text, source_lang=source_lang, target_lang=target_lang, glossary=glossary_object)
    else:
        # Translate text without the glossary
        result = translator.translate_text(text, source_lang=source_lang, target_lang=target_lang)
    
    return result.text

def text_to_speech(text, lang='en'):
    tts = gTTS(text=text, lang=lang)
    temp_mp3 = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3', dir='audio_files')
    tts.save(temp_mp3.name)
    
    return temp_mp3.name

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

def handle_client(temp_file_name, source_lang, target_lang, settings):
    a = process_audio(temp_file_name)
    online.insert_audio_chunk(a)
    if settings.get('glossary'):
        glossary_str = " ".join(settings.get('glossary').keys())
        # Convert original language part of glossary to a string for Whisper
    else:
        glossary_str = None
    output_text = online.process_iter(user_prompt=glossary_str)

    if not output_text[0]:
        return
    
    translated_text = translate_text(output_text[2], source_lang, target_lang, settings.get('glossary'))
    beg = output_text[0]
    end = output_text[1]
    logger.info("%1.0f %1.0f %s" % (beg, end, translated_text)) # Output with start and end timestamps

    tts_mp3_file = text_to_speech(translated_text, lang=target_lang.split('-')[0].lower()) # e.g. 'en-US' -> 'en'
    response = {'filename': os.path.basename(tts_mp3_file), 'text': output_text[2], 'translated_text': translated_text}
    return response

@app.route('/', methods=['POST'])
def index():
    data = request.json
    audio = data.get('audio')
    source_lang = data.get('sourceLang')
    target_lang = data.get('targetLang')
    settings = data.get('settings')

    # Log the request info
    logger.info(f'Request received: audio={audio}, sourceLang={source_lang}, targetLang={target_lang}, settings={settings}')

    if source_lang.lower() != asr.get_language():
        asr.set_language(source_lang.lower())

    response = handle_client(audio, source_lang, target_lang, settings)
    if response is None:
        return {}, 202 # 202 Accepted
    else:
        logger.info(f'Response sent: {response}')
        return response, 200 # 200 OK

if __name__ == "__main__":
    app.run(port=12346,debug=True)
    logging.info("Server 2 is listening...")

