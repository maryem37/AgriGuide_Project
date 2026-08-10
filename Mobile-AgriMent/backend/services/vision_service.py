import base64
import json
import logging
import re

import httpx

from config.settings import get_settings
from schemas.detection import DetectionResult

logger = logging.getLogger(__name__)
settings = get_settings()

IMAGE_MIME_MAP = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"GIF87a": "image/gif",
    b"GIF89a": "image/gif",
    b"RIFF": "image/webp",  # WEBP starts with RIFF, then has WEBP at offset 8
    b"BM": "image/bmp",
    b"II*\x00": "image/tiff",
    b"MM\x00*": "image/tiff",
    b"HEIF": "image/heif",
}


def detect_image_mime_type(image_bytes: bytes) -> str:
    """Detect the MIME type of an image from its magic bytes."""
    for magic, mime in IMAGE_MIME_MAP.items():
        if image_bytes.startswith(magic):
            if mime == "image/webp" and len(image_bytes) >= 12:
                if image_bytes[8:12] == b"WEBP":
                    return "image/webp"
            else:
                return mime
    return "image/jpeg"


class VisionParseError(ValueError):
    """Raised when the vision API response cannot be parsed as JSON."""


VISION_PROMPT = """Analyze this image and identify the insect shown.

If the image is blurry, does not show an insect, or you cannot identify the species, return:
{"species": "Unclear image", "scientific_name": "N/A", "confidence": 0.0, "risk_level": "low", "description": "The image does not clearly show an identifiable insect.", "recommendation": "| Retake the photo in good lighting| Ensure the insect is in focus and centered| Capture from multiple angles| Use macro mode for small insects"}

If you can identify the insect, assess its agricultural risk:
- low: Beneficial insect (ladybug, bee, lacewing)
- medium: Minor pest, manageable with basic controls
- high: Significant pest that damages crops if untreated
- critical: Major threat requiring immediate action

Return ONLY a valid JSON object:
{"species": "Common English name", "scientific_name": "Genus species", "confidence": 0.85, "risk_level": "high", "description": "What the insect is, which crops it affects, and signs of damage.", "recommendation": "| Step 1: specific action| Step 2: specific action| Step 3: specific action| Step 4: specific action"}

The recommendation must have 3-4 actionable steps separated by | with specific product names or techniques. No markdown. No code blocks."""


class VisionService:
    def __init__(self):
        # Accept both 'gemma' (internal name) and the common 'gemini' spelling
        self.provider = settings.VISION_PROVIDER.lower()
        if self.provider == "gemini":
            self.provider = "gemma"
        self._client = httpx.AsyncClient(timeout=45.0)

    async def analyze_image(self, image_bytes: bytes) -> DetectionResult:
        provider_order = [self.provider]
        if self.provider != "gemma":
            provider_order.append("gemma")
        if self.provider != "qwen":
            provider_order.append("qwen")
        if self.provider != "mistral":
            provider_order.append("mistral")

        last_error: Exception | None = None

        for provider in provider_order:
            try:
                if provider == "gemma":
                    return await self._analyze_with_gemma(image_bytes)
                if provider == "qwen":
                    return await self._analyze_with_qwen(image_bytes)
                return await self._analyze_with_mistral(image_bytes)
            except VisionParseError as exc:
                logger.warning(f"[{provider}] returned unparsable JSON: {exc}")
                last_error = exc
            except ValueError as exc:
                logger.warning(f"[{provider}] error: {exc}")
                last_error = exc

        if last_error:
            raise last_error
        raise VisionParseError("Could not parse analysis result. Please try again.")

    async def _analyze_with_mistral(self, image_bytes: bytes) -> DetectionResult:
        base64_image = base64.b64encode(image_bytes).decode("utf-8")
        mime_type = detect_image_mime_type(image_bytes)

        if not settings.MISTRAL_API_KEY:
            raise ValueError("Mistral API key not configured")

        headers = {
            "Authorization": f"Bearer {settings.MISTRAL_API_KEY}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": settings.MISTRAL_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": f"data:{mime_type};base64,{base64_image}",
                        },
                        {
                            "type": "text",
                            "text": VISION_PROMPT,
                        },
                    ],
                }
            ],
            "temperature": 0.1,
            "max_tokens": 4096,
            "response_format": {"type": "json_object"},
        }

        try:
            response = await self._client.post(
                settings.MISTRAL_API_URL, headers=headers, json=payload
            )
            response.raise_for_status()
        except httpx.TimeoutException:
            logger.error("Mistral API timeout")
            raise ValueError("Analysis timed out. Please try again.")
        except httpx.HTTPStatusError as exc:
            logger.error(
                f"Mistral API error: {exc.response.status_code} - {exc.response.text}"
            )
            raise ValueError(f"Analysis service error: {exc.response.status_code}")

        data = response.json()

        # Better error handling for Mistral API response
        if "choices" not in data or not data["choices"]:
            logger.error(f"Mistral API returned no choices: {data}")
            raise ValueError("Analysis failed: No results from vision API")

        content = data["choices"][0]["message"]["content"]
        return self._parse_response(content)

    async def _analyze_with_gemma(self, image_bytes: bytes) -> DetectionResult:
        base64_image = base64.b64encode(image_bytes).decode("utf-8")
        mime_type = detect_image_mime_type(image_bytes)

        if not settings.GEMMA_API_KEY:
            raise ValueError("Gemma API key not configured")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMMA_MODEL}:generateContent?key={settings.GEMMA_API_KEY}"

        headers = {
            "Content-Type": "application/json",
        }

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": base64_image,
                            }
                        },
                        {
                            "text": VISION_PROMPT,
                        },
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 4096,
                "responseMimeType": "application/json",
            },
        }

        try:
            response = await self._client.post(url, headers=headers, json=payload)
            response.raise_for_status()
        except httpx.TimeoutException:
            logger.error("Gemma Vision API timeout")
            raise ValueError("Analysis timed out. Please try again.")
        except httpx.HTTPStatusError as exc:
            logger.error(
                f"Gemma Vision API error: {exc.response.status_code} - {exc.response.text}"
            )
            raise ValueError(f"Analysis service error: {exc.response.status_code}")

        data = response.json()

        # Better error handling for Gemini API response
        if "candidates" not in data or not data["candidates"]:
            logger.error(f"Gemini API returned no candidates: {data}")
            raise ValueError("Analysis failed: No results from vision API")

        candidate = data["candidates"][0]
        if "content" not in candidate or "parts" not in candidate["content"]:
            logger.error(f"Unexpected Gemini response structure: {data}")
            raise ValueError("Analysis failed: Invalid response format")

        content = candidate["content"]["parts"][0]["text"]
        return self._parse_response(content)

    async def _analyze_with_qwen(self, image_bytes: bytes) -> DetectionResult:
        base64_image = base64.b64encode(image_bytes).decode("utf-8")
        mime_type = detect_image_mime_type(image_bytes)

        if not settings.QWEN_API_KEY:
            raise ValueError("Qwen API key not configured")

        headers = {
            "Authorization": f"Bearer {settings.QWEN_API_KEY}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": settings.QWEN_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": VISION_PROMPT,
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}",
                            },
                        },
                    ],
                }
            ],
            "max_tokens": 4096,
            "temperature": 0.1,
        }

        api_url = settings.QWEN_API_URL.rstrip("/") + "/chat/completions"

        try:
            response = await self._client.post(api_url, headers=headers, json=payload)
            response.raise_for_status()
        except httpx.TimeoutException:
            logger.error("Qwen API timeout")
            raise ValueError("Analysis timed out. Please try again.")
        except httpx.HTTPStatusError as exc:
            logger.error(
                f"Qwen API error: {exc.response.status_code} - {exc.response.text}"
            )
            raise ValueError(f"Analysis service error: {exc.response.status_code}")

        data = response.json()

        if "choices" not in data or not data["choices"]:
            logger.error(f"Qwen API returned no choices: {data}")
            raise ValueError("Analysis failed: No results from vision API")

        content = data["choices"][0]["message"]["content"]
        return self._parse_response(content)

    def _parse_response(self, content: str) -> DetectionResult:
        json_str = self._extract_json(content)

        if not json_str:
            logger.error(
                f"Failed to extract JSON from Vision API response: {content[:500]}"
            )
            raise VisionParseError("Could not parse analysis result. Please try again.")

        json_str = self._try_fix_json(json_str) or json_str

        try:
            parsed = json.loads(json_str)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse Vision API JSON: {json_str[:500]}")
            raise VisionParseError("Could not parse analysis result. Please try again.")

        return DetectionResult(
            species=str(parsed.get("species", "Unknown insect")).strip()
            or "Unknown insect",
            scientific_name=str(parsed.get("scientific_name", "Unknown")).strip()
            or "Unknown",
            confidence=float(parsed.get("confidence", 0.0) or 0.0),
            risk_level=str(parsed.get("risk_level", "medium")).strip().lower()
            or "medium",
            description=str(
                parsed.get("description", "No description available.")
            ).strip()
            or "No description available.",
            recommendation=str(
                parsed.get("recommendation", "No recommendation available.")
            ).strip()
            or "No recommendation available.",
        )

    def _extract_json(self, content: str) -> str | None:
        if not content:
            return None

        text = content.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        text = text.strip()

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return match.group(0)

        # No closing brace found — likely a truncated response. Return the raw
        # text so _try_fix_json (or the caller's retry) can attempt recovery.
        if text.startswith("{"):
            return text

        return None

    def _try_fix_json(self, json_str: str) -> str | None:
        if not json_str:
            return None
        try:
            json.loads(json_str)
            return json_str
        except json.JSONDecodeError:
            pass
        fixed = json_str.replace("\n", " ").replace("\r", " ")
        fixed = re.sub(r"\s{2,}", " ", fixed)
        try:
            json.loads(fixed)
            return fixed
        except json.JSONDecodeError:
            pass
        # Last-ditch: the model may have been truncated before the closing brace.
        # Try appending one and see if the result is valid JSON.
        try:
            json.loads(fixed + "}")
            return fixed + "}"
        except json.JSONDecodeError:
            pass
        return None
