from rapidfuzz import fuzz
from dateutil import parser
import re
import logging

logger = logging.getLogger(__name__)


def clean_string(val: str) -> str:
    """Removes extra spaces and normalizes case."""
    if not val:
        return ""
    return str(val).strip().lower()


def compare_vendor(actual: str, predicted: str, threshold: float = 85.0) -> dict:
    """Uses fuzzy matching for handwritten vendor names (handles OCR typos)."""
    if not actual and not predicted:
        return {"is_correct": True, "score": 100.0}
    if not actual or not predicted:
        return {"is_correct": False, "score": 0.0}

    score = fuzz.ratio(clean_string(actual), clean_string(predicted))
    return {"is_correct": score >= threshold, "score": score}


def compare_date(actual: str, predicted: str) -> dict:
    """Normalizes dates before comparison (e.g., 12-Oct-2023 vs 12/10/2023)."""
    if not actual and not predicted:
        return {"is_correct": True, "score": 100.0}
    if not actual or not predicted:
        return {"is_correct": False, "score": 0.0}

    try:
        # fuzzy=True allows the parser to ignore surrounding noise text
        date_actual = parser.parse(actual, fuzzy=True).date()
        date_pred = parser.parse(predicted, fuzzy=True).date()
        is_match = (date_actual == date_pred)
        return {"is_correct": is_match, "score": 100.0 if is_match else 0.0}
    except ValueError:
        # Fallback to exact match if date parsing fails
        is_match = clean_string(actual) == clean_string(predicted)
        return {"is_correct": is_match, "score": 100.0 if is_match else 0.0}


def compare_numeric(actual, predicted) -> dict:
    """Numeric comparison for amounts and GST, handling currency symbols."""
    if actual is None and predicted is None:
        return {"is_correct": True, "score": 100.0}
    if actual is None or predicted is None:
        return {"is_correct": False, "score": 0.0}

    try:
        def extract_float(val):
            # Remove commas first (e.g., "1,500.50" -> "1500.50")
            clean_str = str(val).replace(',', '')
            # Extract the actual number sequence ignoring text like "Rs."
            match = re.search(r'\d+(\.\d+)?', clean_str)
            if match:
                return float(match.group())
            raise ValueError("No number found")

        val_actual = extract_float(actual)
        val_pred = extract_float(predicted)

        # Use a small tolerance for floating point comparison
        is_match = abs(val_actual - val_pred) < 0.01
        return {"is_correct": is_match, "score": 100.0 if is_match else 0.0}
    except ValueError:
        return {"is_correct": False, "score": 0.0}


def compare_exact_string(actual: str, predicted: str) -> dict:
    """Case-insensitive exact match for Invoice Numbers and Currency."""
    if not actual and not predicted:
        return {"is_correct": True, "score": 100.0}
    if not actual or not predicted:
        return {"is_correct": False, "score": 0.0}

    is_match = clean_string(actual) == clean_string(predicted)
    return {"is_correct": is_match, "score": 100.0 if is_match else 0.0}
