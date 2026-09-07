"""
main.py
FastAPI app exposing the blockchain traceability feature.
Run: uvicorn main:app --reload --port 8001

Then open http://127.0.0.1:8001/docs for an interactive Swagger UI
you can literally click through live during your review tomorrow.
"""

import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional
from app.storage_mongo import TraceabilityStore
from app.blockchain import RoleAccessError
from app.customer_view import render_batch_page
from app.qr_generator import generate_qr_for_batch

app = FastAPI(title="Jasmine Blockchain Traceability API")

# Change the URI if your MongoDB is hosted elsewhere (e.g. Atlas connection string)
store = TraceabilityStore(mongo_uri="mongodb://localhost:27017", db_name="jasmine_db")

class EventIn(BaseModel):
    batch_id: str
    event_type: str
    role: str
    actor_id: str
    actor_name: str          # NEW
    data: Dict[str, Any]


@app.post("/event", summary="Record a new supply-chain event for a batch")
def record_event(payload: EventIn):
    try:
        block = store.append_block(
            batch_id=payload.batch_id,
            event_type=payload.event_type,
            role=payload.role,
            actor_id=payload.actor_id,
            actor_name=payload.actor_name,     # NEW
            off_chain_record=payload.data,
        )
        return {"status": "success", "block": block}
    except RoleAccessError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/batch/{batch_id}/history", summary="Customer-facing read-only traceability view (JSON)")
def get_history(batch_id: str):
    history = store.get_batch_history(batch_id)
    if not history:
        raise HTTPException(status_code=404, detail="Batch not found")
    return {"batch_id": batch_id, "events": history}


@app.get("/batch/{batch_id}/verify", summary="Verify tamper-evidence / integrity of a batch's chain")
def verify_batch(batch_id: str):
    report = store.verify_batch(batch_id)
    if not report["blocks"]:
        raise HTTPException(status_code=404, detail="Batch not found")
    return report


@app.get("/track/{batch_id}", response_class=HTMLResponse,
         summary="CUSTOMER-FACING PAGE — what opens when the QR code is scanned")
def track_batch(batch_id: str):
    """
    This is the page a customer sees after scanning the QR code on
    the jasmine packaging: full farm-to-consumer history (cultivation,
    disease detection, treatment, harvest, distribution, transport,
    sale) plus a tamper-evidence badge. Read-only — no login needed.
    """
    timeline = store.get_full_batch_details(batch_id)
    verification = store.verify_batch(batch_id) if timeline else {"valid": False}
    html = render_batch_page(batch_id, timeline, verification.get("valid", False))
    return HTMLResponse(content=html)


@app.get("/batch/{batch_id}/qrcode", summary="Generate/download the QR code image for a batch")
def get_qr_code(batch_id: str):
    """
    Generates a QR code PNG that encodes the link to this batch's
    /track/{batch_id} page. This is what gets printed on the physical
    jasmine packaging.
    """
    base_url = os.getenv("TRACEABILITY_BASE_URL", "http://127.0.0.1:8001").rstrip("/")
    path = generate_qr_for_batch(batch_id, base_url=base_url,
                                  output_path=f"qr_{batch_id}.png")
    return FileResponse(path, media_type="image/png", filename=f"qr_{batch_id}.png")


@app.get("/", summary="Health check")
def root():
    return {"status": "Jasmine Blockchain Traceability API is running"}