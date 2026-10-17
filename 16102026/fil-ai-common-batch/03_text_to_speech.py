"""
04_text_to_speech.py - turn text into speech.mp3 (deck: "A gateway-ready version").

Creates output/speech.mp3, which 05_transcribe.py then reads back.
Lab: generate the same sentence with two voices (alloy, verse, coral...) and compare.
"""

from pathlib import Path
import sys

from llm_client import get_client, settings

client = get_client()

# Path to output speech.mp3
out_dir = Path(__file__).with_name("output")
out_dir.mkdir(exist_ok=True)
speech_path = out_dir / "speech.mp3"

with client.audio.speech.with_streaming_response.create(
    model=settings.tts_model,
    voice="alloy",
    input="Hello, world! This is a test of the text-to-speech functionality.",
    instructions="Speak in warn and upbeat tone, as if you are welcoming a new user to the platform.",
) as response:
    response.stream_to_file(speech_path)
    print(f"Saved speech to {speech_path}")

# Note: the OpenAI TTS API does not return token usage metadata.







