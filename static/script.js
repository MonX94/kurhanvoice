// Add new glossary entry
function addEntry(original = '', translation = '') {
    const glossary = document.getElementById('glossary');
    const entry = document.createElement('div');
    entry.classList.add('glossary-entry');
    entry.innerHTML = `
        <input type="text" class="form-control mb-2" placeholder="Original" value="${original}">
        <input type="text" class="form-control mb-2" placeholder="Translation" value="${translation}">
        <button class="btn btn-danger remove-entry mb-2">Remove</button>
    `;
    glossary.appendChild(entry);
}

document.getElementById('addEntry').addEventListener('click', function(event) {
    event.preventDefault();
    addEntry();
});

// Remove glossary entry
function removeEntry(event) {
    if (event.target.classList.contains('remove-entry')) {
        event.preventDefault();
        event.target.parentElement.remove();
    }
}

document.getElementById('glossary').addEventListener('click', removeEntry);

const sourceLangSelect = document.getElementById('sourceLang');
const targetLangSelect = document.getElementById('targetLang');

let recorder;
let audioContext;
let intervalId;
let audioQueue = [];
let isPlaying = false;

const socket = io.connect('https://' + location.hostname + ':' + location.port);

socket.on('error', function (err) {
    console.log(err);
});


document.getElementById('startButton').addEventListener('click', async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioContext = new AudioContext();
    const input = audioContext.createMediaStreamSource(stream);
    recorder = new Recorder(input, { numChannels: 1 }); // Mono channel
    recorder.record();
    document.getElementById('startButton').disabled = true;
    document.getElementById('stopButton').disabled = false;

    socket.emit('restart');

    intervalId = setInterval(() => {
        recorder.exportWAV((blob) => {
            
            const ttsVoice = document.getElementById('ttsVoice').value;
            const glossaryEntries = document.querySelectorAll('.glossary-entry');
            const glossary = {};

            glossaryEntries.forEach(entry => {
                const original = entry.querySelector('input:nth-child(1)').value;
                const translation = entry.querySelector('input:nth-child(2)').value;
                if (original && translation) {
                    glossary[original] = translation;
                }
            });

            const settings = JSON.stringify({
                ttsVoice: ttsVoice,
                glossary: glossary
            });
            
            const reader = new FileReader();
            reader.readAsDataURL(blob);
            reader.onloadend = () => {
                const base64data = reader.result;
                const data = {
                    audio: base64data,
                    sourceLang: sourceLangSelect.value,
                    targetLang: targetLangSelect.value,
                    settings: settings
                };

                socket.emit('upload_audio', data);
            }

            recorder.clear();
        });
    }, 1000); // Send audio every second
});

const textContainer = document.getElementById('textContainer');
const translationContainer = document.getElementById('translationContainer');
const subtitlesContainer = document.getElementById('subtitlesContainer');

socket.on('audio_processed', (data) => {
    console.log(data);
    if (data.error) {
        console.error(data.error);
        return;
    } else if (!data.filename) {
        console.log('Listening...');
        return
    }
    const audioUrl = `/audio/${data.filename}`;
    audioQueue.push(audioUrl);
    playNextInQueue();

    const text = data.text;
    const translatedText = data.translated_text;
    
    subtitlesContainer.hidden = false;
    textContainer.textContent += text + ' ';
    translationContainer.textContent += translatedText + ' ';
});

socket.on('error', (data) => {
    console.error(data.error);
})


function playNextInQueue() {
    if (isPlaying || audioQueue.length === 0) {
        return;
    }
    
    isPlaying = true;
    const audioUrl = audioQueue.shift();
    const audioPlayback = document.getElementById('audioPlayback');
    audioPlayback.src = audioUrl;
    audioPlayback.play();
    
    audioPlayback.onended = () => {
        isPlaying = false;
        playNextInQueue();
    };
}

// Stop recording
document.getElementById('stopButton').onclick = () => {
    clearInterval(intervalId);
    recorder.stop();
    document.getElementById('startButton').disabled = false;
    document.getElementById('stopButton').disabled = true;
};

// Save settings to local storage
function applySettings() {
    const sourceLang = sourceLangSelect.value;
    const targetLang = targetLangSelect.value;
    const ttsVoice = document.getElementById('ttsVoice').value;
    const glossaryEntries = document.querySelectorAll('.glossary-entry');
    const glossary = {};

    glossaryEntries.forEach(entry => {
        const original = entry.querySelector('input:nth-child(1)').value;
        const translation = entry.querySelector('input:nth-child(2)').value;
        if (original && translation) {
            glossary[original] = translation;
        }
    });

    const settings = {
        sourceLang: sourceLang,
        targetLang: targetLang,
        ttsVoice: ttsVoice,
        glossary: glossary
    };

    localStorage.setItem('settings', JSON.stringify(settings));
}

// Load settings from local storage
const storedSettings = localStorage.getItem('settings');
if (storedSettings) {
    const settings = JSON.parse(storedSettings);
    document.getElementById('sourceLang').value = settings.sourceLang;
    document.getElementById('targetLang').value = settings.targetLang;
    document.getElementById('ttsVoice').value = settings.ttsVoice;
    const glossaryContainer = document.getElementById('glossary');
    glossaryContainer.innerHTML = ''; // Clear the glossary container
    Object.entries(settings.glossary).forEach(([original, translation]) => {
        // Use the addEntry function to create a new glossary entry
        addEntry(original, translation);
    });
}