import httpx
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class ZohoBooksService:
    def __init__(self):
        # Zoho Books v3 API Endpoint for Expenses
        self.base_url = "https://www.zohoapis.com/books/v3/expenses"
        self.org_id = settings.ZOHO_ORG_ID
        self.token = settings.ZOHO_ACCESS_TOKEN

    async def create_expense(self, extracted_data: dict) -> dict:
        """Pushes only the extracted bill data to Zoho Books."""
        if not self.org_id or not self.token:
            raise ValueError("Zoho credentials are not configured.")

        headers = {
            "Authorization": f"Zoho-oauthtoken {self.token}",
            "Content-Type": "application/json"
        }

        # Map our LLM output to Zoho's required fields
        # Note: In a real Zoho setup, you also need an 'account_id' (Expense Category).
        # We omit strict IDs here for the screening prototype, focusing on the data push.
        payload = {
            "amount": extracted_data.get("amount", 0.0),
            "date": extracted_data.get("date", ""),
            "description": f"Vendor: {extracted_data.get('vendor', 'Unknown')}",
            "reference_number": extracted_data.get("invoice_number", ""),
            "currency_code": extracted_data.get("currency", "INR")
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{self.base_url}?organization_id={self.org_id}",
                headers=headers,
                json=payload
            )

            # For debugging during the interview, we return the raw response
            return {
                "status_code": response.status_code,
                "zoho_response": response.json()
            }
