from app.services.evaluation.comparators import (
    compare_vendor, compare_date, compare_numeric, compare_exact_string
)
from app.models.schemas import BillExtraction


class EvaluationEngine:
    def __init__(self):
        # Map fields to their respective comparison strategies
        self.strategies = {
            "vendor": compare_vendor,
            "invoice_number": compare_exact_string,
            "date": compare_date,
            "amount": compare_numeric,
            "currency": compare_exact_string,
            "gst": compare_numeric
        }

    def evaluate_prediction(self, ground_truth: dict, prediction: dict) -> dict:
        """
        Compares a single model prediction against the ground truth.
        Returns detailed field-level metrics and an overall accuracy score.
        """
        field_evaluations = []
        correct_count = 0
        total_fields = len(self.strategies.keys())

        for field, comparator in self.strategies.items():
            actual = ground_truth.get(field)
            pred = prediction.get(field)

            # Execute the specific comparison strategy
            result = comparator(actual, pred)

            if result["is_correct"]:
                correct_count += 1

            field_evaluations.append({
                "field_name": field,
                "actual_value": str(actual) if actual is not None else None,
                "predicted_value": str(pred) if pred is not None else None,
                "is_correct": result["is_correct"],
                "similarity_score": result["score"]
            })

        overall_accuracy = (correct_count / total_fields) * \
            100.0 if total_fields > 0 else 0.0

        return {
            "overall_accuracy": overall_accuracy,
            "field_evaluations": field_evaluations
        }
