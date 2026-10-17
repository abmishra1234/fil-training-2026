"""
05_transcribe.py - speech to text for one file.

    python 05_transcribe.py                 (uses output/speech.mp3 from 03)
    python 04_transcribe.py my_audio.mp3
"""
import sys
from pathlib import Path

from llm_client import get_client, settings

client = get_client()

# Path to audio file to transcribe
audio_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("output") / "speech.mp3"

if not audio_path.exists():
    print(f"Audio file not found: {audio_path}")
    sys.exit(1)

if not audio_path.suffix.lower() in [".mp3", ".wav", ".m4a"]:
    print(f"Unsupported audio file format: {audio_path.suffix}")
    sys.exit(1)

# first opem the audio file and read it into memory
with open(audio_path, "rb") as audio_file:
    transcription = client.audio.transcriptions.create(
        model=settings.stt_model,
        file=audio_file,
        response_format="text"
    )
    print(transcription)







