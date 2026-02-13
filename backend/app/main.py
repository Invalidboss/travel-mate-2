from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from openpyxl import Workbook

app = FastAPI(title="Travel Mate API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_ROOT = Path("uploads")
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)


class TripCreate(BaseModel):
    start: datetime
    end: datetime
    project: str
    trip_type: Literal["domestic", "international"]


trips: dict[str, dict] = {}


@app.post("/trips")
def create_trip(payload: TripCreate):
    trip_id = str(uuid4())
    trip = {
        "id": trip_id,
        "start": payload.start,
        "end": payload.end,
        "project": payload.project,
        "trip_type": payload.trip_type,
        "receipts": [],
        "created_at": datetime.utcnow(),
    }
    trips[trip_id] = trip
    return trip


@app.post("/trips/{trip_id}/receipts")
async def upload_receipts(trip_id: str, files: list[UploadFile] = File(...)):
    trip = trips.get(trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    trip_dir = UPLOAD_ROOT / trip_id
    trip_dir.mkdir(parents=True, exist_ok=True)

    uploaded = []
    for file in files:
        filename = f"{uuid4()}-{file.filename}"
        destination = trip_dir / filename
        content = await file.read()
        destination.write_bytes(content)

        receipt_info = {
            "name": file.filename,
            "path": str(destination),
            "content_type": file.content_type,
            "size": len(content),
        }
        trip["receipts"].append(receipt_info)
        uploaded.append(receipt_info)

    return {"trip_id": trip_id, "uploaded": uploaded}


@app.get("/trips/{trip_id}/summary")
def trip_summary(trip_id: str):
    trip = trips.get(trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    duration_hours = max((trip["end"] - trip["start"]).total_seconds() / 3600, 0)
    estimated_daily = 120 if trip["trip_type"] == "domestic" else 220
    estimated_total = round((duration_hours / 24) * estimated_daily, 2)

    return {
        "trip_id": trip_id,
        "project": trip["project"],
        "trip_type": trip["trip_type"],
        "start": trip["start"],
        "end": trip["end"],
        "duration_hours": round(duration_hours, 2),
        "receipt_count": len(trip["receipts"]),
        "estimated_total": estimated_total,
    }


@app.get("/trips/{trip_id}/export.xlsx")
def export_trip(trip_id: str):
    trip = trips.get(trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    summary = trip_summary(trip_id)
    workbook = Workbook()
    ws = workbook.active
    ws.title = "Expense Summary"

    rows = [
        ("Trip ID", summary["trip_id"]),
        ("Project", summary["project"]),
        ("Type", summary["trip_type"]),
        ("Start", summary["start"].isoformat()),
        ("End", summary["end"].isoformat()),
        ("Duration (hours)", summary["duration_hours"]),
        ("Receipt count", summary["receipt_count"]),
        ("Estimated total", summary["estimated_total"]),
    ]

    for label, value in rows:
        ws.append([label, value])

    ws.append([])
    ws.append(["Receipts"])
    ws.append(["Original Filename", "MIME Type", "Bytes"])
    for receipt in trip["receipts"]:
        ws.append([receipt["name"], receipt["content_type"], receipt["size"]])

    export_dir = Path("exports")
    export_dir.mkdir(parents=True, exist_ok=True)
    export_path = export_dir / f"trip-{trip_id}.xlsx"
    workbook.save(export_path)

    return FileResponse(
        export_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"trip-{trip_id}.xlsx",
    )


@app.get("/health")
def health():
    return {"status": "ok"}
