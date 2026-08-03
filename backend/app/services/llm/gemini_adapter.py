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

    async def extract_bill_data(self, image_path: str, use_mock: bool = False) -> Tuple[Dict[str, Any], int, int]:
        filename = os.path.basename(image_path)

        # ---------------------------------------------------------
        # 1. MODE 1 BYPASS: Do not call the live API at all
        # ---------------------------------------------------------
        if use_mock:
            logger.info(
                f"[Mode 1 - Benchmark] Bypassing live API. Loading mock JSON directly for {filename}")
            return await self._fetch_mock_data(filename)

        # ---------------------------------------------------------
        # 2. MODE 2 LIVE CALL: Attempt to hit Google Servers
        # ---------------------------------------------------------
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
            # Attempt Live API Call
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
            error_str = str(e)

            # Catch 429 Rate Limit errors and switch to smart fallback
            if "429" in error_str or "Too Many Requests" in error_str:
                logger.warning(
                    f"[Smart Fallback] Hit 429 rate limit for {filename}. Gracefully falling back to mock data.")
                return await self._fetch_mock_data(filename)

            # For any other errors, fail loudly and raise the exception
            logger.error(f"Live Gemini API failed for {filename}: {error_str}")
            raise e

    async def _fetch_mock_data(self, filename: str) -> Tuple[Dict[str, Any], int, int]:
        """Helper method to handle graceful fallback to local mock results and tag it."""
        mock_path = os.path.join(os.path.dirname(
            __file__), "../../../mock_results/gemini_results.json")

        if not os.path.exists(mock_path):
            prediction = {
                "vendor_name": "Sample Vendor (Fallback)",
                "date": "2026-03-30",
                "total_amount": 1500.00,
                "tax_amount": 75.00,
                "currency": "INR"
            }
        else:
            try:
                with open(mock_path, "r") as f:
                    all_mocks = json.load(f)
                    prediction = all_mocks.get(
                        filename, next(iter(all_mocks.values()), {}))
            except Exception:
                prediction = {
                    "vendor_name": "Sample Vendor",
                    "total_amount": 1000.00
                }

        # Inject flag so the UI clearly displays that mock data is active
        if isinstance(prediction, dict):
            prediction["fallback_status"] = "this is a mock data"

        await asyncio.sleep(1.0)
        return prediction, random.randint(800, 1200), random.randint(100, 200)
