# converter.py

from pydub import AudioSegment
import os
import subprocess

# Supported audio and video formats
SUPPORTED_AUDIO_FORMATS = ["mp3", "wav", "ogg", "flac"]
SUPPORTED_VIDEO_FORMATS = ["mp4", "avi", "mov", "mkv", "wmv"]

SUPPORTED_FORMATS = SUPPORTED_AUDIO_FORMATS + SUPPORTED_VIDEO_FORMATS

def convert_to_mp3(input_path, output_path):
    """
    Convert an audio file to MP3 format.

    :param input_path: Path to the input audio file.
    :param output_path: Path to save the converted MP3 file.
    :return: True if conversion succeeds, False otherwise.
    """
    try:
        audio = AudioSegment.from_file(input_path)
        audio.export(output_path, format="mp3")
        return True
    except Exception as e:
        print(f"Audio Conversion failed: {e}")
        return False

def extract_audio_from_video(video_path, audio_output_path):
    """
    Extract audio from a video file and save it as an MP3.

    :param video_path: Path to the input video file.
    :param audio_output_path: Path to save the extracted MP3 file.
    :return: True if extraction succeeds, False otherwise.
    """
    try:
        # Use ffmpeg to extract audio
        command = [
            "ffmpeg",
            "-i", video_path,
            "-vn",  # No video
            "-acodec", "mp3",
            "-ab", "192k",
            "-ar", "44100",
            "-y",  # Overwrite if exists
            audio_output_path
        ]
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Video to MP3 extraction failed: {e.stderr.decode()}")
        return False
