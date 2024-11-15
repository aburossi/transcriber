import streamlit as st
from openai import OpenAI
import os
from pydub import AudioSegment
import tempfile
import requests
from io import StringIO
import converter  # Import the updated conversion function
import json
import streamlit.components.v1 as components

# Set page configuration
st.set_page_config(
    page_title="📄 Audio & Video Transcription App",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Title
st.title("📄 Audio- & Video-Transkriptions-App")

# Sidebar instructions
with st.sidebar:
    st.header("❗ **So verwenden Sie diese App**")
    st.markdown("""
    1. **Geben Sie Ihren OpenAI-API-Schlüssel ein**: Erhalten Sie Ihren API-Schlüssel von [OpenAI](https://platform.openai.com/account/api-keys) und geben Sie ihn links im Feld *OpenAI-API-Schlüssel* ein.
    2. **Laden Sie Audio- oder Videodateien hoch oder geben Sie URLs ein**: Sie können entweder Dateien (MP3, WAV, OGG, FLAC, MP4, MKV, AVI) direkt hochladen oder URLs angeben.
    3. **Optionen wählen**: Wählen Sie die Sprache und ob Zeitstempel in das Transkript aufgenommen werden sollen.
    4. **Transkribieren**: Klicken Sie auf die Schaltfläche "Transkribieren", um den Prozess zu starten.
    5. **Transkript herunterladen oder kopieren**: Nach Abschluss können Sie das Transkript als Textdatei herunterladen oder die Kopierschaltfläche verwenden, um es in die Zwischenablage zu kopieren.
    """)
    components.html("""
        <iframe width="100%" height="180" src="https://www.youtube.com/embed/OB99E7Y1cMA" 
        title="Demo-Video auf Deutsch" frameborder="0" allowfullscreen></iframe>
    """, height=180)

# Helper function to download file from URL
def download_file(url, local_filename):
    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(local_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return local_filename
    except Exception as e:
        st.error(f"Failed to download {url}: {e}")
        return None

# Helper function to split audio into chunks
def split_audio(file_path, chunk_size=20*1024*1024):  # 20 MB chunks
    try:
        audio = AudioSegment.from_file(file_path)
        chunks = []
        duration = len(audio)
        bytes_per_second = audio.frame_rate * audio.sample_width * audio.channels
        chunk_length_ms = int((chunk_size / bytes_per_second) * 1000)

        for i in range(0, duration, chunk_length_ms):
            chunk = audio[i:i+chunk_length_ms]
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
                chunk.export(temp_file.name, format="mp3")
                chunks.append(temp_file.name)

        return chunks
    except Exception as e:
        st.error(f"Error splitting audio file {file_path}: {e}")
        return []

# Helper function to generate timestamps
def generate_minute_based_timestamps(transcription, total_duration_seconds, interval_seconds=60):
    words = transcription.split()
    total_words = len(words)
    words_per_interval = max(1, total_words // (total_duration_seconds // interval_seconds))

    result = []
    for i in range(0, total_words, words_per_interval):
        current_time_seconds = (i // words_per_interval) * interval_seconds
        minutes, seconds = divmod(current_time_seconds, 60)
        timestamp = f"[{minutes}:{seconds:02d}]"
        line = f"{timestamp}\n{' '.join(words[i:i + words_per_interval])}"
        result.append(line)
    return "\n\n".join(result)

# Function to handle transcription
def transcribe_audio(api_key, files, urls, language, include_timestamps, progress_bar, status_text):
    client = OpenAI(api_key=api_key)
    total_files = len(files) + len(urls)
    processed_files = 0
    full_result = ""

    for file in files:
        processed_files += 1
        progress = int((processed_files - 1) / total_files * 100)
        progress_bar.progress(progress)
        status_text.text(f"Processing file {file.name}")

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.' + file.type.split('/')[-1]) as temp_file:
                temp_file.write(file.read())
                temp_file_path = temp_file.name

            audio = AudioSegment.from_file(temp_file_path)
            total_duration_seconds = len(audio) // 1000

            transcription = "Sample transcription from OpenAI."  # Replace with actual API call logic
            if include_timestamps:
                transcription = generate_minute_based_timestamps(transcription, total_duration_seconds)

            full_result += transcription + "\n\n"

        except Exception as e:
            st.error(f"Error transcribing {file.name}: {str(e)}")
        finally:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    progress_bar.progress(100)
    status_text.text("Transcription completed successfully!")
    return full_result

# Streamlit interface
st.header("🔑 Geben Sie Ihren OpenAI-API-Schlüssel ein")
api_key = st.text_input("OpenAI-API-Schlüssel:", type="password")

st.header("📂 Audio- oder Videodateien hochladen oder URLs eingeben")
file_upload = st.file_uploader(
    "Audio- oder Videodateien hochladen (MP3, WAV, OGG, FLAC, MP4, MKV, AVI)", 
    type=["mp3", "wav", "ogg", "flac", "mp4", "mkv", "avi"], 
    accept_multiple_files=True
)
url_input = st.text_area("Oder geben Sie Audio-/Video-URLs ein (eine pro Zeile):")

st.header("⚙️ Optionen")
language = st.selectbox("Sprache auswählen", ["de", "en", "it", "fr", "es"], format_func=lambda x: {
    "de": "Deutsch", "en": "Englisch", "it": "Italienisch", "fr": "Französisch", "es": "Spanisch"
}.get(x, x))
include_timestamps = st.checkbox("Zeitstempel im Transkript aufnehmen")

if st.button("Transkribieren"):
    if not api_key:
        st.error("Bitte geben Sie Ihren OpenAI-API-Schlüssel ein.")
    elif not file_upload and not url_input.strip():
        st.error("Bitte laden Sie mindestens eine Audio- oder Videodatei hoch oder geben Sie eine URL ein.")
    else:
        progress_bar = st.progress(0)
        status_text = st.empty()
        status_text.text("Transkription startet...")

        transcription = transcribe_audio(
            api_key=api_key,
            files=file_upload,
            urls=[url.strip() for url in url_input.split('\n') if url.strip()],
            language=language,
            include_timestamps=include_timestamps,
            progress_bar=progress_bar,
            status_text=status_text
        )

        if transcription:
            st.success("Transkription erfolgreich abgeschlossen!")
            st.text_area("Transkriptionsergebnis:", transcription, height=300)
