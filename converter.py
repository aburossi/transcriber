import streamlit as st
from pydub import AudioSegment
import os
from io import BytesIO

# Supported formats
formats = ["mp3", "wav", "ogg", "flac"]

# Title
st.title("Simple Audio Converter")

# Upload audio file
uploaded_file = st.file_uploader("Upload an audio file", type=formats)

# Choose output format
output_format = st.selectbox("Choose output format", formats)

if uploaded_file is not None:
    # Display file details
    st.write(f"Uploaded file: {uploaded_file.name}")
    
    # Convert audio file
    audio = AudioSegment.from_file(uploaded_file)
    
    # Button to start conversion
    if st.button("Convert"):
        # Create output in-memory
        output = BytesIO()
        audio.export(output, format=output_format)
        output.seek(0)
        
        # Display download button
        st.download_button(
            label="Download converted file",
            data=output,
            file_name=f"converted.{output_format}",
            mime=f"audio/{output_format}"
        )
