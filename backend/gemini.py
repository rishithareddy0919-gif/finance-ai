"""Thin Gemini REST client (standard library only). The API key comes from the GEMINI_API_KEY environment
variable and never leaves the backend. Gemini is used for two jobs only: reading screenshots and
writing explanations. It never calculates risk."""
import base64
import json
import os
import urllib.error
import urllib.request

MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class GeminiError(Exception):
    pass


def call_gemini(prompt, image_bytes=None, mime_type=None, json_mode=False, timeout=30):
    """Return the model's text. Raises GeminiError with a readable message on any failure."""
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise GeminiError("GEMINI_API_KEY is not set on the server")
    parts = [{"text": prompt}]
    if image_bytes is not None:
        parts.append({"inline_data": {"mime_type": mime_type, "data": base64.b64encode(image_bytes).decode()}})
    config = {"temperature": 0}
    if json_mode:
        config["responseMimeType"] = "application/json"
    request = urllib.request.Request(
        URL.format(model=MODEL), data=json.dumps({"contents": [{"parts": parts}], "generationConfig": config}).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": key})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read())
        return body["candidates"][0]["content"]["parts"][0]["text"]
    except urllib.error.HTTPError as e:
        raise GeminiError(f"Gemini returned HTTP {e.code}") from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise GeminiError("Could not reach Gemini") from e
    except (KeyError, IndexError, ValueError) as e:
        raise GeminiError("Gemini returned an unexpected response") from e
