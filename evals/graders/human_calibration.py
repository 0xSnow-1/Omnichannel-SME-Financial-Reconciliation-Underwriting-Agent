from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field


class HumanCalibrationRecord(BaseModel):
    sample_id: str
    reviewer_id: str
    overall_rating: int = Field(ge=1, le=5, description="1=Poor, 5=Excellent")
    factual_correctness: bool
    notes: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)


CALIBRATION_DIR = Path("evals/reports/calibrations")


def save_human_calibration(record: HumanCalibrationRecord) -> Path:
    CALIBRATION_DIR.mkdir(parents=True, exist_ok=True)
    out_file = CALIBRATION_DIR / f"{record.sample_id}_{record.reviewer_id}.json"
    out_file.write_text(record.model_dump_json(indent=2), encoding="utf-8")
    return out_file


def load_human_calibrations() -> list[HumanCalibrationRecord]:
    if not CALIBRATION_DIR.exists():
        return []
    records = []
    for f in CALIBRATION_DIR.glob("*.json"):
        try:
            records.append(
                HumanCalibrationRecord.model_validate_json(f.read_text(encoding="utf-8"))
            )
        except Exception:
            pass
    return records
