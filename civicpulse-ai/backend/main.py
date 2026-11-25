"""FastAPI server for CivicPulse AI — Public Complaint Resolution & Delay Analysis System."""

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

from analytics_engine import CivicPulseAnalyticsEngine
from database import CivicPulseDB
from gemini_service import CivicPulseGeminiService, GuardrailViolation
from pdf_report import build_administrative_pdf
from privacy_shield import PrivacyShield
from sample_data_generator import generate_complaint_dataset

load_dotenv()

app = FastAPI(
    title="CivicPulse AI — Public Complaint Resolution & Delay Analysis System",
    version="1.0.0",
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

db = CivicPulseDB()
privacy_shield = PrivacyShield()
analytics_engine = CivicPulseAnalyticsEngine()
gemini_service = CivicPulseGeminiService()

# Session cache holding strictly PII-free DataFrames
SESSIONS: dict[str, dict[str, Any]] = {}
MAX_SESSIONS = 15


class SampleRequest(BaseModel):
    num_rows: int = Field(default=620, ge=100, le=5000)
    include_simulated_pii: bool = False
    granularity: str = Field(default="week", pattern="^(week|month)$")


class FilterRequest(BaseModel):
    session_id: str
    department: str | None = None
    category: str | None = None
    status: str | None = None
    priority: str | None = None
    granularity: str = Field(default="week", pattern="^(week|month)$")


class ReportGenerateRequest(BaseModel):
    session_id: str
    title: str = "CivicPulse Administrative Resolution & Delay Report"
    focus_prompt: str = ""
    department: str | None = None
    category: str | None = None
    status: str | None = None
    priority: str | None = None
    granularity: str = Field(default="week", pattern="^(week|month)$")
    api_key: str | None = None
    model: str | None = None


class AskRequest(BaseModel):
    session_id: str
    question: str
    department: str | None = None
    category: str | None = None
    status: str | None = None
    priority: str | None = None
    granularity: str = Field(default="week", pattern="^(week|month)$")
    api_key: str | None = None
    model: str | None = None


class PdfExportRequest(BaseModel):
    session_id: str | None = None
    report_id: str | None = None
    report_bundle: dict[str, Any] | None = None
    department: str | None = None
    category: str | None = None
    status: str | None = None
    priority: str | None = None
    granularity: str = Field(default="week", pattern="^(week|month)$")


def _store_session(safe_df: pd.DataFrame, receipt: dict[str, Any], source_name: str, file_type: str) -> str:
    if len(SESSIONS) >= MAX_SESSIONS:
        SESSIONS.pop(next(iter(SESSIONS)), None)
    sid = str(uuid.uuid4())[:12]
    SESSIONS[sid] = {
        "safe_df": safe_df,
        "pii_receipt": receipt,
        "source_name": source_name,
        "file_type": file_type,
    }
    db.record_upload_session(
        session_id=sid,
        source_name=source_name,
        file_type=file_type,
        total_rows=len(safe_df),
        dropped_pii_columns=receipt.get("dropped_pii_columns", []),
        inline_pii_scrubbed=receipt.get("total_inline_pii_scrubbed", 0),
    )
    return sid


def _get_session(session_id: str) -> dict[str, Any]:
    s = SESSIONS.get(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Session expired or not found. Load sample data or upload a CSV/Excel file.")
    return s


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "civicpulse-ai",
        "gemini_configured": gemini_service.is_configured(),
        "default_model": gemini_service.default_model,
        "active_sessions": len(SESSIONS),
    }


@app.post("/api/datasets/sample")
def load_sample_dataset(req: SampleRequest) -> dict[str, Any]:
    raw_df = generate_complaint_dataset(
        num_rows=req.num_rows,
        include_simulated_pii=req.include_simulated_pii,
    )
    safe_df, receipt = privacy_shield.sanitize(raw_df)
    receipt_dict = receipt.to_dict()
    source_name = f"Synthetic Municipal Complaints ({req.num_rows} rows)"
    sid = _store_session(safe_df, receipt_dict, source_name, "SYNTHETIC")
    analytics = analytics_engine.analyze(safe_df, granularity=req.granularity)
    db.log_event(
        event_type="ML_ANOMALY_SCAN",
        session_id=sid,
        actor="Isolation Forest",
        summary=f"Flagged {analytics['ml_anomalies']['flagged_delay_ticket_count']} delay anomalies and {len(analytics['ml_anomalies']['volume_anomaly_periods'])} volume spikes.",
    )
    preview_rows = safe_df.head(12).copy()
    for c in ("Date_Received", "Deadline", "Resolution_Date", "Last_Updated_Date"):
        preview_rows[c] = preview_rows[c].dt.strftime("%Y-%m-%d").fillna("")

    return {
        "session_id": sid,
        "source_name": source_name,
        "pii_receipt": receipt_dict,
        "analytics": analytics,
        "preview_rows": preview_rows.to_dict(orient="records"),
        "gemini_configured": gemini_service.is_configured(),
    }


@app.post("/api/datasets/upload")
async def upload_dataset(
    file: UploadFile = File(...),
    granularity: str = Form("week"),
) -> dict[str, Any]:
    filename = file.filename or "complaints.csv"
    low = filename.lower()
    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        if low.endswith(".csv"):
            raw_df = pd.read_csv(io.BytesIO(raw_bytes))
            ftype = "CSV"
        elif low.endswith((".xlsx", ".xls")):
            raw_df = pd.read_excel(io.BytesIO(raw_bytes))
            ftype = "EXCEL"
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format. Please upload .csv, .xlsx, or .xls.")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not parse uploaded file: {exc}") from exc

    try:
        safe_df, receipt = privacy_shield.sanitize(raw_df)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    receipt_dict = receipt.to_dict()
    sid = _store_session(safe_df, receipt_dict, filename, ftype)
    analytics = analytics_engine.analyze(safe_df, granularity=granularity)
    db.log_event(
        event_type="ML_ANOMALY_SCAN",
        session_id=sid,
        actor="Isolation Forest",
        summary=f"Flagged {analytics['ml_anomalies']['flagged_delay_ticket_count']} delay anomalies and {len(analytics['ml_anomalies']['volume_anomaly_periods'])} volume spikes.",
    )
    preview_rows = safe_df.head(12).copy()
    for c in ("Date_Received", "Deadline", "Resolution_Date", "Last_Updated_Date"):
        preview_rows[c] = preview_rows[c].dt.strftime("%Y-%m-%d").fillna("")

    return {
        "session_id": sid,
        "source_name": filename,
        "pii_receipt": receipt_dict,
        "analytics": analytics,
        "preview_rows": preview_rows.to_dict(orient="records"),
        "gemini_configured": gemini_service.is_configured(),
    }


@app.post("/api/analytics/filter")
def filter_analytics(req: FilterRequest) -> dict[str, Any]:
    s = _get_session(req.session_id)
    analytics = analytics_engine.analyze(
        s["safe_df"],
        department_filter=req.department,
        category_filter=req.category,
        status_filter=req.status,
        priority_filter=req.priority,
        granularity=req.granularity,
    )
    return {
        "session_id": req.session_id,
        "source_name": s["source_name"],
        "pii_receipt": s["pii_receipt"],
        "analytics": analytics,
    }


@app.post("/api/reports/generate")
def generate_report(req: ReportGenerateRequest) -> dict[str, Any]:
    s = _get_session(req.session_id)
    analytics = analytics_engine.analyze(
        s["safe_df"],
        department_filter=req.department,
        category_filter=req.category,
        status_filter=req.status,
        priority_filter=req.priority,
        granularity=req.granularity,
    )
    if analytics.get("empty"):
        raise HTTPException(status_code=400, detail="Active filter slice has zero complaints.")

    try:
        bundle = gemini_service.generate_executive_report(
            analytics=analytics,
            focus_prompt=req.focus_prompt,
            api_key=req.api_key,
            model=req.model,
        )
    except GuardrailViolation as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    report_id = f"RPT-{str(uuid.uuid4())[:8].upper()}"
    db.save_report(
        report_id=report_id,
        session_id=req.session_id,
        source_name=s["source_name"],
        title=req.title,
        engine_mode=bundle["mode"],
        model_name=bundle["model"],
        report_data=bundle,
        analytics_snapshot={
            "kpis": analytics["kpis"],
            "departments": analytics["departments"],
            "delay_analysis": analytics["delay_analysis"],
            "pending_overdue_queue": analytics["pending_overdue_queue"][:25],
        },
    )
    return {
        "report_id": report_id,
        "session_id": req.session_id,
        "report_bundle": bundle,
    }


@app.get("/api/reports")
def list_reports() -> dict[str, Any]:
    return {"reports": db.list_reports(limit=30)}


@app.post("/api/reports/pdf")
def export_report_pdf(req: PdfExportRequest) -> Response:
    if req.report_id:
        saved = db.get_report(req.report_id)
        if not saved:
            raise HTTPException(status_code=404, detail="Saved report not found.")
        pdf_bytes = build_administrative_pdf(
            analytics=saved["analytics_snapshot"],
            report_bundle=saved["report_data"],
            source_name=saved["source_name"],
        )
        db.log_event("PDF_EXPORTED", f"Exported PDF for report {req.report_id}.", session_id=saved["session_id"], actor="ReportLab")
    else:
        if not req.session_id or not req.report_bundle:
            raise HTTPException(status_code=400, detail="Provide either report_id or session_id + report_bundle.")
        s = _get_session(req.session_id)
        analytics = analytics_engine.analyze(
            s["safe_df"],
            department_filter=req.department,
            category_filter=req.category,
            status_filter=req.status,
            priority_filter=req.priority,
            granularity=req.granularity,
        )
        pdf_bytes = build_administrative_pdf(
            analytics=analytics,
            report_bundle=req.report_bundle,
            source_name=s["source_name"],
        )
        db.log_event("PDF_EXPORTED", "Exported live administrative PDF report.", session_id=req.session_id, actor="ReportLab")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="civicpulse_administrative_report.pdf"'},
    )


@app.post("/api/ask")
def ask_civicpulse(req: AskRequest) -> dict[str, Any]:
    s = _get_session(req.session_id)
    analytics = analytics_engine.analyze(
        s["safe_df"],
        department_filter=req.department,
        category_filter=req.category,
        status_filter=req.status,
        priority_filter=req.priority,
        granularity=req.granularity,
    )
    if analytics.get("empty"):
        raise HTTPException(status_code=400, detail="Active filter slice has zero complaints to query.")

    history = db.list_chat_history(req.session_id)
    try:
        res = gemini_service.answer_question(
            question=req.question,
            analytics=analytics,
            history=history,
            api_key=req.api_key,
            model=req.model,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except GuardrailViolation as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    db.append_chat_turn(req.session_id, res["question"], res["answer"], res["mode"])
    return {
        "session_id": req.session_id,
        "result": res,
        "history": db.list_chat_history(req.session_id),
    }


@app.get("/api/ask/history/{session_id}")
def get_chat_history(session_id: str) -> dict[str, Any]:
    return {"history": db.list_chat_history(session_id)}


@app.get("/api/audit-logs")
def get_audit_logs(limit: int = 100) -> dict[str, Any]:
    return {"logs": db.list_audit_logs(limit=min(max(limit, 10), 500))}


@app.get("/api/sample-data/csv")
def download_sample_csv(rows: int = 620, include_pii: bool = False) -> Response:
    df = generate_complaint_dataset(num_rows=min(max(rows, 100), 2000), include_simulated_pii=include_pii)
    return Response(
        content=df.to_csv(index=False).encode("utf-8"),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="civicpulse_complaints_{len(df)}.csv"'},
    )


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

