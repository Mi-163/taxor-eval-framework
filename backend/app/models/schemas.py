from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

# --- LLM Extraction Contract ---


class BillExtraction(BaseModel):
    vendor: Optional[str] = Field(
        None, description="Name of the shop, vendor, or merchant.")
    invoice_number: Optional[str] = Field(
        None, description="Bill, invoice, or receipt number if present.")
    date: Optional[str] = Field(
        None, description="Date of the bill, formatted as YYYY-MM-DD if possible.")
    amount: Optional[float] = Field(
        None, description="Total amount of the bill as a numeric value.")
    currency: Optional[str] = Field(
        "INR", description="Currency of the bill, default to INR.")
    gst: Optional[float] = Field(
        None, description="Any tax, SGST, CGST, or IGST amount visible.")

# --- API Response Schemas ---


class BillResponse(BaseModel):
    id: str
    filename: str

    model_config = ConfigDict(from_attributes=True)
