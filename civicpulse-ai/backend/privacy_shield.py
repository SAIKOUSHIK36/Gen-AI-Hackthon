"""Layer 2: Zero-PII Privacy Firewall & Schema Normalizer for CivicPulse AI.

Ingests CSV or Excel (.xlsx/.xls) complaint datasets, strips any citizen PII
columns (names, phones, emails, addresses, free-text personal descriptions),
scrubs residual inline PII tokens, and outputs strictly anonymized operational
records matching the CivicPulse schema.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

SAFE_COMPLAINT_COLUMNS: tuple[str, ...] = (
    "Complaint_ID",
    "Category",
    "Department",
    "Date_Received",
    "Status",
    "Deadline",
    "Resolution_Date",
    "Assigned_Department",
    "Assigned_Team",
    "Priority",
    "Delay_Reason",
    "Last_Updated_Date",
)

# Case-insensitive column aliases mapped to CivicPulse canonical names
COLUMN_ALIASES: dict[str, str] = {
    # Complaint_ID
    "complaint_id": "Complaint_ID",
    "complaintid": "Complaint_ID",
    "ticket_id": "Complaint_ID",
    "case_id": "Complaint_ID",
    "request_id": "Complaint_ID",
    "servicerequestid": "Complaint_ID",
    "sr_number": "Complaint_ID",
    "id": "Complaint_ID",
    # Category
    "category": "Category",
    "servicecodedescription": "Category",
    "service_name": "Category",
    "complaint_type": "Category",
    "service_category": "Category",
    "issue_type": "Category",
    # Department
    "department": "Department",
    "dept": "Department",
    "organizationacronym": "Department",
    "agency": "Department",
    # Date_Received
    "date_received": "Date_Received",
    "datereceived": "Date_Received",
    "date": "Date_Received",
    "created_at": "Date_Received",
    "adddate": "Date_Received",
    "created_date": "Date_Received",
    "open_dt": "Date_Received",
    "requested_datetime": "Date_Received",
    "submitted_at": "Date_Received",
    # Status
    "status": "Status",
    "status_code": "Status",
    "case_status": "Status",
    "ticket_status": "Status",
    # Deadline
    "deadline": "Deadline",
    "due_date": "Deadline",
    "serviceduedate": "Deadline",
    "target_date": "Deadline",
    "sla_due_date": "Deadline",
    # Resolution_Date
    "resolution_date": "Resolution_Date",
    "resolutiondate": "Resolution_Date",
    "resolved_at": "Resolution_Date",
    "closed_at": "Resolution_Date",
    "closed_date": "Resolution_Date",
    "closeddate": "Resolution_Date",
    # Assigned_Department
    "assigned_department": "Assigned_Department",
    "assigned_dept": "Assigned_Department",
    # Assigned_Team
    "assigned_team": "Assigned_Team",
    "team": "Assigned_Team",
    "worker_id": "Assigned_Team",
    "assigned_to": "Assigned_Team",
    "crew_id": "Assigned_Team",
    # Priority
    "priority": "Priority",
    "urgency": "Priority",
    "severity": "Priority",
    # Delay_Reason
    "delay_reason": "Delay_Reason",
    "delay_reasons": "Delay_Reason",
    "reason": "Delay_Reason",
    "action_taken": "Delay_Reason",
    "action_taken_log": "Delay_Reason",
    "resolution_description": "Delay_Reason",
    "service_notes": "Delay_Reason",
    # Last_Updated_Date
    "last_updated_date": "Last_Updated_Date",
    "last_updated": "Last_Updated_Date",
    "lastmodifieddate": "Last_Updated_Date",
    "updated_at": "Last_Updated_Date",
}

CANONICAL_PRIORITY: dict[str, tuple[str, ...]] = {
    "Complaint_ID": ("complaint_id", "complaintid", "servicerequestid", "ticket_id", "case_id", "request_id", "id"),
    "Category": ("category", "service_category", "servicecodedescription", "service_name", "complaint_type", "issue_type"),
    "Department": ("department", "dept", "organizationacronym", "agency"),
    "Date_Received": ("date_received", "datereceived", "created_at", "created_date", "adddate", "open_dt", "requested_datetime", "date"),
    "Status": ("status", "status_code", "case_status", "ticket_status"),
    "Deadline": ("deadline", "due_date", "serviceduedate", "target_date", "sla_due_date"),
    "Resolution_Date": ("resolution_date", "resolutiondate", "resolved_at", "closed_date", "closeddate", "closed_at"),
    "Assigned_Department": ("assigned_department", "assigned_dept"),
    "Assigned_Team": ("assigned_team", "team", "worker_id", "assigned_to", "crew_id"),
    "Priority": ("priority", "urgency", "severity"),
    "Delay_Reason": ("delay_reason", "delay_reasons", "reason", "resolution_description", "action_taken", "service_notes"),
    "Last_Updated_Date": ("last_updated_date", "last_updated", "lastmodifieddate", "updated_at"),
}

FORBIDDEN_PII_KEYWORDS: tuple[str, ...] = (
    "citizen",
    "resident",
    "caller",
    "complainant",
    "requester",
    "customer",
    "applicant",
    "name",
    "phone",
    "mobile",
    "tel",
    "email",
    "mail",
    "address",
    "street",
    "apt",
    "zip",
    "postal",
    "ssn",
    "aadhaar",
    "passport",
    "license",
    "dob",
    "birth",
    "ip_addr",
    "lat",
    "lon",
    "coord",
    "complaint_text",
    "free_text",
    "comment",
    "detail",
    "bio",
)

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(
    r"(?<!\w)(?:\+?\d{1,3}[\s.-]?)?(?:\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}(?!\w)"
    r"|(?<!\w)\d{3}[\s.-]\d{4}(?!\w)"
)
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
ADDRESS_RE = re.compile(
    r"\b\d{1,5}\s+(?!Day\b|Days\b|Hour\b|Hours\b|Week\b|Weeks\b|Month\b|Months\b|Year\b|Years\b)"
    r"[A-Za-z0-9.\s]{2,30}\b(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Way|Court|Ct|Place|Pl)\b\.?",
    re.IGNORECASE,
)
TITLE_NAME_RE = re.compile(r"\b(?:Mr|Mrs|Ms|Miss|Dr|Prof)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b")
IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

ANON_TEAM_RE = re.compile(r"^[A-Z0-9]{2,6}-(?:Team-[A-Z0-9]{1,4}|\d{2,4})$", re.IGNORECASE)

STATUS_MAP: dict[str, str] = {
    "resolved": "Resolved",
    "closed": "Resolved",
    "close": "Resolved",
    "completed": "Resolved",
    "complete": "Resolved",
    "done": "Resolved",
    "pending": "Pending",
    "open": "Pending",
    "opened": "Pending",
    "new": "Pending",
    "awaiting": "Pending",
    "in progress": "In Progress",
    "in_progress": "In Progress",
    "in-progress": "In Progress",
    "active": "In Progress",
    "assigned": "In Progress",
    "rejected": "Rejected",
    "void": "Rejected",
    "voided": "Rejected",
    "cancelled": "Rejected",
    "canceled": "Rejected",
    "invalid": "Rejected",
    "overdue": "Overdue",
    "escalated": "Overdue",
}

PRIORITY_MAP: dict[str, str] = {
    "critical": "Critical",
    "emergency": "Critical",
    "urgent": "High",
    "high": "High",
    "standard": "Medium",
    "normal": "Medium",
    "medium": "Medium",
    "routine": "Low",
    "low": "Low",
}


def scrub_pii_text(value: str) -> tuple[str, dict[str, int]]:
    """Scrub inline PII from a string and return cleaned text + match counts."""
    counts = {"email": 0, "phone": 0, "address": 0, "gov_id": 0, "name_marker": 0, "ip_address": 0}
    if not value:
        return "", counts

    text = str(value)
    for pattern, key, token in (
        (EMAIL_RE, "email", "[REDACTED-EMAIL]"),
        (SSN_RE, "gov_id", "[REDACTED-ID]"),
        (ADDRESS_RE, "address", "[REDACTED-ADDRESS]"),
        (PHONE_RE, "phone", "[REDACTED-PHONE]"),
        (TITLE_NAME_RE, "name_marker", "[REDACTED-PERSON]"),
        (IPV4_RE, "ip_address", "[REDACTED-IP]"),
    ):
        found = pattern.findall(text)
        if found:
            counts[key] += len(found)
            text = pattern.sub(token, text)

    text = re.sub(r"\s{2,}", " ", text).strip(" ,;-")
    return text, counts


def scan_text_for_pii(text: str) -> list[str]:
    if not text:
        return []
    hits: list[str] = []
    if EMAIL_RE.search(text):
        hits.append("email")
    if SSN_RE.search(text):
        hits.append("gov_id")
    if ADDRESS_RE.search(text):
        hits.append("street_address")
    if PHONE_RE.search(text):
        hits.append("phone_number")
    if TITLE_NAME_RE.search(text):
        hits.append("personal_name_title")
    if IPV4_RE.search(text):
        hits.append("ip_address")
    return hits


@dataclass
class SanitizationReceipt:
    input_rows: int = 0
    input_columns: list[str] = field(default_factory=list)
    mapped_columns: dict[str, str] = field(default_factory=dict)
    dropped_pii_columns: list[str] = field(default_factory=list)
    retained_columns: list[str] = field(default_factory=list)
    scrubbed_inline_pii: dict[str, int] = field(
        default_factory=lambda: {"email": 0, "phone": 0, "address": 0, "gov_id": 0, "name_marker": 0, "ip_address": 0}
    )
    total_inline_pii_scrubbed: int = 0
    teams_anonymized_count: int = 0
    post_shield_leaks: int = 0
    shield_status: str = "VERIFIED_ZERO_PII"

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_rows": self.input_rows,
            "input_columns": self.input_columns,
            "mapped_columns": self.mapped_columns,
            "dropped_pii_columns": self.dropped_pii_columns,
            "retained_columns": self.retained_columns,
            "scrubbed_inline_pii": self.scrubbed_inline_pii,
            "total_inline_pii_scrubbed": self.total_inline_pii_scrubbed,
            "teams_anonymized_count": self.teams_anonymized_count,
            "post_shield_leaks": self.post_shield_leaks,
            "shield_status": self.shield_status,
        }


class PrivacyShield:
    """Zero-PII firewall & schema mapper for CSV/Excel complaint datasets."""

    def __init__(self, salt: str = "civicpulse-zero-pii-shield") -> None:
        self.salt = salt

    @staticmethod
    def _clean_key(col: str) -> str:
        return re.sub(r"[^a-z0-9]+", "_", str(col).strip().lower()).strip("_")

    def _is_forbidden(self, raw_col: str, mapped_col: str) -> bool:
        if mapped_col in SAFE_COMPLAINT_COLUMNS:
            return False
        low = str(raw_col).strip().lower()
        return any(kw in low or kw in mapped_col.lower() for kw in FORBIDDEN_PII_KEYWORDS)

    def _anonymize_team(self, raw_team: Any, dept: str, complaint_id: str) -> tuple[str, bool]:
        val = "" if raw_team is None or (isinstance(raw_team, float) and np.isnan(raw_team)) else str(raw_team).strip()
        if val.lower() in {"", "nan", "none", "null", "unassigned"}:
            val = ""

        if val and ANON_TEAM_RE.match(val):
            return val, False

        dept_letters = re.sub(r"[^A-Za-z]", "", dept).upper()[:3] or "DEP"
        if not val:
            slot = (int(hashlib.sha256(f"{self.salt}:{dept}:{complaint_id}".encode("utf-8")).hexdigest()[:6], 16) % 4) + 1
            return f"{dept_letters}-Team-{slot:02d}", True

        digest = hashlib.sha256(f"{self.salt}:{val}".encode("utf-8")).hexdigest()
        code = (int(digest[:6], 16) % 90) + 10
        return f"{dept_letters}-Team-{code}", True

    def sanitize(self, raw_df: pd.DataFrame) -> tuple[pd.DataFrame, SanitizationReceipt]:
        if raw_df is None or raw_df.empty:
            raise ValueError("Uploaded dataset is empty; at least one complaint record is required.")

        receipt = SanitizationReceipt(
            input_rows=int(len(raw_df)),
            input_columns=[str(c) for c in raw_df.columns],
        )

        # 1. Map case-insensitive column aliases and drop citizen PII/unmapped columns
        candidates: dict[str, list[tuple[str, str]]] = {}
        dropped: list[str] = []

        for raw_col in raw_df.columns:
            raw_str = str(raw_col)
            clean_key = self._clean_key(raw_str)
            canonical = COLUMN_ALIASES.get(clean_key, "")
            if not canonical or self._is_forbidden(raw_str, canonical):
                dropped.append(raw_str)
            else:
                candidates.setdefault(canonical, []).append((raw_str, clean_key))

        rename_map: dict[str, str] = {}
        for canonical, pairs in candidates.items():
            order = CANONICAL_PRIORITY.get(canonical, ())
            sorted_pairs = sorted(
                pairs,
                key=lambda p: order.index(p[1]) if p[1] in order else len(order),
            )
            chosen_raw, _ = sorted_pairs[0]
            rename_map[chosen_raw] = canonical
            receipt.mapped_columns[chosen_raw] = canonical
            for dup_raw, _ in sorted_pairs[1:]:
                dropped.append(dup_raw)

        receipt.dropped_pii_columns = dropped
        df = raw_df[list(rename_map.keys())].rename(columns=rename_map).copy()

        # 2. Validate Date_Received & populate missing structural defaults
        if "Date_Received" not in df.columns:
            raise ValueError("Dataset must contain a Date_Received (or date/created_at/adddate) column.")

        if "Complaint_ID" not in df.columns:
            df["Complaint_ID"] = [f"C{i + 1:04d}" for i in range(len(df))]
        if "Category" not in df.columns:
            df["Category"] = "General Public Service"
        if "Department" not in df.columns:
            df["Department"] = "Municipal Dept"
        if "Status" not in df.columns:
            df["Status"] = "Pending"
        if "Assigned_Department" not in df.columns:
            df["Assigned_Department"] = df["Department"]
        if "Assigned_Team" not in df.columns:
            df["Assigned_Team"] = ""
        if "Priority" not in df.columns:
            df["Priority"] = "Medium"
        if "Delay_Reason" not in df.columns:
            df["Delay_Reason"] = ""

        # 3. Parse dates cleanly (timezone-naive UTC)
        df["Date_Received"] = pd.to_datetime(df["Date_Received"], errors="coerce", format="mixed", utc=True).dt.tz_localize(None)
        df = df.dropna(subset=["Date_Received"]).copy()
        if df.empty:
            raise ValueError("No valid timestamps found in Date_Received column.")

        if "Deadline" in df.columns:
            df["Deadline"] = pd.to_datetime(df["Deadline"], errors="coerce", format="mixed", utc=True).dt.tz_localize(None)
            df["Deadline"] = df["Deadline"].fillna(df["Date_Received"] + pd.Timedelta(days=5))
        else:
            df["Deadline"] = df["Date_Received"] + pd.Timedelta(days=5)

        if "Resolution_Date" in df.columns:
            df["Resolution_Date"] = pd.to_datetime(
                df["Resolution_Date"], errors="coerce", format="mixed", utc=True
            ).dt.tz_localize(None)
        else:
            df["Resolution_Date"] = pd.NaT

        if "Last_Updated_Date" in df.columns:
            df["Last_Updated_Date"] = pd.to_datetime(
                df["Last_Updated_Date"], errors="coerce", format="mixed", utc=True
            ).dt.tz_localize(None)
            df["Last_Updated_Date"] = df["Last_Updated_Date"].fillna(
                df["Resolution_Date"].fillna(df["Date_Received"])
            )
        else:
            df["Last_Updated_Date"] = df["Resolution_Date"].fillna(df["Date_Received"])

        # 4. Normalize categorical columns
        for col, default in (
            ("Category", "General Public Service"),
            ("Department", "Municipal Dept"),
            ("Assigned_Department", "Municipal Dept"),
        ):
            vals = df[col].fillna(default).astype(str).str.strip()
            df[col] = vals.replace({"": default, "nan": default, "None": default})

        df["Status"] = [
            STATUS_MAP.get(str(v).strip().lower(), str(v).strip().title() if str(v).strip() else "Pending")
            for v in df["Status"].fillna("Pending").tolist()
        ]
        df["Priority"] = [
            PRIORITY_MAP.get(str(v).strip().lower(), "Medium")
            for v in df["Priority"].fillna("Medium").tolist()
        ]

        # 5. Scrub inline PII in text fields (preserving blank Delay_Reason as empty so analytics distinguishes missing reasons!)
        for text_col in ("Complaint_ID", "Category", "Department", "Assigned_Department", "Delay_Reason"):
            cleaned_list: list[str] = []
            for raw_val in df[text_col].tolist():
                val_str = "" if raw_val is None or (isinstance(raw_val, float) and np.isnan(raw_val)) else str(raw_val).strip()
                if val_str.lower() in {"nan", "none", "null", "n/a", "na", "-"}:
                    val_str = ""
                if not val_str:
                    cleaned_list.append("" if text_col == "Delay_Reason" else "General")
                    continue
                cleaned, counts = scrub_pii_text(val_str)
                for k, v in counts.items():
                    receipt.scrubbed_inline_pii[k] += v
                cleaned_list.append(cleaned)
            df[text_col] = cleaned_list

        # 6. Anonymize Assigned_Team tokens
        teams: list[str] = []
        anon_cnt = 0
        for raw_t, dept, cid in zip(
            df["Assigned_Team"].tolist(),
            df["Assigned_Department"].tolist(),
            df["Complaint_ID"].tolist(),
        ):
            anon_team, was_hashed = self._anonymize_team(raw_t, dept, cid)
            if was_hashed:
                anon_cnt += 1
            teams.append(anon_team)
        df["Assigned_Team"] = teams
        receipt.teams_anonymized_count = anon_cnt

        final_cols = [c for c in SAFE_COMPLAINT_COLUMNS if c in df.columns]
        df = df[final_cols].copy()
        receipt.retained_columns = final_cols
        receipt.total_inline_pii_scrubbed = sum(receipt.scrubbed_inline_pii.values())

        # 7. Post-shield verification sweep
        leaks = 0
        for col in ("Category", "Department", "Status", "Assigned_Team", "Delay_Reason"):
            concat = " | ".join(df[col].astype(str).tolist())
            if scan_text_for_pii(concat):
                leaks += 1
        receipt.post_shield_leaks = leaks
        receipt.shield_status = "VERIFIED_ZERO_PII" if leaks == 0 else "PII_WARNING"

        return df.reset_index(drop=True), receipt

