"""
07_image_edit_compose.py - 
combine two input images into one (deck: "A safer version").

Put two images you have the rights to use into inputs/:
    inputs/product.jpeg   inputs/model.jpg
(or pass paths:  python 07_image_edit_compose.py a.png b.png)
"""

import os
import sys

import base64

from pathlib import Path
from datetime import datetime

from openai import APITimeoutError, BadRequestError
from llm_client import get_client, settings

here = Path(__file__).parent
first, second = (Path(sys.argv[1]), Path(sys.argv[2])) if len(sys.argv) > 2 else (here / "inputs" / "product.jpeg", here / "inputs" / "model.jpg")

for p in (first, second):
    if not p.exists():
        raise FileNotFoundError(f"Input file not found: {p}")

image_timeout = float(os.getenv("IMAGE_TIMEOUT_SECONDS", "600"))
if image_timeout <= 0:
    raise ValueError("IMAGE_TIMEOUT_SECONDS must be greater than zero")
client = get_client().with_options(timeout=image_timeout, max_retries=0)
prompt = "Combine the person and the lotion bottle into one polished ad scene"

try:
    print(f"Composing images; waiting up to {image_timeout:g} seconds for a response...", flush=True)
    with open(first, "rb") as a, open(second, "rb") as b:
        result = client.images.edit(model=settings.image_model, image=[a, b], prompt=prompt)
except APITimeoutError:
    raise SystemExit(
        f"Image edit timed out (configured timeout: {image_timeout:g} seconds). "
        "The server may still be processing the request. "
        "If this keeps happening, check your network/proxy or service status. "
        "Set IMAGE_TIMEOUT_SECONDS to allow a longer wait."
    ) from None
except BadRequestError as err:
    raise SystemExit(f"Edit rejected: {err}")

out_dir = here / "output"
out_dir.mkdir(exist_ok=True)

out = out_dir / f"composite_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
out.write_bytes(base64.b64decode(result.data[0].b64_json))
print(f"compose image saved to:", out.resolve())
