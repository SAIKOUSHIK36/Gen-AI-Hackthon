"""Automated verification suite for PS 158 4-Layer Pipeline & FastAPI Endpoints."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from generate_sample_data import generate_synthetic_dataset  # noqa: E402
from llm_engine import (  # noqa: E402
    GeminiCognitiveEngine,
    PrivacyGuardrailViolation,
    assert_zero_pii_payload,
    build_safe_llm_payload,
)
from main import app  # noqa: E402
from privacy_analytics import ANON_WORKER_ID_RE, PIIShield, WorkloadAnalyticsEngine  # noqa: E402


def test_sample_generator_and_layer2_zero_pii() -> None:
    raw_df = generate_synthetic_dataset(num_rows=560, include_simulated_pii=True)
    assert len(raw_df) == 560
    assert "citizen_name" in raw_df.columns
    assert "free_text_complaint" in raw_df.columns

    shield = PIIShield()
    safe_df, receipt = shield.sanitize(raw_df)

    # All citizen PII columns must be completely dropped
    for forbidden in ("citizen_name", "citizen_phone", "citizen_email", "street_address", "free_text_complaint"):
        assert forbidden not in safe_df.columns
        assert forbidden in receipt.dropped_pii_columns

    # Zero post-shield PII leaks allowed
    assert receipt.post_shield_pii_leaks_detected == 0
    assert receipt.shield_status == "VERIFIED_ZERO_PII"
    assert receipt.total_inline_pii_scrubbed > 0

    # All worker IDs strictly follow anonymized DEPT-NNN pattern
    for wid in safe_df["worker_id"].unique():
        assert ANON_WORKER_ID_RE.match(wid), f"Worker ID not anonymized: {wid}"


def test_layer2_hashes_real_worker_names_and_blocks_custom_pii() -> None:
    dirty_df = pd.DataFrame(
        [
            {
                "ticket_id": "T-101",
                "submitted_at": "2026-10-01 09:00:00",
                "closed_at": "2026-10-01 15:00:00",
                "department": "Water & Sewer",
                "status": "Completed",
                "assigned_to": "Alice Johnson",
                "action": "Fixed leak, called Mr. Robert Smith at 555-391-4422 and 450 Maple Crest Rd",
                "requester_email": "alice.citizen@example.org",
                "notes": "Citizen complained loudly",
            },
            {
                "ticket_id": "T-102",
                "submitted_at": "2026-10-02 10:00:00",
                "closed_at": "",
                "department": "Sanitation & Waste",
                "status": "Open",
                "assigned_to": "SAN-108",
                "action": "Dispatched crew; contact bob.resident@mail.net",
                "requester_email": "bob.resident@mail.net",
                "notes": "123 Pine St",
            },
        ]
    )
    shield = PIIShield()
    safe_df, receipt = shield.sanitize(dirty_df)

    assert "requester_email" in receipt.dropped_pii_columns
    assert "notes" in receipt.dropped_pii_columns
    assert receipt.worker_ids_anonymized_count == 1
    assert receipt.post_shield_pii_leaks_detected == 0

    serialized = safe_df.to_json(date_format="iso")
    assert "Alice Johnson" not in serialized
    assert "Robert Smith" not in serialized
    assert "555-391-4422" not in serialized
    assert "450 Maple Crest Rd" not in serialized
    assert "bob.resident@mail.net" not in serialized
    assert "SAN-108" in serialized
    assert ANON_WORKER_ID_RE.match(safe_df.iloc[0]["worker_id"])


def test_layer3_and_layer4_guardrails() -> None:
    raw_df = generate_synthetic_dataset(num_rows=520, include_simulated_pii=True)
    safe_df, _ = PIIShield().sanitize(raw_df)
    analytics = WorkloadAnalyticsEngine().analyze(safe_df, granularity="month")

    assert analytics["kpis"]["total_requests"] == 520
    assert (
        analytics["kpis"]["completed_count"] + analytics["kpis"]["remaining_count"]
        == analytics["kpis"]["total_requests"]
    )
    assert len(analytics["categories"]) == 6
    assert len(analytics["worker_audit"]) >= 15

    # Pre-flight guardrail rejects tainted payload
    with pytest.raises(PrivacyGuardrailViolation):
        assert_zero_pii_payload({"kpis": {"note": "contact citizen@example.com"}})

    engine = GeminiCognitiveEngine()
    result = engine.generate_report(analytics, focus_area="Audit overdue water repairs")
    assert result["guardrails"]["preflight"]["preflight_passed"] is True
    assert result["guardrails"]["post_output"]["output_pii_scan_passed"] is True
    assert result["guardrails"]["post_output"]["worker_id_grounding_passed"] is True
    assert "executive_summary" in result["narrative"]

    # Ensure zero raw citizen info exists in payload preview
    preview_str = json.dumps(result["llm_payload_preview"])
    assert "citizen_name" not in preview_str
    assert "free_text_complaint" not in preview_str


def test_fastapi_endpoints_end_to_end() -> None:
    client = TestClient(app)

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    sample_resp = client.post(
        "/api/analyze/sample",
        json={"num_rows": 550, "include_simulated_pii": True, "granularity": "week"},
    )
    assert sample_resp.status_code == 200
    sample_data = sample_resp.json()
    session_id = sample_data["session_id"]
    assert sample_data["analytics"]["kpis"]["total_requests"] == 550
    assert sample_data["pii_audit"]["shield_status"] == "VERIFIED_ZERO_PII"

    filter_resp = client.post(
        "/api/filter",
        json={"session_id": session_id, "granularity": "month", "service_category": "Roads & Infrastructure"},
    )
    assert filter_resp.status_code == 200
    assert filter_resp.json()["analytics"]["kpis"]["total_requests"] > 0

    narrative_resp = client.post(
        "/api/narrative",
        json={"session_id": session_id, "granularity": "week", "focus_area": "Review backlog & ENG-042"},
    )
    assert narrative_resp.status_code == 200
    narrative_payload = narrative_resp.json()["narrative_result"]
    assert narrative_payload["guardrails"]["post_output"]["output_pii_scan_passed"] is True

    pdf_resp = client.post(
        "/api/export/pdf",
        json={"session_id": session_id, "granularity": "week", "narrative_result": narrative_payload},
    )
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    assert pdf_resp.content.startswith(b"%PDF")

    csv_resp = client.get("/api/sample-data/csv?rows=500")
    assert csv_resp.status_code == 200
    assert b"citizen_name" in csv_resp.content

    upload_resp = client.post(
        "/api/analyze/upload",
        files={"file": ("sample.csv", csv_resp.content, "text/csv")},
        data={"granularity": "week"},
    )
    assert upload_resp.status_code == 200
    assert upload_resp.json()["pii_audit"]["shield_status"] == "VERIFIED_ZERO_PII"
    assert upload_resp.json()["analytics"]["kpis"]["total_requests"] == 500


def test_dc311_and_public_open_data_ingestion() -> None:
    dc311_df = pd.DataFrame(
        [
            {
                "OBJECTID": 1001,
                "SERVICEREQUESTID": "24-00192831",
                "ADDDATE": "2026-09-01T10:15:00Z",
                "RESOLUTIONDATE": "2026-09-02T14:15:00Z",
                "SERVICEDUEDATE": "2026-09-04T10:15:00Z",
                "SERVICECODEDESCRIPTION": "Bulk Collection",
                "ORGANIZATIONACRONYM": "DPW",
                "STATUS_CODE": "CLOSED",
                "PRIORITY": "STANDARD",
                "WARD": 2.0,
                "STREETADDRESS": "1600 Pennsylvania Ave NW",
                "STATE": "DC",
                "LATITUDE": 38.8977,
                "LONGITUDE": -77.0365,
                "DETAILS": "Resident John Doe requested bulk pickup by front gate",
            },
            {
                "OBJECTID": 1002,
                "SERVICEREQUESTID": "24-00192832",
                "ADDDATE": "2026-09-03T09:00:00Z",
                "RESOLUTIONDATE": "",
                "SERVICEDUEDATE": "2026-09-05T09:00:00Z",
                "SERVICECODEDESCRIPTION": "15 Day Street Light Repair",
                "ORGANIZATIONACRONYM": "DDOT",
                "STATUS_CODE": "OPEN",
                "PRIORITY": "EMERGENCY",
                "WARD": 4.0,
                "STREETADDRESS": "4500 Georgia Ave NW",
                "STATE": "DC",
                "LATITUDE": 38.9451,
                "LONGITUDE": -77.0268,
                "DETAILS": "Outage reported by 202-555-0192",
            },
            {
                "OBJECTID": 1003,
                "SERVICEREQUESTID": "24-00192833",
                "ADDDATE": "2026-09-04T11:30:00Z",
                "RESOLUTIONDATE": "",
                "SERVICEDUEDATE": "2026-09-08T11:30:00Z",
                "SERVICECODEDESCRIPTION": "Pothole Investigation",
                "ORGANIZATIONACRONYM": "DDOT",
                "STATUS_CODE": "VOID",
                "PRIORITY": "LOW",
                "WARD": 6.0,
                "STREETADDRESS": "800 H St NE",
                "STATE": "DC",
                "LATITUDE": 38.9001,
                "LONGITUDE": -76.9950,
                "DETAILS": "Duplicate ticket",
            },
        ]
    )

    shield = PIIShield()
    safe_df, receipt = shield.sanitize(dc311_df)

    # PII & state columns must be dropped (STATE="DC" must NOT map to status)
    for dropped in ("STREETADDRESS", "STATE", "LATITUDE", "LONGITUDE", "DETAILS"):
        assert dropped in receipt.dropped_pii_columns
    assert "SERVICEDUEDATE" not in safe_df.columns
    assert receipt.post_shield_pii_leaks_detected == 0
    assert receipt.shield_status == "VERIFIED_ZERO_PII"

    assert list(safe_df["status"]) == ["Completed", "In Progress", "On Hold"]
    assert list(safe_df["priority"]) == ["Medium", "Critical", "Low"]
    assert list(safe_df["district_zone"]) == ["Ward 2", "Ward 4", "Ward 6"]
    assert safe_df.iloc[0]["action_taken"] == "Completed: Field inspection & resolution logged"
    assert safe_df.iloc[1]["action_taken"] == "Assigned: Pending field verification"
    assert "On Hold:" in safe_df.iloc[2]["action_taken"]
    assert safe_df.iloc[0]["sla_target_hours"] == pytest.approx(72.0)

    # Worker IDs derived from ORGANIZATIONACRONYM as DPW-XX / DDOT-XX matching strict regex
    assert safe_df.iloc[0]["worker_id"].startswith("DPW-")
    assert safe_df.iloc[1]["worker_id"].startswith("DDOT-")
    for wid in safe_df["worker_id"]:
        assert ANON_WORKER_ID_RE.match(wid)

    # Test minimal public 311 CSV missing worker_id, sla, and resolved_at, with PII in service_notes
    minimal_df = pd.DataFrame(
        [
            {
                "open_dt": "2026-10-01 08:00:00",
                "complaint_type": "Water Main Break",
                "case_status": "OPEN",
                "service_notes": "Crew check scheduled; call 202-555-8811 or citizen@example.com",
            },
            {
                "open_dt": "2026-10-05 14:00:00",
                "complaint_type": "Uncollected Trash",
                "case_status": "OPEN",
                "service_notes": "",
            },
            {
                "open_dt": "2026-10-02 10:00:00",
                "complaint_type": "General Inquiry",
                "case_status": "CLOSED",
                "service_notes": "",
            },
        ]
    )
    min_safe, min_receipt = shield.sanitize(minimal_df)
    assert min_receipt.post_shield_pii_leaks_detected == 0
    assert min_receipt.total_inline_pii_scrubbed >= 2
    assert "202-555-8811" not in min_safe.to_json(date_format="iso")
    assert "citizen@example.com" not in min_safe.to_json(date_format="iso")
    assert list(min_safe["status"]) == ["In Progress", "In Progress", "Completed"]
    assert min_safe.iloc[1]["action_taken"] == "No action taken"
    assert min_safe.iloc[2]["action_taken"] == "Completed: Field inspection & resolution logged"
    assert min_safe.iloc[2]["worker_id"].startswith("DEPT-")
    for wid in min_safe["worker_id"]:
        assert ANON_WORKER_ID_RE.match(wid)

    # Layer 3 + Layer 4 run seamlessly on real-world 311 structure
    analytics = WorkloadAnalyticsEngine().analyze(safe_df, granularity="month")
    narrative = GeminiCognitiveEngine().generate_report(analytics)
    assert narrative["guardrails"]["post_output"]["output_pii_scan_passed"] is True
    assert narrative["guardrails"]["post_output"]["worker_id_grounding_passed"] is True


