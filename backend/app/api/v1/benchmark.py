from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Bill, ExtractionRun, FieldEvaluation
from app.services.llm.factory import get_llm_adapter
from app.services.evaluation.evaluator import EvaluationEngine
import os
import json
import time
import asyncio

router = APIRouter()
eval_engine = EvaluationEngine()

DATASET_DIR = "../dataset"
GT_DIR = "../ground_truth"

# Dynamic pricing per 1,000,000 tokens (USD)
MODEL_PRICING = {
    "openai": {"input_rate": 2.50, "output_rate": 10.00},
    "claude": {"input_rate": 3.00, "output_rate": 15.00},
    "gemini": {"input_rate": 0.10, "output_rate": 0.40},
}


def calculate_cost(model_name: str, in_tokens: int, out_tokens: int) -> float:
    """Calculates extraction cost based on model-specific token pricing."""
    pricing = MODEL_PRICING.get(
        model_name.lower(), {"input_rate": 2.50, "output_rate": 10.00}
    )
    input_cost = (in_tokens / 1000000) * pricing["input_rate"]
    output_cost = (out_tokens / 1000000) * pricing["output_rate"]
    return input_cost + output_cost


async def process_single_bill(
    filename: str, model_name: str, ground_truth_data: dict, db: Session
):
    """Processes a single bill for a specific model during the benchmark run."""
    image_path = os.path.join(DATASET_DIR, filename)

    # Retrieve ground truth object for this specific file key (e.g. "bill1.png")
    ground_truth_dict = ground_truth_data.get(filename)
    if not ground_truth_dict:
        print(f"Skipping {filename}: No entry found in ground_truth.json")
        return

    # Fetch existing Bill record or create a new one
    bill = db.query(Bill).filter(Bill.filename == filename).first()
    if not bill:
        bill = Bill(
            filename=filename, ground_truth_json=json.dumps(ground_truth_dict)
        )
        db.add(bill)
        db.commit()
        db.refresh(bill)

    try:
        adapter = get_llm_adapter(model_name)
        start_time = time.time()
        prediction, in_tokens, out_tokens = await adapter.extract_bill_data(
            image_path
        )
        latency = time.time() - start_time
        is_success = True
    except Exception as e:
        print(f"Failed extracting {filename} with {model_name}: {e}")
        prediction, in_tokens, out_tokens, latency, is_success = (
            {},
            0,
            0,
            0.0,
            False,
        )

    # Calculate exact cost dynamically per model
    cost = calculate_cost(model_name, in_tokens, out_tokens)

    # Save Run record
    run = ExtractionRun(
        bill_id=bill.id,
        model_name=model_name,
        raw_response_json=json.dumps(prediction),
        latency_seconds=latency,
        input_tokens=in_tokens,
        output_tokens=out_tokens,
        total_cost_usd=cost,
        is_successful=is_success,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    # Evaluate extracted fields if successful
    if is_success and prediction:
        eval_results = eval_engine.evaluate_prediction(
            ground_truth_dict, prediction
        )
        for field_eval in eval_results.get("field_evaluations", []):
            fe_record = FieldEvaluation(
                run_id=run.id,
                field_name=field_eval["field_name"],
                actual_value=str(field_eval["actual_value"]),
                predicted_value=str(field_eval["predicted_value"]),
                is_correct=field_eval["is_correct"],
                similarity_score=field_eval["similarity_score"],
            )
            db.add(fe_record)
        db.commit()


@router.post("/run")
async def run_benchmark(db: Session = Depends(get_db)):
    """Triggers the benchmark evaluation run across all images and models."""
    gt_file_path = os.path.join(GT_DIR, "ground_truth.json")
    if not os.path.exists(gt_file_path):
        raise HTTPException(
            status_code=400,
            detail="ground_truth.json not found in ground_truth directory.",
        )

    with open(gt_file_path, "r") as f:
        ground_truth_data = json.load(f)

    if not os.path.exists(DATASET_DIR):
        raise HTTPException(
            status_code=400,
            detail=f"Dataset directory '{DATASET_DIR}' not found.",
        )

    models_to_test = ["openai", "claude", "gemini"]
    processed_count = 0

    image_files = [
        f
        for f in os.listdir(DATASET_DIR)
        if f.lower().endswith((".png", ".jpg", ".jpeg"))
    ]

    for filename in image_files:
        for model in models_to_test:
            await process_single_bill(filename, model, ground_truth_data, db)
            # Sleep to stay well within free tier rate limits
            await asyncio.sleep(4)
        processed_count += 1

    return {
        "status": "success",
        "message": f"Benchmark completed for {processed_count} images across {len(models_to_test)} models.",
    }
