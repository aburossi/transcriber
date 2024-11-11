import streamlit as st
import openai
import os
from pydub import AudioSegment
import tempfile
import requests
from io import StringIO
import re

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

# Function to generate minute-based timestamps
def generate_minute_based_timestamps(text, interval_minutes=1):
    words = text.split()
    num_words = len(words)
    words_per_interval = 160 * interval_minutes  # Assuming 160 words per minute
    timestamp_text = ""
    current_time = 0  # in seconds

    for i in range(0, num_words, words_per_interval):
        minute = current_time // 60
        second = current_time % 60
        timestamp = f"[{int(minute):02d}:{int(second):02d}]"
        chunk = " ".join(words[i:i + words_per_interval])
        timestamp_text += f"{timestamp} {chunk}\n\n"
        current_time += interval_minutes * 60

    return timestamp_text

# Function to handle transcription
def transcribe_audio(api_key, files, urls, include_timestamps, progress_bar, status_text):
    openai.api_key = api_key
    total_files = len(files) + len(urls)
    processed_files = 0
    full_result = ""

    for file in files:
        processed_files += 1
        progress = int((processed_files - 1) / total_files * 100)
        progress_bar.progress(progress)
        status_text.text(f"Processing file {processed_files} of {total_files}: {file.name}")

        # Save uploaded file to a temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
            temp_file.write(file.read())
            temp_file_path = temp_file.name

        try:
            file_size = os.path.getsize(temp_file_path)
            if file_size > 20 * 1024 * 1024:  # If file is larger than 20 MB
                status_text.text(f"Splitting large audio file {file.name}...")
                chunks = split_audio(temp_file_path)
                for idx, chunk in enumerate(chunks, start=1):
                    status_text.text(f"Transcribing chunk {idx} of {len(chunks)} for {file.name}...")
                    progress_increment = (100 / total_files) / len(chunks)
                    current_progress = progress + int((idx / len(chunks)) * (100 / total_files))
                    progress_bar.progress(min(current_progress, 100))
                    with open(chunk, "rb") as audio_file:
                        transcription = openai.Audio.transcribe(
                            model="whisper-1",
                            file=audio_file,
                            response_format="text",
                            language="de"  # Adjust language as needed
                        )
                    full_result += transcription + " "
                    os.unlink(chunk)  # Delete temporary chunk file
            else:
                status_text.text(f"Transcribing {file.name}...")
                with open(temp_file_path, "rb") as audio_file:
                    transcription = openai.Audio.transcribe(
                        model="whisper-1",
                        file=audio_file,
                        response_format="text",
                        language="de"  # Adjust language as needed
                    )
                full_result += transcription + " "
        except Exception as e:
            st.error(f"Error transcribing {file.name}: {e}")
        finally:
            os.unlink(temp_file_path)  # Delete the temporary file

    for url in urls:
        processed_files += 1
        progress = int((processed_files - 1) / total_files * 100)
        progress_bar.progress(progress)
        status_text.text(f"Processing URL {processed_files} of {total_files}: {url}")

        try:
            local_filename = f"temp_audio_{processed_files}.mp3"
            downloaded_file = download_file(url, local_filename)
            if not downloaded_file:
                continue  # Skip to next file if download failed

            file_size = os.path.getsize(local_filename)
            if file_size > 20 * 1024 * 1024:
                status_text.text(f"Splitting large audio file from {url}...")
                chunks = split_audio(local_filename)
                for idx, chunk in enumerate(chunks, start=1):
                    status_text.text(f"Transcribing chunk {idx} of {len(chunks)} for {url}...")
                    progress_increment = (100 / total_files) / len(chunks)
                    current_progress = progress + int((idx / len(chunks)) * (100 / total_files))
                    progress_bar.progress(min(current_progress, 100))
                    with open(chunk, "rb") as audio_file:
                        transcription = openai.Audio.transcribe(
                            model="whisper-1",
                            file=audio_file,
                            response_format="text",
                            language="de"  # Adjust language as needed
                        )
                    full_result += transcription + " "
                    os.unlink(chunk)  # Delete temporary chunk file
            else:
                status_text.text(f"Transcribing audio from {url}...")
                with open(local_filename, "rb") as audio_file:
                    transcription = openai.Audio.transcribe(
                        model="whisper-1",
                        file=audio_file,
                        response_format="text",
                        language="de"  # Adjust language as needed
                    )
                full_result += transcription + " "
        except Exception as e:
            st.error(f"Error transcribing from {url}: {e}")
        finally:
            if os.path.exists(local_filename):
                os.remove(local_filename)  # Delete the downloaded file

    if include_timestamps:
        status_text.text("Generating timestamps...")
        full_result = generate_minute_based_timestamps(full_result, interval_minutes=1)

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
        # Prepare list of URLs
        urls = [url.strip() for url in url_input.strip().split('\n') if url.strip()]

        # Initialize progress bar and status text
        progress_bar = st.progress(0)
        status_text = st.empty()
        status_text.text("Starting transcription...")

        # Perform transcription
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
            # Display transcription
            st.text_area("Transcription Result:", transcription, height=300)

            # Provide download option
            transcription_filename = "transcription.txt"
            transcription_io = StringIO(transcription)
            st.download_button(
                label="Download Transcription as .txt",
                data=transcription_io.getvalue(),
                file_name=transcription_filename,
                mime="text/plain"
            )