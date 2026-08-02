import pytest
from app.services.evaluation.comparators import (
    compare_vendor, compare_date, compare_numeric, compare_exact_string
)
from app.services.evaluation.evaluator import EvaluationEngine


def test_compare_vendor_fuzzy():
    # True positive: OCR missed a double consonant and a letter
    result = compare_vendor("Aggarwal Sweets", "Agarwal Swets")
    assert result["is_correct"] is True
    assert result["score"] > 85.0

    # True negative: Completely different vendors
    result_fail = compare_vendor("Aggarwal Sweets", "Dominos Pizza")
    assert result_fail["is_correct"] is False
    assert result_fail["score"] < 50.0


def test_compare_date_normalization():
    # True positive: LLM extracted a standard date, ground truth is formatted differently
    result = compare_date("12-Oct-2023", "2023-10-12")
    assert result["is_correct"] is True

    # True negative: Different dates entirely
    result_fail = compare_date("12-Oct-2023", "2023-10-15")
    assert result_fail["is_correct"] is False


def test_compare_numeric_currency_symbols():
    # True positive: LLM hallucinated a currency symbol and comma
    result = compare_numeric(1500.50, "₹ 1,500.50")
    assert result["is_correct"] is True

    # True positive: Checking float tolerance
    result_float = compare_numeric(150.0, 150.00)
    assert result_float["is_correct"] is True


def test_evaluation_engine_full_run():
    engine = EvaluationEngine()

    ground_truth = {
        "vendor": "Delhi Stationers",
        "invoice_number": "INV-001",
        "date": "14 Nov 2023",
        "amount": 450.0,
        "currency": "INR",
        "gst": 0.0
    }

    prediction = {
        "vendor": "Delhi Stationer",  # Missing 's', should pass via fuzzy match
        # Case different, should pass via exact_string lowercasing
        "invoice_number": "inv-001",
        "date": "2023-11-14",        # ISO format, should pass via date parsing
        "amount": "Rs. 450.00",      # String with currency, should pass via numeric cleaning
        "currency": "inr",           # Case different, should pass
        "gst": None                  # None vs 0.0, should fail
    }

    results = engine.evaluate_prediction(ground_truth, prediction)

    # 5 out of 6 fields should be correct
    assert round(results["overall_accuracy"], 2) == round((5/6)*100, 2)
    assert len(results["field_evaluations"]) == 6
