import streamlit as st
from openai import OpenAI
import os
from pydub import AudioSegment
import tempfile
import requests
from io import StringIO
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

# Sidebar Instructions
with st.sidebar:
    st.header("❗ **So verwenden Sie diese App**")
    st.markdown("""
    1. **Geben Sie Ihren OpenAI-API-Schlüssel ein**: Erhalten Sie Ihren API-Schlüssel von [OpenAI](https://platform.openai.com/account/api-keys).
    2. **Laden Sie Audio- oder Videodateien hoch oder geben Sie URLs ein**: Unterstützte Formate sind MP3, WAV, OGG, FLAC, MP4, MKV, AVI.
    3. **Optionen wählen**: Wählen Sie die Sprache und ob Zeitstempel im Transkript aufgenommen werden sollen.
    4. **Transkribieren**: Starten Sie den Prozess und erhalten Sie das Transkript.
    5. **Transkript herunterladen oder kopieren**: Nach Abschluss können Sie das Transkript herunterladen oder kopieren.
    """)
    components.html("""
        <iframe width="100%" height="180" src="https://www.youtube.com/embed/NsTAjBdHb1k" 
        title="Demo-Video auf Deutsch" frameborder="0" allow="accelerometer; autoplay; 
        clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen>
        </iframe>
    """, height=180)
    st.markdown("---")
    st.header("📜 Lizenz")
    st.markdown("Diese Anwendung steht unter der [MIT-Lizenz](https://opensource.org/licenses/MIT).")
    st.header("💬 Kontakt")
    st.markdown("**Kontakt**: [Pietro](mailto:pietro.rossi@bbw.ch)")

# Helper Functions
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

def split_audio(file_path, chunk_size=20 * 1024 * 1024):
    try:
        audio = AudioSegment.from_file(file_path)
        chunks = []
        duration = len(audio)
        bytes_per_second = audio.frame_rate * audio.sample_width * audio.channels
        chunk_length_ms = int((chunk_size / bytes_per_second) * 1000)

        for i in range(0, duration, chunk_length_ms):
            chunk = audio[i:i + chunk_length_ms]
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
                chunk.export(temp_file.name, format="mp3")
                chunks.append(temp_file.name)

        return chunks
    except Exception as e:
        st.error(f"Error splitting audio file {file_path}: {e}")
        return []

def generate_minute_based_timestamps(transcript, words_per_minute=150, interval_minutes=1):
    words = transcript.split()
    interval_words = words_per_minute * interval_minutes
    result = []
    timestamp_minutes = 0

    for i in range(0, len(words), interval_words):
        timestamp = f"[{timestamp_minutes:02d}:00]"
        chunk = " ".join(words[i:i + interval_words])
        result.append(f"{timestamp} {chunk}")
        timestamp_minutes += interval_minutes

    return "\n".join(result)

def transcribe_audio(api_key, files, urls, language, include_timestamps, progress_bar, status_text):
    client = OpenAI(api_key=api_key)
    total_files = len(files) + len(urls)
    processed_files = 0
    full_result = ""

    for file in files:
        processed_files += 1
        progress_bar.progress(processed_files / total_files)
        status_text.text(f"Processing file {file.name}")

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file.type.split('/')[-1]}") as temp_file:
                temp_file.write(file.read())
                temp_file_path = temp_file.name

            file_size = os.path.getsize(temp_file_path)
            if file_size > 20 * 1024 * 1024:
                chunks = split_audio(temp_file_path)
                for chunk in chunks:
                    with open(chunk, "rb") as audio_file:
                        transcription = client.audio.transcriptions.create(
                            model="whisper-1",
                            file=audio_file,
                            response_format="text",
                            language=language
                        )
                        full_result += transcription + " "
            else:
                with open(temp_file_path, "rb") as audio_file:
                    transcription = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        response_format="text",
                        language=language
                    )
                    full_result += transcription + " "
        except Exception as e:
            st.error(f"Error transcribing {file.name}: {str(e)}")
        finally:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    if include_timestamps:
        full_result = generate_minute_based_timestamps(full_result)

    progress_bar.progress(1.0)
    status_text.text("Transcription completed successfully!")
    return full_result

# Streamlit UI
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
language = st.selectbox(
    "Sprache auswählen", 
    ["de", "en", "it", "fr", "es"], 
    format_func=lambda x: {
        "de": "Deutsch", 
        "en": "Englisch", 
        "it": "Italienisch", 
        "fr": "Französisch", 
        "es": "Spanisch"
    }.get(x, x)
)
include_timestamps = st.checkbox("Zeitstempel im Transkript aufnehmen")

if st.button("Transkribieren"):
    if not api_key:
        st.error("Bitte geben Sie Ihren OpenAI-API-Schlüssel ein.")
    elif not file_upload and not url_input.strip():
        st.error("Bitte laden Sie mindestens eine Datei hoch oder geben Sie eine URL ein.")
    else:
        urls = [url.strip() for url in url_input.splitlines() if url.strip()]
        progress_bar = st.progress(0)
        status_text = st.empty()

        transcription = transcribe_audio(
            api_key=api_key,
            files=file_upload,
            urls=urls,
            language=language,
            include_timestamps=include_timestamps,
            progress_bar=progress_bar,
            status_text=status_text
        )

        if transcription:
            st.success("Transkription erfolgreich abgeschlossen!")
            st.text_area("Transkriptionsergebnis:", transcription, height=300)

            transcription_json = json.dumps(transcription)

            copy_button_html = f"""
            <div style="margin-top: 10px;">
                <button onclick="copyToClipboard()" style="background-color:#4CAF50; border:none; color:white; padding:10px 20px; text-align:center;
                text-decoration:none; display:inline-block; font-size:16px; border-radius:5px; cursor:pointer;">
                    📋 In die Zwischenablage kopieren
                </button>
            </div>
            <script>
                function copyToClipboard() {{
                    const text = {json.dumps(transcription)};
                    navigator.clipboard.writeText(text).then(function() {{
                        alert("Transkription in die Zwischenablage kopiert!");
                    }}, function(err) {{
                        alert("Kopieren des Texts fehlgeschlagen: ", err);
                    }});
                }}
            </script>
            """
            components.html(copy_button_html, height=100)

            st.download_button(
                label="⬇️ Transkription herunterladen",
                data=transcription,
                file_name="transcription.txt",
                mime="text/plain"
            )
