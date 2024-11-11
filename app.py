import streamlit as st
from openai import OpenAI
import os
from pydub import AudioSegment
import tempfile
import requests
from io import StringIO
import converter  # Import the conversion function
import json
import streamlit.components.v1 as components

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
    2. **Upload Audio Files or Enter URLs**: You can either upload audio files (MP3, WAV, OGG, FLAC) directly or provide URLs to audio files.
    3. **Choose Options**: Select language and whether to include timestamps in the transcription.
    4. **Transcribe**: Click the "Transcribe" button to start the process.
    5. **Download or Copy Transcription**: Once completed, download the transcription as a text file or use the copy button to save it to the clipboard.
    """)

    st.header("👉 **Best Practices**")
    st.markdown("""
    - Ensure your audio files are in supported formats (MP3, WAV, OGG, FLAC).
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

# Function to generate minute-based timestamps with adjusted WPM
def generate_minute_based_timestamps(text, interval_minutes=1, words_per_minute=100):
    words = text.split()
    num_words = len(words)
    words_per_interval = words_per_minute * interval_minutes
    timestamp_text = ""
    current_time = 0

    for i in range(0, num_words, words_per_interval):
        minute = current_time // 60
        second = current_time % 60
        timestamp = f"[{minute:02d}:{second:02d}]"
        chunk = " ".join(words[i:i + words_per_interval])
        timestamp_text += f"{timestamp} {chunk}\n\n"
        current_time += interval_minutes * 60

    return timestamp_text

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
            # Download the file
            local_filename = f"temp_audio_{processed_files}"
            url_extension = url.split('.')[-1].lower()
            if url_extension not in converter.SUPPORTED_FORMATS:
                st.error(f"Unsupported file format from URL: {url}")
                continue
            temp_download_path = f"{local_filename}.{url_extension}"
            downloaded_file = download_file(url, temp_download_path)
            if not downloaded_file:
                continue

            # Convert to MP3 if necessary
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
        full_result = generate_minute_based_timestamps(full_result, interval_minutes=1)

    progress_bar.progress(100)
    status_text.text("Transcription completed successfully!")
    return full_result

# Streamlit Widgets
st.header("🔑 Enter Your OpenAI API Key")
api_key = st.text_input("OpenAI API Key:", type="password")

st.header("📂 Upload Audio Files or Enter URLs")
file_upload = st.file_uploader(
    "Upload audio files (MP3, WAV, OGG, FLAC)", 
    type=["mp3", "wav", "ogg", "flac"], 
    accept_multiple_files=True
)
url_input = st.text_area("Or enter audio URLs (one per line):")

st.header("⚙️ Options")

# Language selection
language = st.selectbox(
    "Select Language", 
    ["de", "en", "it", "fr", "es"], 
    format_func=lambda x: {
        "de": "German", 
        "en": "English", 
        "it": "Italian", 
        "fr": "French", 
        "es": "Spanish"
    }.get(x, x)
)

# Timestamp option with explanation
include_timestamps = st.checkbox(
    "Include Timestamps in Transcription (based on estimated word count, not exact seconds)"
)

# Transcribe Button
if st.button("Transcribe"):
    if not api_key:
        st.error("Please enter your OpenAI API key.")
    elif not file_upload and not url_input.strip():
        st.error("Please upload at least one audio file or enter a URL.")
    else:
        urls = [url.strip() for url in url_input.strip().split('\n') if url.strip()]

        progress_bar = st.progress(0)
        status_text = st.empty()
        status_text.text("Starting transcription...")

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
            st.success("Transcription completed successfully!")
            
            # Display the transcription in a read-only text area
            transcription_area = st.text_area(
                "Transcription Result:",
                transcription,
                height=300,
                key="transcription"
            )

            # Encode the transcription text safely for JavaScript
            transcription_json = json.dumps(transcription)

            # Create the HTML and JavaScript for the copy button
            copy_button_html = f"""
            <div style="margin-top: 10px;">
                <button onclick="copyToClipboard()" style="background-color:#4CAF50; border:none; color:white; padding:10px 20px; text-align:center;
                text-decoration:none; display:inline-block; font-size:16px; border-radius:5px; cursor:pointer;">
                    📋 Copy to Clipboard
                </button>
            </div>
            <script>
                function copyToClipboard() {{
                    const text = {transcription_json};
                    navigator.clipboard.writeText(text).then(function() {{
                        alert("Transcription copied to clipboard!");
                    }}, function(err) {{
                        alert("Failed to copy text: ", err);
                    }});
                }}
            </script>
            """

            # Embed the HTML and JavaScript in the Streamlit app
            components.html(copy_button_html, height=100)
            
            # Provide a download button as an alternative
            transcription_filename = "transcription.txt"
            transcription_io = StringIO(transcription)
            st.download_button(
                label="⬇️ Download Transcription as .txt",
                data=transcription_io.getvalue(),
                file_name=transcription_filename,
                mime="text/plain"
            )
