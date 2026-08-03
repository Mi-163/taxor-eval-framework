import os
import json
import re
import httpx
import logging
from datetime import datetime
from app.core.config import settings

logger = logging.getLogger(__name__)


class ZohoBooksService:
    def __init__(self):
        self.base_url = "https://www.zohoapis.in/books/v3/expenses"
        self.org_id = settings.ZOHO_ORG_ID

    def _find_key_recursively(self, data, possible_keys):
        """Recursively search through a nested dictionary or list for specific keys."""

        # If the LLM returned a string with Markdown JSON inside the dictionary, try to parse it
        if isinstance(data, str):
            try:
                clean_str = re.sub(r'^```[jJ]son\s*', '', data)
                clean_str = re.sub(r'\s*```$', '', clean_str)
                data = json.loads(clean_str)
            except Exception:
                pass  # Not valid JSON string, continue search normally

        if isinstance(data, dict):
            # Check the current level first
            for k, v in data.items():
                if str(k).lower().strip() in possible_keys:
                    # Ignore nulls/empty strings, keep searching in case a valid one exists
                    if v is not None and v != "":
                        return v

            # If not found, recurse deeper into nested dictionaries
            for v in data.values():
                res = self._find_key_recursively(v, possible_keys)
                if res is not None and res != "":
                    return res

        elif isinstance(data, list):
            # If it's a list of items, check each item
            for item in data:
                res = self._find_key_recursively(item, possible_keys)
                if res is not None and res != "":
                    return res

        return None

    async def create_expense(self, extracted_data: dict) -> dict:
        current_token = os.environ.get(
            "ZOHO_ACCESS_TOKEN") or settings.ZOHO_ACCESS_TOKEN

        if not self.org_id or not current_token:
            raise ValueError("Zoho credentials are not configured.")

        headers = {
            "Authorization": f"Zoho-oauthtoken {current_token}",
            "Content-Type": "application/json"
        }

        # --- ROBUST RECURSIVE EXTRACTION ---
        # Hunt down the values no matter how deep the LLM nested them
        raw_amount = self._find_key_recursively(extracted_data, [
                                                'amount', 'total', 'total_amount', 'grand_total', 'net_amount', 'sum'])
        raw_date = self._find_key_recursively(extracted_data, [
                                              'date', 'invoice_date', 'receipt_date', 'billing_date', 'transaction_date'])
        raw_vendor = self._find_key_recursively(extracted_data, [
                                                'vendor', 'vendor_name', 'merchant', 'store', 'shop_name', 'merchant_name'])
        raw_ref = self._find_key_recursively(extracted_data, [
                                             'invoice_number', 'receipt_number', 'reference_number', 'bill_no', 'invoice_no', 'ref'])
        raw_currency = self._find_key_recursively(
            extracted_data, ['currency', 'currency_code'])

        # --- AMOUNT PARSING ---
        try:
            cleaned_amount = re.sub(r'[^0-9.]', '', str(raw_amount))
            amount_value = float(cleaned_amount) if cleaned_amount else 0.0
        except Exception:
            amount_value = 0.0

        if amount_value <= 0:
            # If it STILL fails, print exactly what the LLM returned so we can diagnose it immediately
            dump_data = str(extracted_data)[:250]
            return {
                "status_code": 400,
                "zoho_response": {
                    "code": 5015,
                    "message": f"Could not find Amount. Raw LLM Data snippet: {dump_data}"
                }
            }

        # --- DATE PARSING ---
        try:
            # Try YYYY-MM-DD
            valid_date = datetime.strptime(
                str(raw_date)[:10], "%Y-%m-%d").strftime("%Y-%m-%d")
        except Exception:
            try:
                # Try DD-MM-YYYY
                valid_date = datetime.strptime(
                    str(raw_date)[:10], "%d-%m-%Y").strftime("%Y-%m-%d")
            except Exception:
                valid_date = datetime.now().strftime("%Y-%m-%d")

        vendor_name = str(raw_vendor)[:100] if raw_vendor else "Unknown Vendor"
        ref_number = str(raw_ref)[:50] if raw_ref else ""
        currency_code = str(raw_currency)[
            :3].upper() if raw_currency else "INR"

        payload = {
            "account_id": "4044797000000033009",
            "amount": amount_value,
            "date": valid_date,
            "description": f"Vendor: {vendor_name}",
            "reference_number": ref_number,
            "currency_code": currency_code
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{self.base_url}?organization_id={self.org_id}",
                headers=headers,
                json=payload
            )

            return {
                "status_code": response.status_code,
                "zoho_response": response.json()
            }
