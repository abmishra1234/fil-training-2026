"""
   06_image_generate.py - generate one image and save it as PNG.

    python 06_image_generate.py         (one image, docs prompt)
    python 06_image_generate.py --n 3   (three variations, deck "Try it")
    python 06_image_generate.py --prompt "a robot teacher" --size 1536x1024

    Image calls take noticeably longer than chat calls - be patient.
"""
import os
import sys
import argparse
import base64

from pathlib import Path
from llm_client import get_client, settings

parser = argparse.ArgumentParser(description="Generate an image using the LLM client.")
parser.add_argument("--prompt", type=str, default="a robot teacher", help="Prompt for natural image generation.")
parser.add_argument("--size", type=str, default="1024x1024", help="Size of the generated image (e.g., 256x256, 512x512, 1024x1024).")
parser.add_argument("--n", type=int, default=1, help="Number of images to generate.")
args = parser.parse_args()

client = get_client()
img = client.images.generate(
    model=settings.image_model,
    prompt=args.prompt,
    size=args.size,
    n=args.n
)

# Save the generated images to files
output_dir = Path("output/images")
output_dir.mkdir(parents=True, exist_ok=True)

for i, image_data in enumerate(img.data, start=1):
    image_path = output_dir / f"image_{i}.png"
    image_path.write_bytes(base64.b64decode(image_data.b64_json))
    print("saved image to", image_path.resolve())
    