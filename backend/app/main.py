from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from app.db.database import engine, Base

from app.api.v1 import bills, leaderboard, benchmark

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Taxor Eval Framework", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/health")
def health_check():
    return {"status": "ok", "message": "Backend engine is running natively."}


app.include_router(bills.router, prefix="/api/v1/bills", tags=["Bills"])
app.include_router(leaderboard.router, prefix="/api/v1/analytics",
                   tags=["Analytics & Integration"])
app.include_router(
    benchmark.router, prefix="/api/v1/benchmark", tags=["Benchmark"])
