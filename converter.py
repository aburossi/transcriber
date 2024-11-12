from pydub import AudioSegment
import moviepy.editor as mp  # Install moviepy with pip install moviepy
import os

# Supported audio and video formats
SUPPORTED_FORMATS = ["mp3", "wav", "ogg", "flac", "mp4", "mkv", "avi"]

def convert_to_mp3(input_path, output_path):
    """
    Convert an audio or video file to MP3 format.

    :param input_path: Path to the input file (audio or video).
    :param output_path: Path to save the converted MP3 file.
    :return: True if conversion succeeds, False otherwise.
    """
    try:
        # Check file extension to determine if it's audio or video
        file_extension = os.path.splitext(input_path)[-1].lower()

        if file_extension in ["mp4", "mkv", "avi"]:
            # Extract audio from video file
            video = mp.VideoFileClip(input_path)
            audio = video.audio
            audio.write_audiofile(output_path, codec="mp3")
        else:
            # Process audio file directly
            audio = AudioSegment.from_file(input_path)
            audio.export(output_path, format="mp3")

        return True
    except Exception as e:
        print(f"Conversion failed: {e}")
        return False
