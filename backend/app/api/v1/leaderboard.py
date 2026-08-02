from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import ExtractionRun
from app.services.zoho_service import ZohoBooksService
import json

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


@router.post("/zoho/create-expense/{run_id}")
async def push_to_zoho(run_id: str, db: Session = Depends(get_db)):
    """Takes a specific successful run and pushes its extracted JSON to Zoho Books."""
    run = db.query(ExtractionRun).filter(ExtractionRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")

    extracted_data = json.loads(run.raw_response_json)

    try:
        response = await zoho_service.create_expense(extracted_data)
        return {"status": "success", "zoho_api_response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
