import streamlit as st
from openai import OpenAI
import os
from pydub import AudioSegment
import tempfile
import requests
from io import StringIO

# Set page configuration
st.set_page_config(
    page_title="📄 Audio Transcription App",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Title
st.title("📄 Audio Transcription App")

# Sidebar for instructions
with st.sidebar:
    st.header("❗ **How to Use This App**")
    st.markdown("""
    1. **Enter your OpenAI API Key**: Obtain your API key from [OpenAI](https://platform.openai.com/account/api-keys) and enter it below.
    2. **Upload Audio Files or Enter URLs**: You can either upload MP3 files directly or provide URLs to audio files.
    3. **Choose Options**: Select whether to include timestamps in the transcription.
    4. **Transcribe**: Click the "Transcribe" button to start the process.
    5. **Download Transcription**: Once completed, download the transcription as a text file.
    """)

    st.header("👉 **Best Practices**")
    st.markdown("""
    - Ensure your audio files are in MP3 format.
    - For large audio files, consider splitting them into smaller segments for more accurate transcription.
    - Keep your API key secure and do not share it publicly.
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

# Function to handle transcription
def transcribe_audio(api_key, files, urls, include_timestamps, progress_bar, status_text):
    client = OpenAI(api_key=api_key)
    total_files = len(files) + len(urls)
    processed_files = 0
    full_result = ""

    def transcription_to_dict(transcription):
        return {
            "text": transcription.get("text", ""),
            "words": [
                {
                    "start": word.get("start"),
                    "end": word.get("end"),
                    "text": word.get("text")
                } for word in transcription.get("words", [])
            ]
        }

    for file in files:
        processed_files += 1
        progress = int((processed_files - 1) / total_files * 100)
        progress_bar.progress(progress)
        status_text.text(f"Processing file {processed_files} of {total_files}: {file.name}")

        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
            temp_file.write(file.read())
            temp_file_path = temp_file.name

        try:
            file_size = os.path.getsize(temp_file_path)
            if file_size > 20 * 1024 * 1024:
                status_text.text(f"Splitting large audio file {file.name}...")
                chunks = split_audio(temp_file_path)
                for idx, chunk in enumerate(chunks, start=1):
                    with open(chunk, "rb") as audio_file:
                        transcription = client.audio.transcriptions.create(
                            model="whisper-1",
                            file=audio_file,
                            response_format="verbose_json" if include_timestamps else "text",
                            language="de"
                        )
                        transcription_dict = transcription_to_dict(transcription)
                        full_result += transcription_dict["text"] + " "
                    os.unlink(chunk)
            else:
                with open(temp_file_path, "rb") as audio_file:
                    transcription = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        response_format="verbose_json" if include_timestamps else "text",
                        language="de"
                    )
                    transcription_dict = transcription_to_dict(transcription)
                    full_result += transcription_dict["text"] + " "
        except Exception as e:
            st.error(f"Error transcribing {file.name}: {str(e)}")
        finally:
            os.unlink(temp_file_path)

    for url in urls:
        processed_files += 1
        progress = int((processed_files - 1) / total_files * 100)
        progress_bar.progress(progress)
        status_text.text(f"Processing URL {processed_files} of {total_files}: {url}")

        try:
            local_filename = f"temp_audio_{processed_files}.mp3"
            downloaded_file = download_file(url, local_filename)
            if not downloaded_file:
                continue

            file_size = os.path.getsize(local_filename)
            if file_size > 20 * 1024 * 1024:
                chunks = split_audio(local_filename)
                for idx, chunk in enumerate(chunks, start=1):
                    with open(chunk, "rb") as audio_file:
                        transcription = client.audio.transcriptions.create(
                            model="whisper-1",
                            file=audio_file,
                            response_format="verbose_json" if include_timestamps else "text",
                            language="de"
                        )
                        transcription_dict = transcription_to_dict(transcription)
                        full_result += transcription_dict["text"] + " "
                    os.unlink(chunk)
            else:
                with open(local_filename, "rb") as audio_file:
                    transcription = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        response_format="verbose_json" if include_timestamps else "text",
                        language="de"
                    )
                    transcription_dict = transcription_to_dict(transcription)
                    full_result += transcription_dict["text"] + " "
        except Exception as e:
            st.error(f"Error transcribing from {url}: {str(e)}")
        finally:
            if os.path.exists(local_filename):
                os.remove(local_filename)

    progress_bar.progress(100)
    status_text.text("Transcription completed successfully!")
    return full_result

# Streamlit Widgets
st.header("🔑 Enter Your OpenAI API Key")
api_key = st.text_input("OpenAI API Key:", type="password")

st.header("📂 Upload MP3 Files or Enter URLs")
file_upload = st.file_uploader("Upload MP3 files", type=["mp3"], accept_multiple_files=True)
url_input = st.text_area("Or enter MP3 URLs (one per line):")

st.header("⚙️ Options")
include_timestamps = st.checkbox("Include Timestamps in Transcription")

# Transcribe Button
if st.button("Transcribe"):
    if not api_key:
        st.error("Please enter your OpenAI API key.")
    elif not file_upload and not url_input.strip():
        st.error("Please upload at least one MP3 file or enter a URL.")
    else:
        urls = [url.strip() for url in url_input.strip().split('\n') if url.strip()]

        progress_bar = st.progress(0)
        status_text = st.empty()
        status_text.text("Starting transcription...")

        transcription = transcribe_audio(
            api_key=api_key,
            files=file_upload,
            urls=urls,
            include_timestamps=include_timestamps,
            progress_bar=progress_bar,
            status_text=status_text
        )

        if transcription:
            st.success("Transcription completed successfully!")
            st.text_area("Transcription Result:", transcription, height=300)

            transcription_filename = "transcription.txt"
            transcription_io = StringIO(transcription)
            st.download_button(
                label="Download Transcription as .txt",
                data=transcription_io.getvalue(),
                file_name=transcription_filename,
                mime="text/plain"
            )
