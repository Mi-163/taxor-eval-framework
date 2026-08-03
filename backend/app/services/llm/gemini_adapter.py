import os
import httpx
import json
import logging
from typing import Tuple, Dict, Any
from app.services.llm.base import BaseModelAdapter

logger = logging.getLogger(__name__)


class GeminiModel(BaseModelAdapter):

    async def extract_bill_data(self, image_path: str) -> Tuple[Dict[str, Any], int, int]:
        filename = os.path.basename(image_path)

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
            # Fail loudly and raise the exception so bad/empty data is never saved to the DB
            logger.error(f"Live Gemini API failed for {filename}: {str(e)}")
            raise e
