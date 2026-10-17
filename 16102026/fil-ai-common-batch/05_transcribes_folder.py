"""
    05_transcribe.py - speech to text for one file.
    python 05_transcribe.py (uses output/speech.mp3 from 04)
"""
import os
import sys

from pathlib import Path
from llm_client import get_client, settings


client = get_client()

# next stpe is to process the audio file from the given folder
def transcribe_audio_file(audio_file_path: Path):
    """
    Transcribe the audio file using the LLM client.

    Args:
        audio_file_path (Path): Path to the audio file to be transcribed.

    Returns:
        str: The transcribed text.
    """
    if not audio_file_path.exists():
        print(f"Audio file {audio_file_path} does not exist.")
        return None

    with open(audio_file_path, "rb") as audio_file:
        response = client.audio.transcriptions.create(
            model=settings.stt_model,
            file=audio_file,
            response_format="text"
        )
    
    return response

# I need to iterate the given folder and transcribe all the audio files in it
def transcribe_folder(folder_path: Path):
    for audio_file_path in folder_path.glob("*.mp*"):
        print(f"Transcribing {audio_file_path}...")
        transcribed_text = transcribe_audio_file(audio_file_path)
        if transcribed_text:
            output_file_path = audio_file_path.with_suffix(".txt")
            with open(output_file_path, "w") as output_file:
                output_file.write(transcribed_text)
            print(f"Transcription saved to {output_file_path}")


if __name__ == "__main__":
    # Check if the folder path is provided as a command-line argument
    if len(sys.argv) < 2:
        print("Usage: python 05_transcribe.py <folder_path>")
        sys.exit(1)

    folder_path = Path(sys.argv[1])

    if not folder_path.is_dir():
        print(f"{folder_path} is not a valid directory.")
        sys.exit(1)

    transcribe_folder(folder_path) 

