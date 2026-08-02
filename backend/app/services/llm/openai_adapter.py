import os
import json
import asyncio
import random


class OpenAIModel:
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def extract_bill_data(self, image_path: str):
        filename = os.path.basename(image_path)
        mock_path = os.path.join("../mock_results", "openai_results.json")

        with open(mock_path, "r") as f:
            prediction = json.load(f).get(filename, {})

        # Simulate network latency and typical ChatGPT token usage
        await asyncio.sleep(random.uniform(1.5, 3.0))
        return prediction, random.randint(1000, 1500), random.randint(150, 250)
