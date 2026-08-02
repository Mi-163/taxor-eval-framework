import os
import json
import asyncio
import random


class ClaudeModel:
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def extract_bill_data(self, image_path: str):
        filename = os.path.basename(image_path)
        mock_path = os.path.join("../mock_results", "claude_results.json")

        with open(mock_path, "r") as f:
            prediction = json.load(f).get(filename, {})

        # Simulate network latency and typical Claude token usage
        await asyncio.sleep(random.uniform(1.0, 2.5))
        return prediction, random.randint(900, 1400), random.randint(140, 230)
