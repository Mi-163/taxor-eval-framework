import asyncio
import json
import re
import os
import httpx
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import ExtractionRun
from app.services.zoho_service import ZohoBooksService

logger = logging.getLogger(__name__)

router = APIRouter()
zoho_service = ZohoBooksService()


@router.get("/metrics")
def get_leaderboard_metrics(db: Session = Depends(get_db)):
    """Aggregates data to compare models on accuracy and extrapolated cost."""
    runs = db.query(ExtractionRun).all()

    results = {}
    for run in runs:
        model = run.model_name
        if model not in results:
            results[model] = {
                "total_runs": 0, "total_latency": 0.0,
                "total_cost": 0.0, "correct_fields": 0, "total_fields": 0
            }

        results[model]["total_runs"] += 1
        results[model]["total_latency"] += run.latency_seconds
        results[model]["total_cost"] += run.total_cost_usd

        for eval_row in run.evaluations:
            results[model]["total_fields"] += 1
            if eval_row.is_correct:
                results[model]["correct_fields"] += 1

    leaderboard = []
    for model, stats in results.items():
        if stats["total_runs"] == 0:
            continue

        avg_acc = (stats["correct_fields"] / stats["total_fields"]
                   * 100) if stats["total_fields"] > 0 else 0
        avg_cost_per_bill = stats["total_cost"] / stats["total_runs"]

        leaderboard.append({
            "model_name": model,
            "average_accuracy_percent": round(avg_acc, 2),
            "average_latency_seconds": round(stats["total_latency"] / stats["total_runs"], 2),
            "cost_per_100_bills_usd": round(avg_cost_per_bill * 100, 4),
            "cost_per_1000_bills_usd": round(avg_cost_per_bill * 1000, 4),
            "total_bills_processed": stats["total_runs"]
        })

    # Sort by highest accuracy first
    leaderboard.sort(key=lambda x: x["average_accuracy_percent"], reverse=True)
    return {"leaderboard": leaderboard}


def get_fresh_zoho_token():
    url = "https://accounts.zoho.in/oauth/v2/token"
    params = {
        "refresh_token": os.getenv("ZOHO_REFRESH_TOKEN"),
        "client_id": os.getenv("ZOHO_CLIENT_ID"),
        "client_secret": os.getenv("ZOHO_CLIENT_SECRET"),
        "grant_type": "refresh_token"
    }

    with httpx.Client() as client:
        response = client.post(url, params=params)

    if response.status_code == 200:
        data = response.json()
        return data.get("access_token")
    else:
        raise Exception(f"Failed to refresh token: {response.text}")


@router.post("/zoho/create-expense/{run_id}")
async def push_to_zoho(run_id: str, db: Session = Depends(get_db)):
    """Takes a specific successful run and pushes its extracted JSON to Zoho Books."""
    run = db.query(ExtractionRun).filter(ExtractionRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")

    try:
        extracted_data = json.loads(run.raw_response_json)
        if isinstance(extracted_data, str):
            extracted_data = json.loads(extracted_data)
    except Exception:
        extracted_data = {}

    try:
        response = await zoho_service.create_expense(extracted_data)

        # Mark as synced if Zoho recorded it
        if response.get("status_code") in [200, 201]:
            run.is_synced = True
            db.commit()

        return {"status": "success", "zoho_api_response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/zoho/sync-all")
async def sync_all_expenses(db: Session = Depends(get_db)):
    """Pushes all unsynced, successful extracted JSON bills from the database to Zoho Books."""

    # Only fetch runs that succeeded and haven't been synced yet
    runs = db.query(ExtractionRun).filter(
        ExtractionRun.is_successful == True,
        ExtractionRun.is_synced == False
    ).all()

    if not runs:
        return {
            "message": "Everything is up to date! No new bills to sync.",
            "data": {"success": 0, "failed": 0, "skipped": 0, "details": []}
        }

    results = {"success": 0, "failed": 0, "skipped": 0, "details": []}

    for run in runs:
        try:
            # --- SAFE JSON UNWRAPPING ---
            extracted_data = {}
            if run.raw_response_json:
                extracted_data = json.loads(run.raw_response_json)

                # If stored as a stringified JSON in DB, unwrap it again
                if isinstance(extracted_data, str):
                    clean_str = re.sub(
                        r'^```[jJ]son\s*', '', extracted_data.strip())
                    clean_str = re.sub(r'\s*```$', '', clean_str.strip())
                    try:
                        extracted_data = json.loads(clean_str)
                    except Exception:
                        extracted_data = {}

            # THE FIX: Silently skip empty JSONs, do NOT count them as failed
            if not extracted_data or extracted_data == {}:
                continue

            # 1st Attempt: Push to Zoho
            response = await zoho_service.create_expense(extracted_data)
            status_code = response.get("status_code")

            # --- AUTO-REFRESH LOGIC FOR 401 ---
            if status_code == 401:
                print(f"Token expired on run {run.id}. Refreshing...")
                new_token = get_fresh_zoho_token()
                os.environ["ZOHO_ACCESS_TOKEN"] = new_token

                # Retry with new token
                response = await zoho_service.create_expense(extracted_data)
                status_code = response.get("status_code")
            # ----------------------------------

            # SMART ERROR HANDLING
            if status_code in [200, 201]:
                results["success"] += 1
                run.is_synced = True  # Flag row in DB
            else:
                err_msg = str(response.get("zoho_response", "")).lower()
                if "already exists" in err_msg or "duplicate" in err_msg or "35002" in err_msg:
                    results["skipped"] += 1  # Not a failure, just a duplicate!
                    run.is_synced = True     # Mark as synced so we don't ask again
                else:
                    results["failed"] += 1
                    results["details"].append(
                        {"run_id": str(run.id), "response": response})

        except Exception as e:
            results["failed"] += 1
            results["details"].append({"run_id": str(run.id), "error": str(e)})

        # Respect Zoho's API rate limits
        await asyncio.sleep(0.5)

    # Save all updated 'is_synced' flags
    db.commit()

    return {
        "message": f"Bulk sync complete. {results['success']} synced, {results['skipped']} skipped (duplicates), {results['failed']} failed.",
        "data": results
    }
