# converter.py

from pydub import AudioSegment
import os

# Supported formats
SUPPORTED_FORMATS = ["mp3", "wav", "ogg", "flac"]

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
        print(f"Conversion failed: {e}")
        return False
