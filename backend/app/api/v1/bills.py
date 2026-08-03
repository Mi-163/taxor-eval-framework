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
import logging
from app.services.zoho_service import ZohoBooksService

logger = logging.getLogger(__name__)

router = APIRouter()
eval_engine = EvaluationEngine()

# Ensure dataset directory exists
UPLOAD_DIR = "../dataset"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/extract")
async def extract_bill(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Extracts data from a single bill using Gemini, saves the run into the DB, 
    and returns the run_id so it can be pushed to Zoho Books.
    """
    file_path = os.path.join(UPLOAD_DIR, f"live_{file.filename}")

    # 1. Save file locally
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 2. Get Gemini LLM adapter
    try:
        adapter = get_llm_adapter("gemini")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"LLM Adapter Error: {str(e)}")

    # 3. Run extraction
    start_time = time.time()
    try:
        prediction, in_tokens, out_tokens = await adapter.extract_bill_data(file_path)
        is_success = True
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Gemini Extraction Failed: {str(e)}")

    latency = time.time() - start_time
    cost = (in_tokens / 1000000 * 0.15) + (out_tokens / 1000000 * 0.60)

    # 4. Save Bill record to DB
    new_bill = Bill(filename=file.filename, ground_truth_json="{}")
    db.add(new_bill)
    db.commit()
    db.refresh(new_bill)

    # 5. Save ExtractionRun to DB (Generates the run_id needed for Zoho Sync)
    run = ExtractionRun(
        bill_id=new_bill.id,
        model_name="gemini",
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

    # 6. Return exact JSON format expected by React UI
    return {
        "status": "success",
        "run_id": str(run.id),
        "extracted_json": prediction
    }


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

    # Calculate approximate cost
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


@router.post("/sync-all")
async def sync_all_expenses(db: Session = Depends(get_db)):
    """
    Fetches all successful extraction runs from the database, safely decodes 
    the JSON (handling double-escaped strings from pre-computed text files), 
    and pushes them to Zoho Books.
    """
    zoho_service = ZohoBooksService()

    # Only fetch runs that have data
    runs = db.query(ExtractionRun).filter(
        ExtractionRun.is_successful == True).all()

    success_count = 0
    failed_count = 0
    details = []

    for run in runs:
        extracted_data = {}

        # --- THE FIX: SAFE JSON UNWRAPPING ---
        if run.raw_response_json:
            try:
                # 1st unwrap: Convert DB string to Python object
                extracted_data = json.loads(run.raw_response_json)

                # 2nd unwrap: If the static file import double-encoded it, it will still be a string.
                # Decode it one more time to get the actual dictionary.
                if isinstance(extracted_data, str):
                    extracted_data = json.loads(extracted_data)

            except Exception as e:
                logger.error(f"Failed to decode JSON for run {run.id}: {e}")
                extracted_data = {}

        # If data is completely empty after unwrapping, skip hitting the Zoho API
        if not extracted_data:
            failed_count += 1
            details.append({
                "run_id": str(run.id),
                "response": {
                    "status_code": 400,
                    "zoho_response": {"code": 5015, "message": "Failed before Zoho: Data is completely empty or invalid JSON string."}
                }
            })
            continue

        # Send the clean, verified dictionary to Zoho
        zoho_res = await zoho_service.create_expense(extracted_data)

        if zoho_res["status_code"] in [200, 201]:
            success_count += 1
        else:
            failed_count += 1

        details.append({
            "run_id": str(run.id),
            "response": zoho_res
        })

    return {
        "message": f"Bulk sync complete. {success_count} synced, {failed_count} failed.",
        "data": {
            "success": success_count,
            "failed": failed_count,
            "details": details
        }
    }


@router.post("/sync-one/{run_id}")
async def sync_one_expense(run_id: str, db: Session = Depends(get_db)):
    """
    Syncs a single extraction run to Zoho Books using its unique run_id, 
    with duplicate prevention.
    """
    zoho_service = ZohoBooksService()

    # Find the specific run in the database
    run = db.query(ExtractionRun).filter(ExtractionRun.id == run_id).first()
    if not run:
        raise HTTPException(
            status_code=404, detail="Extraction run not found.")

    extracted_data = {}
    if run.raw_response_json:
        try:
            extracted_data = json.loads(run.raw_response_json)
            if isinstance(extracted_data, str):
                extracted_data = json.loads(extracted_data)
        except Exception as e:
            logger.error(f"Failed to decode JSON for run {run.id}: {e}")

    if not extracted_data:
        raise HTTPException(
            status_code=400,
            detail="Data is completely empty or invalid JSON string."
        )

    # Send to Zoho Books
    zoho_res = await zoho_service.create_expense(extracted_data)

    if zoho_res["status_code"] in [200, 201]:
        return {
            "status": "success",
            "message": "Expense successfully created in Zoho Books.",
            "zoho_response": zoho_res["zoho_response"]
        }
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Zoho Error: {zoho_res.get('zoho_response', {})}"
        )
