from abc import ABC, abstractmethod
from typing import Tuple, Dict, Any
import base64


class BaseModelAdapter(ABC):
    def __init__(self, api_key: str):
        self.api_key = api_key
        # The universal prompt ensuring consistency across all evaluations
        self.system_prompt = """
        You are an expert AI data extraction assistant specializing in Indian handwritten bills.
        Extract the following fields from the provided image: vendor, invoice_number, date, amount, currency, gst.
        Return ONLY a valid JSON object matching this exact schema. Do not include markdown formatting like ```json.
        """

    def encode_image_to_base64(self, image_path: str) -> str:
        """Helper to convert local images to base64 for REST API payloads."""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    @abstractmethod
    async def extract_bill_data(self, image_path: str) -> Tuple[Dict[str, Any], int, int]:
        """
        Processes the image and returns a tuple containing:
        1. The extracted data as a Python dictionary.
        2. Input tokens used.
        3. Output tokens used.
        """
        pass
