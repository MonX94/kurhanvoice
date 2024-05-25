document.getElementById('addEntry').addEventListener('click', function(event) {
    event.preventDefault();
    const glossary = document.getElementById('glossary');
    const entry = document.createElement('div');
    entry.classList.add('glossary-entry');
    entry.innerHTML = `
        <input type="text" class="form-control mb-2" placeholder="Original">
        <input type="text" class="form-control mb-2" placeholder="Translation">
        <button class="btn btn-danger remove-entry mb-2">Remove</button>
    `;
    glossary.appendChild(entry);
});

document.getElementById('glossary').addEventListener('click', function(event) {
    if (event.target.classList.contains('remove-entry')) {
        event.preventDefault();
        event.target.parentElement.remove();
    }
});

const sourceLangSelect = document.getElementById('sourceLang');
const targetLangSelect = document.getElementById('targetLang');

let recorder;
let audioContext;
let intervalId;

document.getElementById('startButton').addEventListener('click', async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioContext = new AudioContext();
    const input = audioContext.createMediaStreamSource(stream);
    recorder = new Recorder(input, { numChannels: 1 }); // Mono channel
    recorder.record();
    document.getElementById('startButton').disabled = true;
    document.getElementById('stopButton').disabled = false;

    intervalId = setInterval(() => {
        recorder.exportWAV((blob) => {
            const formData = new FormData();
            formData.append('audio', blob, 'audio.wav');
            formData.append('sourceLang', document.getElementById('sourceLang').value);
            formData.append('targetLang', document.getElementById('targetLang').value);
            
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
                ttsVoice: ttsVoice,
                glossary: glossary
            };

            formData.append('settings', JSON.stringify(settings));

            fetch('/upload', {
                method: 'POST',
                body: formData
            }).then(response => response.json())
              .then(data => {
                if (data.filename) {
                    const audioUrl = `/audio/${data.filename}`;
                    const audioPlayback = document.getElementById('audioPlayback');
                    audioPlayback.src = audioUrl;
                    audioPlayback.play();
                }
            }).catch(error => console.error(error));

            recorder.clear();
        });
    }, 1000); // Send audio every second
});

document.getElementById('stopButton').onclick = () => {
    clearInterval(intervalId);
    recorder.stop();
    document.getElementById('startButton').disabled = false;
    document.getElementById('stopButton').disabled = true;
};


function applySettings() {
    const volume = document.getElementById('volumeControl').value;
    const ttsVoice = document.getElementById('ttsVoice').value;
    const glossaryEntries = document.querySelectorAll('#glossary .glossary-entry');
    const glossary = {};

    glossaryEntries.forEach(entry => {
        const original = entry.querySelector('input:nth-child(1)').value;
        const translation = entry.querySelector('input:nth-child(2)').value;
        if (original && translation) {
            glossary[original] = translation;
        }
    });

    // Apply settings logic here
}