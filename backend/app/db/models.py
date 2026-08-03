from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.db.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class Bill(Base):
    __tablename__ = "bills"

    id = Column(String, primary_key=True, default=generate_uuid)
    filename = Column(String, index=True)
    # We store the truth as a serialized JSON string
    ground_truth_json = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship to evaluation runs
    runs = relationship("ExtractionRun", back_populates="bill",
                        cascade="all, delete-orphan")


class ExtractionRun(Base):
    __tablename__ = "extraction_runs"

    id = Column(String, primary_key=True, default=generate_uuid)
    bill_id = Column(String, ForeignKey("bills.id"))
    model_name = Column(String, index=True)
    raw_response_json = Column(String)
    latency_seconds = Column(Float)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_cost_usd = Column(Float, default=0.0)
    is_successful = Column(Boolean, default=True)
    is_synced = Column(Boolean, default=False)

    bill = relationship("Bill", back_populates="runs")
    evaluations = relationship(
        "FieldEvaluation", back_populates="run", cascade="all, delete-orphan"
    )


class FieldEvaluation(Base):
    __tablename__ = "field_evaluations"

    id = Column(String, primary_key=True, default=generate_uuid)
    run_id = Column(String, ForeignKey("extraction_runs.id"))
    field_name = Column(String, index=True)
    actual_value = Column(String, nullable=True)
    predicted_value = Column(String, nullable=True)
    is_correct = Column(Boolean)
    # Stores the RapidFuzz score for fuzzy matching
    similarity_score = Column(Float)

    run = relationship("ExtractionRun", back_populates="evaluations")
