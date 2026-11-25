"""Layer 1/FastAPI Server & Orchestration Endpoints for PS 158."""

from __future__ import annotations

import io
import os
import uuid
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from generate_sample_data import generate_synthetic_dataset
from llm_engine import GeminiCognitiveEngine, PrivacyGuardrailViolation
from pdf_generator import generate_executive_pdf
from privacy_analytics import PIIShield, WorkloadAnalyticsEngine

load_dotenv()

app = FastAPI(
    title="PS 158: Public Service Workload Narrative Assistant",
    version="1.0.0",
    description="4-Layer Privacy-First Municipal Workload Analytics & GenAI Briefing Engine",
)

allowed_origins = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pii_shield = PIIShield()
analytics_engine = WorkloadAnalyticsEngine()
cognitive_engine = GeminiCognitiveEngine()

# In-memory store holding ONLY Layer 2 PII-free sanitized DataFrames keyed by session_id.
# Raw citizen PII is discarded immediately inside Layer 2 and never cached.
SANITIZED_DATASETS: dict[str, dict[str, Any]] = {}
MAX_SESSIONS = 12


class SampleLoadRequest(BaseModel):
    num_rows: int = Field(default=640, ge=500, le=5000)
    include_simulated_pii: bool = True
    granularity: str = Field(default="week", pattern="^(week|month)$")


class FilterRequest(BaseModel):
    session_id: str
    granularity: str = Field(default="week", pattern="^(week|month)$")
    service_category: str | None = None
    status: str | None = None
    priority: str | None = None


class NarrativeRequest(BaseModel):
    session_id: str
    granularity: str = Field(default="week", pattern="^(week|month)$")
    service_category: str | None = None
    status: str | None = None
    priority: str | None = None
    focus_area: str = ""
    api_key: str | None = None
    model: str | None = None


class PdfExportRequest(BaseModel):
    session_id: str
    granularity: str = Field(default="week", pattern="^(week|month)$")
    service_category: str | None = None
    status: str | None = None
    priority: str | None = None
    narrative_result: dict[str, Any]


def _store_sanitized_session(safe_df: pd.DataFrame, pii_audit_dict: dict[str, Any], source_label: str) -> str:
    if len(SANITIZED_DATASETS) >= MAX_SESSIONS:
        oldest_key = next(iter(SANITIZED_DATASETS))
        SANITIZED_DATASETS.pop(oldest_key, None)
    session_id = str(uuid.uuid4())[:12]
    SANITIZED_DATASETS[session_id] = {
        "safe_df": safe_df,
        "pii_audit": pii_audit_dict,
        "source_label": source_label,
    }
    return session_id


def _get_session_or_404(session_id: str) -> dict[str, Any]:
    session = SANITIZED_DATASETS.get(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail="Dataset session not found or expired. Please load sample data or upload a CSV/JSON file.",
        )
    return session


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "ps158-workload-assistant",
        "gemini_configured": cognitive_engine.is_gemini_configured(),
        "default_model": cognitive_engine.default_model,
        "active_sessions": len(SANITIZED_DATASETS),
    }


@app.post("/api/analyze/sample")
def analyze_sample(req: SampleLoadRequest) -> dict[str, Any]:
    raw_df = generate_synthetic_dataset(
        num_rows=req.num_rows,
        include_simulated_pii=req.include_simulated_pii,
    )
    safe_df, receipt = pii_shield.sanitize(raw_df)
    pii_audit_dict = receipt.to_dict()
    session_id = _store_sanitized_session(
        safe_df,
        pii_audit_dict,
        source_label=f"Synthetic Municipal Dataset ({req.num_rows} rows)",
    )
    analytics = analytics_engine.analyze(safe_df, granularity=req.granularity)
    return {
        "session_id": session_id,
        "source_label": f"Synthetic Municipal Dataset ({req.num_rows} rows)",
        "pii_audit": pii_audit_dict,
        "analytics": analytics,
        "gemini_configured": cognitive_engine.is_gemini_configured(),
    }


@app.post("/api/analyze/upload")
async def analyze_upload(
    file: UploadFile = File(...),
    granularity: str = Form("week"),
) -> dict[str, Any]:
    filename = (file.filename or "upload.csv").lower()
    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        if filename.endswith(".json"):
            raw_df = pd.read_json(io.BytesIO(raw_bytes))
        elif filename.endswith(".csv"):
            raw_df = pd.read_csv(io.BytesIO(raw_bytes))
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format. Please upload a .csv or .json file.")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to parse uploaded file: {exc}") from exc

    try:
        safe_df, receipt = pii_shield.sanitize(raw_df)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    pii_audit_dict = receipt.to_dict()
    session_id = _store_sanitized_session(
        safe_df,
        pii_audit_dict,
        source_label=file.filename or "Uploaded Municipal Log",
    )
    analytics = analytics_engine.analyze(safe_df, granularity=granularity)
    return {
        "session_id": session_id,
        "source_label": file.filename or "Uploaded Municipal Log",
        "pii_audit": pii_audit_dict,
        "analytics": analytics,
        "gemini_configured": cognitive_engine.is_gemini_configured(),
    }


@app.post("/api/filter")
def filter_dataset(req: FilterRequest) -> dict[str, Any]:
    session = _get_session_or_404(req.session_id)
    analytics = analytics_engine.analyze(
        session["safe_df"],
        granularity=req.granularity,
        category_filter=req.service_category,
        status_filter=req.status,
        priority_filter=req.priority,
    )
    return {
        "session_id": req.session_id,
        "source_label": session["source_label"],
        "pii_audit": session["pii_audit"],
        "analytics": analytics,
    }


@app.post("/api/narrative")
def generate_narrative(req: NarrativeRequest) -> dict[str, Any]:
    session = _get_session_or_404(req.session_id)
    analytics = analytics_engine.analyze(
        session["safe_df"],
        granularity=req.granularity,
        category_filter=req.service_category,
        status_filter=req.status,
        priority_filter=req.priority,
    )
    if analytics.get("empty"):
        raise HTTPException(status_code=400, detail="Selected filters match zero records; relax filters to generate a briefing.")

    try:
        result = cognitive_engine.generate_report(
            analytics=analytics,
            focus_area=req.focus_area,
            api_key_override=req.api_key,
            model_override=req.model,
        )
    except PrivacyGuardrailViolation as exc:
        raise HTTPException(status_code=422, detail=f"Privacy guardrail blocked Layer 4 execution: {exc}") from exc

    return {
        "session_id": req.session_id,
        "pii_audit": session["pii_audit"],
        "narrative_result": result,
    }


@app.post("/api/export/pdf")
def export_pdf(req: PdfExportRequest) -> Response:
    session = _get_session_or_404(req.session_id)
    analytics = analytics_engine.analyze(
        session["safe_df"],
        granularity=req.granularity,
        category_filter=req.service_category,
        status_filter=req.status,
        priority_filter=req.priority,
    )
    pdf_bytes = generate_executive_pdf(
        analytics=analytics,
        narrative_result=req.narrative_result,
        pii_audit=session["pii_audit"],
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="ps158_executive_workload_report.pdf"'},
    )


@app.get("/api/sample-data/csv")
def download_sample_csv(rows: int = 640, include_pii: bool = True) -> Response:
    bounded_rows = min(max(rows, 500), 2000)
    raw_df = generate_synthetic_dataset(num_rows=bounded_rows, include_simulated_pii=include_pii)
    csv_bytes = raw_df.to_csv(index=False).encode("utf-8")
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="ps158_sample_{bounded_rows}_rows.csv"'},
    )


# Serve built React frontend if dist exists (single-server production convenience)
_FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _FRONTEND_DIST.is_dir():
    assets_dir = _FRONTEND_DIST / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str) -> FileResponse:
        if full_path.startswith("api/") or full_path == "api":
            raise HTTPException(status_code=404, detail="API endpoint not found.")
        candidate = _FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(str(candidate))
        return FileResponse(str(_FRONTEND_DIST / "index.html"))
