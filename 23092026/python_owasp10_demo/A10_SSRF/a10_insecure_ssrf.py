import requests # type: ignore
from fastapi import FastAPI, HTTPException # type: ignore
from fastapi.responses import Response # type: ignore

app = FastAPI(title="A10 SSRF - Insecure")

@app.get('/fetch_image')
async def fetch_image(url: str):
    # Insecure: Making a request to a user-supplied URL without validation
    try:
        response = requests.get(url)
        response.raise_for_status()
        return Response(content=response.content, media_type="image/jpeg")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error fetching image: {e}")
