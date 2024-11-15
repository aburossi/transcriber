import streamlit as st
from openai import OpenAI
import os
from pydub import AudioSegment
import tempfile
import requests
from io import StringIO
import converter  # Import your updated conversion function
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

# Sidebar with instructions
with st.sidebar:
    st.header("❗ **So verwenden Sie diese App**")
    st.markdown("""
    1. **Geben Sie Ihren OpenAI-API-Schlüssel ein**: Erhalten Sie Ihren API-Schlüssel von [OpenAI](https://platform.openai.com/account/api-keys) und geben Sie ihn links im Feld *OpenAI-API-Schlüssel* ein.
    2. **Laden Sie Audio- oder Videodateien hoch oder geben Sie URLs ein**: Unterstützte Formate: MP3, WAV, OGG, FLAC, MP4, MKV, AVI.
    3. **Optionen wählen**: Wählen Sie die Sprache und ob Zeitstempel im Transkript enthalten sein sollen.
    4. **Transkribieren**: Klicken Sie auf die Schaltfläche "Transkribieren", um den Vorgang zu starten.
    """)
    components.html("""
        <iframe width="100%" height="180" src="https://www.youtube.com/embed/OB99E7Y1cMA" 
        title="Demo-Video auf Deutsch" frameborder="0" allowfullscreen></iframe>
    """, height=180)
    st.markdown("""
    5. **Transkript speichern oder kopieren**: Nach der Transkription können Sie das Ergebnis herunterladen oder in die Zwischenablage kopieren.
    """)

# Helper function to download files from URL
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

# Helper function to split audio into smaller chunks
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

# Function to generate timestamps for transcription
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
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.' + file.type.split('/')[-1]) as temp_file:
                temp_file.write(file.read())
                temp_file_path = temp_file.name

            audio = AudioSegment.from_file(temp_file_path)
            total_duration_seconds = len(audio) // 1000  # Convert milliseconds to seconds

            if include_timestamps:
                transcription = "Your transcription logic here"  # Example
                full_result = generate_minute_based_timestamps(full_result, total_duration_seconds, interval_seconds)
    full_result.append(temp_file)

    [re ADD Clean Up
