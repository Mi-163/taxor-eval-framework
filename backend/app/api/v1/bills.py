import asyncio
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Bill, ExtractionRun, FieldEvaluation
from app.services.llm.factory import get_llm_adapter
from app.services.evaluation.evaluator import EvaluationEngine
import shutil
import os
import time
import json

router = APIRouter()
eval_engine = EvaluationEngine()

# Ensure dataset directory exists
UPLOAD_DIR = "../dataset"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/evaluate/{model_name}")
async def evaluate_bill(
    model_name: str,
    ground_truth_json: str,  # Passed as stringified JSON for the prototype
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # 1. Save File Locally
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 2. Save Bill Record to DB
    new_bill = Bill(filename=file.filename,
                    ground_truth_json=ground_truth_json)
    db.add(new_bill)
    db.commit()
    db.refresh(new_bill)

    # 3. Instantiate Model
    try:
        adapter = get_llm_adapter(model_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 4. Execute LLM Extraction (with timing)
    start_time = time.time()
    try:
        prediction, in_tokens, out_tokens = await adapter.extract_bill_data(file_path)
        is_success = True
    except Exception as e:
        prediction, in_tokens, out_tokens = {}, 0, 0
        is_success = False
        print(f"LLM Error: {e}")
    latency = time.time() - start_time

    # Calculate approximate cost (e.g., GPT-4o pricing)
    cost = (in_tokens / 1000000 * 5.00) + (out_tokens / 1000000 * 15.00)

    # 5. Save Run Metrics
    run = ExtractionRun(
        bill_id=new_bill.id,
        model_name=model_name,
        raw_response_json=json.dumps(prediction),
        latency_seconds=latency,
        input_tokens=in_tokens,
        output_tokens=out_tokens,
        total_cost_usd=cost,
        is_successful=is_success
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    # 6. Run Evaluation Engine
    truth_dict = json.loads(ground_truth_json)
    eval_results = eval_engine.evaluate_prediction(truth_dict, prediction)

    # 7. Save Field Evaluations to DB
    for field_eval in eval_results["field_evaluations"]:
        fe_record = FieldEvaluation(
            run_id=run.id,
            field_name=field_eval["field_name"],
            actual_value=field_eval["actual_value"],
            predicted_value=field_eval["predicted_value"],
            is_correct=field_eval["is_correct"],
            similarity_score=field_eval["similarity_score"]
        )
        db.add(fe_record)
    db.commit()

    return {
        "status": "success",
        "bill_id": new_bill.id,
        "run_id": run.id,
        "metrics": {
            "latency": latency,
            "cost_usd": cost,
            "accuracy": eval_results["overall_accuracy"]
        },
        "details": eval_results["field_evaluations"]
    }


@router.post("/live-test")
async def live_test_bill(file: UploadFile = File(...)):
    """Runs a single uploaded bill against all 3 models concurrently for side-by-side comparison."""
    file_path = os.path.join(UPLOAD_DIR, f"live_{file.filename}")

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    models = ["openai", "claude", "gemini"]
    results = {}

    async def fetch_model_data(model_name: str):
        try:
            adapter = get_llm_adapter(model_name)
            prediction, _, _ = await adapter.extract_bill_data(file_path)
            return model_name, prediction
        except Exception as e:
            return model_name, {"error": str(e)}

    # Run all 3 models concurrently
    tasks = [fetch_model_data(model) for model in models]
    completed_tasks = await asyncio.gather(*tasks)

    for model_name, data in completed_tasks:
        results[model_name] = data

    return {
        "status": "success",
        "filename": file.filename,
        "extracted_data": results
    }
