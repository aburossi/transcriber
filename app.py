import streamlit as st
from openai import OpenAI
import os
from pydub import AudioSegment
import tempfile
import threading
import requests
from io import StringIO

# Set page configuration
st.set_page_config(
    page_title="Audio Transcription App",
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
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return local_filename

# Function to split audio into chunks
def split_audio(file_path, chunk_size=20*1024*1024):  # 20 MB chunks
    audio = AudioSegment.from_mp3(file_path)
    chunks = []
    duration = len(audio)
    chunk_length = int((chunk_size / (audio.frame_rate * audio.sample_width * audio.channels)) * 1000)
    
    for i in range(0, duration, chunk_length):
        chunk = audio[i:i+chunk_length]
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
            chunk.export(temp_file.name, format="mp3")
            chunks.append(temp_file.name)
    
    return chunks

# Function to handle transcription
def transcribe_audio(api_key, files, urls, include_timestamps, progress_bar, status_text):
    client = OpenAI(api_key=api_key)
    total_files = len(files) + len(urls)
    processed_files = 0
    full_result = ""

    for file in files:
        processed_files += 1
        progress = int((processed_files / total_files) * 100)
        progress_bar.progress(progress)
        status_text.text(f"Processing file {processed_files} of {total_files}: {file.name}")
        
        # Save uploaded file to a temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
            temp_file.write(file.read())
            temp_file_path = temp_file.name
        
        try:
            file_size = os.path.getsize(temp_file_path)
            if file_size > 20 * 1024 * 1024:  # If file is larger than 20 MB
                chunks = split_audio(temp_file_path)
                for idx, chunk in enumerate(chunks, start=1):
                    progress = int((processed_files / total_files) * 100 + (idx / len(chunks)) * 50)
                    progress_bar.progress(progress)
                    status_text.text(f"Transcribing chunk {idx} of {len(chunks)} for {file.name}...")
                    with open(chunk, "rb") as audio_file:
                        transcription = client.audio.transcriptions.create(
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
                    transcription = client.audio.transcriptions.create(
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
        progress = int((processed_files / total_files) * 100)
        progress_bar.progress(progress)
        status_text.text(f"Processing URL {processed_files} of {total_files}: {url}")
        
        try:
            local_filename = f"temp_audio_{processed_files}.mp3"
            download_file(url, local_filename)
            file_size = os.path.getsize(local_filename)
            if file_size > 20 * 1024 * 1024:
                chunks = split_audio(local_filename)
                for idx, chunk in enumerate(chunks, start=1):
                    progress = int((processed_files / total_files) * 100 + (idx / len(chunks)) * 50)
                    progress_bar.progress(progress)
                    status_text.text(f"Transcribing chunk {idx} of {len(chunks)} for {url}...")
                    with open(chunk, "rb") as audio_file:
                        transcription = client.audio.transcriptions.create(
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
                    transcription = client.audio.transcriptions.create(
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
        # Implement timestamp generation if needed
        # For simplicity, here we assume the transcription includes timestamps
        # Modify this section based on your specific timestamp generation logic
        full_result = generate_minute_based_timestamps(full_result, interval_minutes=1)

    return full_result

# Function to generate minute-based timestamps
def generate_minute_based_timestamps(text, interval_minutes):
    words = text.split()  # Split text into words
    num_words = len(words)
    total_duration = num_words / 160 * 60  # Assuming an average of 160 words per minute
    timestamps = []
    timestamp_text = ""
    
    # Add a timestamp every 'interval_minutes'
    current_time = 0  # Time in seconds
    words_per_minute = int(160 * interval_minutes)  # Approximate number of words in each interval
    
    for i in range(0, num_words, words_per_minute):
        minute = current_time // 60
        second = current_time % 60
        timestamp = f"[{int(minute):02d}:{int(second):02d}]"
        timestamps.append(timestamp)
        chunk = " ".join(words[i:i + words_per_minute])
        timestamp_text += f"{timestamp} {chunk}\n\n"
        current_time += interval_minutes * 60  # Increment the time by the interval in seconds
    
    return timestamp_text

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
        
        # Start transcription in a separate thread to prevent blocking
        def run_transcription():
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
                    data=transcription_io,
                    file_name=transcription_filename,
                    mime="text/plain"
                )
        
        threading.Thread(target=run_transcription, daemon=True).start()

# Function to display the transcription result (optional)
# This is handled within the `run_transcription` function above
