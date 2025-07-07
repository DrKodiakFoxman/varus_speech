from flask import Flask, request, send_file, render_template
import uuid
import os
import asyncio
from edge_tts import Communicate
from pydub import AudioSegment
from io import BytesIO
import re

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/synthesize", methods=["POST"])
def synthesize():
    text = request.json.get("text")
    voice_en = request.json.get("voice_en", "en-US-JennyNeural")
    voice_es = request.json.get("voice_es", "es-MX-DaliaNeural")

    segments = split_text(text, voice_en, voice_es)
    combined = AudioSegment.empty()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    for segment_text, voice in segments:
        filename = f"output_{uuid.uuid4().hex}.mp3"
        loop.run_until_complete(save_audio(segment_text, voice, filename))
        audio = AudioSegment.from_file(filename, format="mp3")
        combined += audio
        os.remove(filename)

    out_io = BytesIO()
    combined.export(out_io, format="mp3")
    out_io.seek(0)
    return send_file(out_io, mimetype="audio/mp3", as_attachment=False, download_name="final_output.mp3")

@app.route("/test-voice", methods=["POST"])
def test_voice():
    voice = request.json.get("voice")
    if voice.startswith("en-"):
        name = voice.split('-')[-1].replace("Neural", "")
        text = f"Hello, I am {name}. It's a pleasure to help you."
    elif voice.startswith("es-"):
        name = voice.split('-')[-1].replace("Neural", "")
        text = f"Hola, soy {name}. Es un placer ayudarte."
    else:
        text = "Hola"

    filename = f"test_{uuid.uuid4().hex}.mp3"
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(save_audio(text, voice, filename))
    return send_file(filename, mimetype="audio/mp3", as_attachment=False, download_name="preview.mp3")

def split_text(text, voice_en, voice_es):
    parts = re.split(r'(\[en\]|\[es\])', text)
    lang = "en"
    segments = []

    for part in parts:
        if part == "[en]":
            lang = "en"
        elif part == "[es]":
            lang = "es"
        elif part.strip():
            voice = voice_en if lang == "en" else voice_es
            segments.append((part.strip(), voice))

    return segments

async def save_audio(text, voice, filename):
    communicate = Communicate(text, voice=voice)
    await communicate.save(filename)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    app.run(host="0.0.0.0", port=port)
