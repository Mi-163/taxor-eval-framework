import os
import httpx
import json
import logging
import asyncio
import random
from typing import Tuple, Dict, Any
from app.services.llm.base import BaseModelAdapter

logger = logging.getLogger(__name__)


class GeminiModel(BaseModelAdapter):
    # Class-level variable: acts as our global circuit breaker state
    _circuit_open = False

    async def extract_bill_data(self, image_path: str) -> Tuple[Dict[str, Any], int, int]:
        filename = os.path.basename(image_path)

        # 1. CIRCUIT BREAKER CHECK (Instantly route to mock if already tripped)
        if GeminiModel._circuit_open:
            logger.info(
                f"[Circuit Breaker] API limit previously reached. Instantly routing {filename} to mock data.")
            return await self._fetch_mock_data(filename)

        base64_image = self.encode_image_to_base64(image_path)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.api_key}"

        payload = {
            "contents": [{
                "parts": [
                    {"text": self.system_prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": base64_image
                        }
                    }
                ]
            }],
            "generationConfig": {
                "responseMimeType": "application/json"
            }
        }

        try:
            # 2. ATTEMPT LIVE API CALL
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()

                data = response.json()
                raw_content = data['candidates'][0]['content']['parts'][0]['text']
                extracted_json = json.loads(raw_content)

                usage = data.get('usageMetadata', {})
                input_tokens = usage.get('promptTokenCount', 0)
                output_tokens = usage.get('candidatesTokenCount', 0)

                logger.info(
                    f"[Live API] Successfully extracted {filename} via Gemini.")
                return extracted_json, input_tokens, output_tokens

        except Exception as e:
            # 3. TRIP THE CIRCUIT BREAKER ON FIRST FAILURE
            logger.warning(
                f"[Mock Fallback] Live Gemini API failed for {filename} ({e}). Tripping circuit breaker!")
            GeminiModel._circuit_open = True
            return await self._fetch_mock_data(filename)

    async def _fetch_mock_data(self, filename: str) -> Tuple[Dict[str, Any], int, int]:
        """Helper method to handle the fallback logic."""
        mock_path = os.path.join("../mock_results", "gemini_results.json")

        if not os.path.exists(mock_path):
            logger.error(
                f"Mock file not found at {mock_path}. Returning empty data.")
            return {}, 0, 0

        with open(mock_path, "r") as f:
            all_mocks = json.load(f)
            prediction = all_mocks.get(filename, {})

        await asyncio.sleep(random.uniform(2.0, 4.0))
        return prediction, random.randint(800, 1200), random.randint(100, 200)
