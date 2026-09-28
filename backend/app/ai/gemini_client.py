import httpx
import json
import logging
import os
import asyncio
import hashlib
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# In-memory prompt response cache — eliminates duplicate Gemini calls for
# identical prompts (e.g., same category cost profile asked multiple times).
# Keyed on SHA256 of prompt string. Max 256 entries, no TTL (process lifetime).
_prompt_cache: Dict[str, Any] = {}
_PROMPT_CACHE_MAX_SIZE = 256

def _cache_key(prompt: str) -> str:
    return hashlib.sha256(prompt.encode()).hexdigest()[:16]

class GeminiClient:
    """
    Client for interacting with Google's Gemini API via HTTP.
    Used for generating dynamic market intelligence fallbacks and insights.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            logger.warning("GEMINI_API_KEY is not set. Gemini API calls will fail.")
            
        self.model = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
        self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        logger.info("[GEMINI] Using model: %s", self.model)

    def _build_payload(self, prompt: str, schema: Optional[Dict[str, Any]] = None, mime_type: str = "application/json") -> dict:
        generation_config: Dict[str, Any] = {
            "response_mime_type": mime_type
        }
        if schema:
            generation_config["response_schema"] = schema
        return {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": generation_config
        }

    def _parse_response(self, data: dict, mime_type: str) -> Any:
        content = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        if not content:
            return None
        if mime_type == "application/json":
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return content
        return content

    def generate_json(self, prompt: str, schema: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Synchronous Gemini JSON generation with retry on 503 and prompt-level caching."""
        if not self.api_key:
            return None
        key = _cache_key(prompt)
        if key in _prompt_cache:
            logger.debug("Gemini prompt cache HIT (sync)")
            return _prompt_cache[key]
        for attempt in range(2):
            try:
                with httpx.Client(timeout=7.0) as client:
                    response = client.post(
                        f"{self.base_url}?key={self.api_key}",
                        json=self._build_payload(prompt, schema)
                    )
                    response.raise_for_status()
                    result = self._parse_response(response.json(), mime_type)
                    if result and len(_prompt_cache) < _PROMPT_CACHE_MAX_SIZE:
                        _prompt_cache[key] = result
                    return result
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 503 and attempt < 2:
                    import time
                    time.sleep(0.5)
                    continue
                logger.error(f"Gemini API error: {e}")
                logger.error(f"Response: {e.response.text}")
                return None
            except Exception as e:
                logger.error(f"Gemini API error: {e}")
                return None
        return None

    async def generate_json_async(self, prompt: str, schema: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Async Gemini JSON generation with retry on 503 and prompt-level caching."""
        if not self.api_key:
            return None
        key = _cache_key(prompt)
        if key in _prompt_cache:
            logger.debug("Gemini prompt cache HIT (async)")
            return _prompt_cache[key]
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=7.0) as client:
                    response = await client.post(
                        f"{self.base_url}?key={self.api_key}",
                        json=self._build_payload(prompt, schema)
                    )
                    response.raise_for_status()
                    result = self._parse_response(response.json(), mime_type)
                    if result and len(_prompt_cache) < _PROMPT_CACHE_MAX_SIZE:
                        _prompt_cache[key] = result
                    return result
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 503 and attempt < 2:
                    wait = 0.5
                    logger.warning(f"Gemini 503 (attempt {attempt + 1}/3), retrying in {wait}s...")
                    await asyncio.sleep(wait)
                    continue
                logger.error(f"Gemini API error (async): {e}")
                logger.error(f"Response: {e.response.text}")
                return None
            except Exception as e:
                logger.error(f"Gemini API error (async): {e}")
                return None
        return None
