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

# Titel
st.title("📄 Audio- & Video-Transkriptions-App")

# Seitenleiste für Anweisungen
with st.sidebar:
    st.header("❗ **So verwenden Sie diese App**")
    
    st.markdown("""
    1. **Geben Sie Ihren OpenAI-API-Schlüssel ein**: Erhalten Sie Ihren API-Schlüssel von [OpenAI](https://platform.openai.com/account/api-keys) und geben Sie ihn links im Feld *OpenAI-API-Schlüssel* ein.
    """)
    
    # Video in die Seitenleiste einbetten
    components.html("""
        <iframe width="100%" height="180" src="https://www.youtube.com/embed/OB99E7Y1cMA" 
        title="Demo-Video auf Deutsch" frameborder="0" allow="accelerometer; autoplay; 
        clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen>
        </iframe>
    """, height=180)
    
    # Fortfahren mit zusätzlichen Anweisungen
    st.markdown("""
    2. **Laden Sie Audio- oder Videodateien hoch oder geben Sie URLs ein**: Sie können entweder Dateien (MP3, WAV, OGG, FLAC, MP4, MKV, AVI) direkt hochladen oder URLs angeben.
    3. **Optionen wählen**: Wählen Sie die Sprache und ob Zeitstempel in das Transkript aufgenommen werden sollen.
    4. **Transkribieren**: Klicken Sie auf die Schaltfläche "Transkribieren", um den Prozess zu starten.
    5. **Transkript herunterladen oder kopieren**: Nach Abschluss können Sie das Transkript als Textdatei herunterladen oder die Kopierschaltfläche verwenden, um es in die Zwischenablage zu kopieren.
    6. **Kosten**: Die Transkription einer Audiodatei kostet 0.006 US$ per Minute. Die Kosten werden vom persönlichen OpenAI-Guthaben gedeckt (s. Video 👆 für eine Anleitung, wie man einen API-Schlüssel generiert und Guthaben laden kann).
    """)

    # Seitenleiste oder Fußzeile für Lizenz- und Kontaktinformationen
    st.markdown("---")
    st.header("📜 Lizenz")
    st.markdown("""
    Diese Anwendung steht unter der [MIT-Lizenz](https://opensource.org/licenses/MIT). 
    Sie dürfen diese Software verwenden, ändern und weitergeben, solange die ursprüngliche Lizenz beibehalten wird.
    """)

    st.header("💬 Kontakt")
    st.markdown("""
    Für Unterstützung, Fragen oder um mehr über die Nutzung dieser App zu erfahren, kannst du gerne auf mich zukommen.
    **Kontakt**: [Pietro](mailto:pietro.rossi@bbw.ch)
    """)


# Function to download file from URL
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


# Function to split audio into chunks
def split_audio(file_path, chunk_size=20*1024*1024):  # 20 MB chunks
    try:
        audio = AudioSegment.from_mp3(file_path)
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

def generate_minute_based_timestamps(transcription, total_duration_seconds, interval_seconds=60):
    """
    Generate timestamps for transcription based on actual audio duration.

    Args:
        transcription (str): The full transcription text.
        total_duration_seconds (int): Total duration of the audio file in seconds.
        interval_seconds (int): Interval in seconds for timestamps.

    Returns:
        str: Transcription text with timestamps, each starting on a new line.
    """
    words = transcription.split()
    total_words = len(words)

    # Calculate the number of words per interval
    words_per_interval = max(1, total_words // (total_duration_seconds // interval_seconds))

    result = []
    for i in range(0, total_words, words_per_interval):
        # Calculate timestamp in minutes and seconds
        current_time_seconds = (i // words_per_interval) * interval_seconds
        minutes, seconds = divmod(current_time_seconds, 60)
        timestamp = f"[{minutes}:{seconds:02d}]"
        
        # Add timestamp and corresponding text to the result
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
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.' + file.type.split('/')[-1]) as temp_file:
                temp_file.write(file.read())
                temp_file_path = temp_file.name

            # Determine file extension
            file_extension = temp_file_path.split('.')[-1].lower()

            # Convert to MP3 if necessary
            if file_extension != 'mp3':
                st.info(f"Converting {file.name} to MP3 format...")
                converted_path = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3').name
                conversion_success = converter.convert_to_mp3(temp_file_path, converted_path)
                if conversion_success:
                    os.unlink(temp_file_path)  # Remove original file
                    temp_file_path = converted_path
                else:
                    st.error(f"Failed to convert {file.name} to MP3.")
                    continue

            file_size = os.path.getsize(temp_file_path)
            if file_size > 20 * 1024 * 1024:
                status_text.text(f"Splitting large audio file {file.name}...")
                chunks = split_audio(temp_file_path)
                for chunk in chunks:
                    with open(chunk, "rb") as audio_file:
                        transcription = client.audio.transcriptions.create(
                            model="whisper-1",
                            file=audio_file,
                            response_format="verbose_json" if include_timestamps else "text",
                            language=language
                        )
                        if include_timestamps:
                            transcription_data = transcription.model_dump()
                            text = transcription_data.get("text", "")
                        else:
                            text = transcription
                        full_result += text + " "
                    os.unlink(chunk)
            else:
                with open(temp_file_path, "rb") as audio_file:
                    transcription = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        response_format="verbose_json" if include_timestamps else "text",
                        language=language
                    )
                    if include_timestamps:
                        transcription_data = transcription.model_dump()
                        text = transcription_data.get("text", "")
                    else:
                        text = transcription
                    full_result += text + " "
        except Exception as e:
            st.error(f"Error transcribing {file.name}: {str(e)}")
        finally:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    for url in urls:
        processed_files += 1
        progress = int((processed_files - 1) / total_files * 100)
        progress_bar.progress(progress)
        status_text.text(f"Processing URL {url}")

        try:
            local_filename = f"temp_audio_{processed_files}"
            url_extension = url.split('.')[-1].lower()
            if url_extension not in converter.SUPPORTED_FORMATS:
                st.error(f"Unsupported file format from URL: {url}")
                continue
            temp_download_path = f"{local_filename}.{url_extension}"
            downloaded_file = download_file(url, temp_download_path)
            if not downloaded_file:
                continue

            if url_extension != 'mp3':
                st.info(f"Converting {url} to MP3 format...")
                converted_path = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3').name
                conversion_success = converter.convert_to_mp3(downloaded_file, converted_path)
                if conversion_success:
                    os.unlink(downloaded_file)  # Remove original file
                    temp_download_path = converted_path
                else:
                    st.error(f"Failed to convert audio from {url} to MP3.")
                    continue

            file_size = os.path.getsize(temp_download_path)
            if file_size > 20 * 1024 * 1024:
                chunks = split_audio(temp_download_path)
                for chunk in chunks:
                    with open(chunk, "rb") as audio_file:
                        transcription = client.audio.transcriptions.create(
                            model="whisper-1",
                            file=audio_file,
                            response_format="verbose_json" if include_timestamps else "text",
                            language=language
                        )
                        if include_timestamps:
                            transcription_data = transcription.model_dump()
                            text = transcription_data.get("text", "")
                        else:
                            text = transcription
                        full_result += text + " "
                    os.unlink(chunk)
            else:
                with open(temp_download_path, "rb") as audio_file:
                    transcription = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        response_format="verbose_json" if include_timestamps else "text",
                        language=language
                    )
                    if include_timestamps:
                        transcription_data = transcription.model_dump()
                        text = transcription_data.get("text", "")
                    else:
                        text = transcription
                    full_result += text + " "
        except Exception as e:
            st.error(f"Error transcribing from {url}: {str(e)}")
        finally:
            if os.path.exists(temp_download_path):
                os.remove(temp_download_path)

    if include_timestamps:
        audio = AudioSegment.from_file(temp_file_path)
        total_duration_seconds = len(audio) // 1000  # Convert milliseconds to seconds
        full_result = generate_minute_based_timestamps(
            full_result, 
            total_duration_seconds=total_duration_seconds, 
            interval_seconds=60  # Default 1-minute intervals
        )

        
        # Generate timestamps
        full_result = generate_minute_based_timestamps(full_result, total_duration_seconds=total_duration_seconds, interval_seconds=60)

    progress_bar.progress(100)
    status_text.text("Transcription completed successfully!")
    return full_result

# Streamlit Widgets
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

include_timestamps = st.checkbox(
    "Zeitstempel im Transkript aufnehmen (basierend auf geschätzter Wortanzahl, nicht exakten Sekunden)"
)

if st.button("Transkribieren"):
    if not api_key:
        st.error("Bitte geben Sie Ihren OpenAI-API-Schlüssel ein.")
    elif not file_upload and not url_input.strip():
        st.error("Bitte laden Sie mindestens eine Audio- oder Videodatei hoch oder geben Sie eine URL ein.")
    else:
        urls = [url.strip() for url in url_input.strip().split('\n') if url.strip()]

        progress_bar = st.progress(0)
        status_text = st.empty()
        status_text.text("Transkription startet...")

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
            
            transcription_area = st.text_area(
                "Transkriptionsergebnis:",
                transcription,
                height=300,
                key="transcription"
            )

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
                    const text = {transcription_json};
                    navigator.clipboard.writeText(text).then(function() {{
                        alert("Transkription in die Zwischenablage kopiert!");
                    }}, function(err) {{
                        alert("Kopieren des Texts fehlgeschlagen: ", err);
                    }});
                }}
            </script>
            """

            components.html(copy_button_html, height=100)
            
            transcription_filename = "transkription.txt"
            transcription_io = StringIO(transcription)
            st.download_button(
                label="⬇️ Transkription als .txt herunterladen",
                data=transcription_io.getvalue(),
                file_name=transcription_filename,
                mime="text/plain"
            )
