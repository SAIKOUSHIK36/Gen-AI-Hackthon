"""Comprehensive pytest suite for CivicPulse AI backend, ML Isolation Forest, SQLite & FastAPI."""

from __future__ import annotations

import io
import sys
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from analytics_engine import INSUFFICIENT_EVIDENCE_MSG, CivicPulseAnalyticsEngine  # noqa: E402
from database import CivicPulseDB  # noqa: E402
from gemini_service import CivicPulseGeminiService  # noqa: E402
import main as main_module  # noqa: E402
from privacy_shield import PrivacyShield  # noqa: E402
from sample_data_generator import generate_complaint_dataset  # noqa: E402


def test_privacy_shield_and_evidence_separation() -> None:
    raw_df = generate_complaint_dataset(num_rows=320, include_simulated_pii=True)
    shield = PrivacyShield()
    safe_df, receipt = shield.sanitize(raw_df)

    for pii_col in ("Citizen_Name", "Citizen_Phone", "Citizen_Email", "Street_Address"):
        assert pii_col not in safe_df.columns
        assert pii_col in receipt.dropped_pii_columns
    assert receipt.post_shield_leaks == 0
    assert receipt.shield_status == "VERIFIED_ZERO_PII"

    analytics = CivicPulseAnalyticsEngine().analyze(safe_df)
    assert analytics["kpis"]["total_received"] == 320
    assert analytics["kpis"]["overdue_count"] > 0
    assert len(analytics["delay_analysis"]["recorded_reasons"]) > 0
    assert analytics["ml_anomalies"]["model"] == "Scikit-learn IsolationForest"
    assert analytics["ml_anomalies"]["flagged_delay_ticket_count"] >= 1


def test_insufficient_evidence_never_hallucinates_reason() -> None:
    # Isolated delayed ticket with no Delay_Reason and small dataset (no pattern signal)
    df = pd.DataFrame(
        [
            {
                "Complaint_ID": "C001",
                "Category": "Water Leakage",
                "Department": "Water Dept",
                "Date_Received": "2026-10-01",
                "Status": "Pending",
                "Deadline": "2026-10-03",
                "Resolution_Date": "",
                "Priority": "Low",
                "Delay_Reason": "",
                "Last_Updated_Date": "2026-10-20",
            },
            {
                "Complaint_ID": "C002",
                "Category": "Water Leakage",
                "Department": "Water Dept",
                "Date_Received": "2026-10-21",
                "Status": "Resolved",
                "Deadline": "2026-10-25",
                "Resolution_Date": "2026-10-22",
                "Priority": "Medium",
                "Delay_Reason": "None",
                "Last_Updated_Date": "2026-10-22",
            },
        ]
    )
    safe_df, _ = PrivacyShield().sanitize(df)
    analytics = CivicPulseAnalyticsEngine().analyze(safe_df)
    q = analytics["pending_overdue_queue"][0]
    assert q["is_overdue"] is True
    assert q["evidence_type"] == "INSUFFICIENT_EVIDENCE"
    assert q["delay_explanation"] == INSUFFICIENT_EVIDENCE_MSG


def test_excel_upload_qa_reports_pdf_and_sqlite(tmp_path: Path) -> None:
    # Use isolated test SQLite db
    main_module.db = CivicPulseDB(db_path=tmp_path / "test_civicpulse.db")
    client = TestClient(main_module.app)

    assert client.get("/api/health").status_code == 200

    # Generate Excel (.xlsx) in memory with citizen PII column to verify Excel + PII Shield
    df = generate_complaint_dataset(num_rows=180, include_simulated_pii=True)
    xlsx_buf = io.BytesIO()
    df.to_excel(xlsx_buf, index=False, engine="openpyxl")
    xlsx_buf.seek(0)

    up = client.post(
        "/api/datasets/upload",
        files={
            "file": (
                "complaints_2026.xlsx",
                xlsx_buf.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        data={"granularity": "week"},
    )
    assert up.status_code == 200
    payload = up.json()
    sid = payload["session_id"]
    assert payload["analytics"]["kpis"]["total_received"] == 180
    assert "Citizen_Email" in payload["pii_receipt"]["dropped_pii_columns"]

    # Ask CivicPulse AI
    ask1 = client.post("/api/ask", json={"session_id": sid, "question": "How many complaints are resolved?"})
    assert ask1.status_code == 200
    assert str(payload["analytics"]["kpis"]["resolved_count"]) in ask1.json()["result"]["answer"]

    ask2 = client.post("/api/ask", json={"session_id": sid, "question": "Why are complaints getting delayed?"})
    assert ask2.status_code == 200
    assert "Confirmed Recorded Delay Reasons" in ask2.json()["result"]["answer"]

    # Generate & save report in SQLite
    rep = client.post(
        "/api/reports/generate",
        json={"session_id": sid, "title": "Q4 Municipal Delay Audit", "focus_prompt": "Roads and Water overdue analysis"},
    )
    assert rep.status_code == 200
    report_id = rep.json()["report_id"]

    hist = client.get("/api/reports")
    assert hist.status_code == 200
    assert any(r["report_id"] == report_id for r in hist.json()["reports"])

    # Export PDF directly via report_id
    pdf = client.post("/api/reports/pdf", json={"report_id": report_id})
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF")

    # Verify SQLite Audit Logs
    logs = client.get("/api/audit-logs")
    assert logs.status_code == 200
    event_types = {entry["event_type"] for entry in logs.json()["logs"]}
    assert {"DATASET_INGESTED", "ML_ANOMALY_SCAN", "AI_QA_QUERY", "REPORT_GENERATED", "PDF_EXPORTED"}.issubset(event_types)

