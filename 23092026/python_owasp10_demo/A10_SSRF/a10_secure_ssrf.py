import requests # type: ignore
from fastapi import FastAPI, HTTPException # type: ignore
from fastapi.responses import Response # type: ignore
from urllib.parse import urlparse

app = FastAPI(title="A10 SSRF - Secure")

# Whitelist of allowed domains
ALLOWED_DOMAINS = {'images.example.com', 'static.example.com', 'picsum.photos'}

@app.get('/fetch_image')
async def fetch_image(url: str):
    parsed_url = urlparse(url)

    # Secure: Validate the domain against a whitelist
    if parsed_url.hostname in ALLOWED_DOMAINS:
        try:
            response = requests.get(url)
            response.raise_for_status()
            return Response(content=response.content, media_type="image/jpeg")
        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=500, detail=f"Error fetching image: {e}")
    else:
        raise HTTPException(status_code=403, detail="Forbidden domain")
