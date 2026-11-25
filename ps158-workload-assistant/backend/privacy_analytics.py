"""Layer 2 (PII Shield) & Layer 3 (Pandas/NumPy Analytics Engine).

Layer 2 strictly strips citizen PII columns, scrubs inline PII tokens from
surviving operational text, and guarantees every staff reference uses an
anonymized worker ID (e.g., ENG-042, SAN-108).

Layer 3 processes only the PII-free sanitized dataset using Pandas and NumPy
to compute period workloads, completed vs. remaining backlog, category SLA
performance, and worker accountability audit metrics.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

# Strict allowlist of operational columns permitted beyond Layer 2.
SAFE_OPERATIONAL_COLUMNS: tuple[str, ...] = (
    "request_id",
    "created_at",
    "resolved_at",
    "service_category",
    "priority",
    "status",
    "worker_id",
    "action_taken",
    "sla_target_hours",
    "resolution_hours",
    "district_zone",
)

# Internal helper columns allowed during Layer 2 normalization (never retained past Layer 2).
INTERNAL_DERIVATION_COLUMNS: tuple[str, ...] = (
    "due_at",
    "sla_days",
)

# Column aliases mapped to canonical operational names before allowlist filtering (case-insensitive).
COLUMN_ALIASES: dict[str, str] = {
    # Request ID
    "request_id": "request_id",
    "servicerequestid": "request_id",
    "service_request_id": "request_id",
    "sr_number": "request_id",
    "unique_key": "request_id",
    "ticket_id": "request_id",
    "case_id": "request_id",
    "id": "request_id",
    # Date / Created Timestamp
    "created_at": "created_at",
    "date": "created_at",
    "adddate": "created_at",
    "created_date": "created_at",
    "open_dt": "created_at",
    "requested_datetime": "created_at",
    "submitted_at": "created_at",
    "opened_at": "created_at",
    "serviceorderdate": "created_at",
    "timestamp": "created_at",
    # Resolved Timestamp
    "resolved_at": "resolved_at",
    "resolutiondate": "resolved_at",
    "resolution_date": "resolved_at",
    "closed_at": "resolved_at",
    "closeddate": "resolved_at",
    "closed_date": "resolved_at",
    "completed_at": "resolved_at",
    # Service Category
    "service_category": "service_category",
    "category": "service_category",
    "servicecodedescription": "service_category",
    "service_name": "service_category",
    "complaint_type": "service_category",
    "department": "service_category",
    "service_type": "service_category",
    "request_type": "service_category",
    "servicetypecodedescription": "service_category",
    # Priority
    "priority": "priority",
    "urgency": "priority",
    "severity": "priority",
    # Status
    "status": "status",
    "status_code": "status",
    "case_status": "status",
    "ticket_status": "status",
    # Worker / Agency Identifier
    "worker_id": "worker_id",
    "assigned_to": "worker_id",
    "organizationacronym": "worker_id",
    "agency": "worker_id",
    "worker": "worker_id",
    "employee_id": "worker_id",
    "crew_id": "worker_id",
    "team_id": "worker_id",
    "staff_id": "worker_id",
    "agent_id": "worker_id",
    "technician_id": "worker_id",
    # Action Taken
    "action_taken": "action_taken",
    "action_taken_log": "action_taken",
    "resolution_description": "action_taken",
    "service_notes": "action_taken",
    "action": "action_taken",
    "resolution_action": "action_taken",
    "work_action": "action_taken",
    # SLA & Duration
    "sla_target_hours": "sla_target_hours",
    "sla_hours": "sla_target_hours",
    "target_hours": "sla_target_hours",
    "serviceduedate": "due_at",
    "due_date": "due_at",
    "sla_due_date": "due_at",
    "sla_days": "sla_days",
    "resolution_hours": "resolution_hours",
    "turnaround_hours": "resolution_hours",
    "duration_hours": "resolution_hours",
    # District / Ward
    "district_zone": "district_zone",
    "ward": "district_zone",
    "zone": "district_zone",
    "district": "district_zone",
}

# Preferred source column order when multiple aliases map to the same canonical field.
CANONICAL_ALIAS_PRIORITY: dict[str, tuple[str, ...]] = {
    "request_id": ("request_id", "servicerequestid", "service_request_id", "ticket_id", "case_id", "sr_number", "unique_key", "id"),
    "created_at": ("created_at", "created_date", "adddate", "open_dt", "requested_datetime", "date", "submitted_at", "opened_at", "serviceorderdate", "timestamp"),
    "resolved_at": ("resolved_at", "resolutiondate", "resolution_date", "closed_at", "closeddate", "closed_date", "completed_at"),
    "service_category": ("service_category", "category", "servicecodedescription", "service_name", "complaint_type", "department", "service_type", "request_type", "servicetypecodedescription"),
    "status": ("status", "status_code", "case_status", "ticket_status"),
    "worker_id": ("worker_id", "assigned_to", "staff_id", "employee_id", "agent_id", "technician_id", "crew_id", "team_id", "worker", "organizationacronym", "agency"),
    "action_taken": ("action_taken", "action_taken_log", "resolution_description", "service_notes", "resolution_action", "work_action", "action"),
}

ORG_LEVEL_WORKER_ALIASES: set[str] = {"organizationacronym", "agency", "department"}

# Explicit substrings identifying forbidden citizen PII or free-text columns.
FORBIDDEN_COLUMN_KEYWORDS: tuple[str, ...] = (
    "citizen",
    "resident",
    "caller",
    "requester",
    "customer",
    "applicant",
    "complainant",
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
    "description",
    "complaint",
    "comment",
    "note",
    "free_text",
    "narrative",
    "remark",
    "message",
    "detail",
    "bio",
)

# Compiled PII detection regex patterns.
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(
    r"(?<!\w)(?:\+?\d{1,3}[\s.-]?)?(?:\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}(?!\w)"
    r"|(?<!\w)\d{3}[\s.-]\d{4}(?!\w)"
)
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
ADDRESS_RE = re.compile(
    r"\b\d{1,5}\s+(?!Day\b|Days\b|Hour\b|Hours\b|Minute\b|Minutes\b|Week\b|Weeks\b|Month\b|Months\b|Year\b|Years\b)"
    r"[A-Za-z0-9.\s]{2,32}\b(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Way|Court|Ct|Place|Pl)\b\.?",
    re.IGNORECASE,
)
TITLE_NAME_RE = re.compile(
    r"\b(?:Mr|Mrs|Ms|Miss|Dr|Prof)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b"
)
CONTACT_PHRASE_RE = re.compile(
    r"\b(?i:notify|contact|caller|resident|citizen)\s*[:=-]\s*[A-Z][a-z]{1,20}(?:\s+[A-Z][a-z]{1,20})?\b"
    r"|\b(?i:resident|citizen|caller)\s+[A-Z][a-z]{1,20}\s+[A-Z][a-z]{1,20}\b"
)
IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

ANON_WORKER_ID_RE = re.compile(r"^[A-Z]{2,5}-\d{2,4}$")

CATEGORY_PREFIX_MAP: dict[str, str] = {
    "Roads & Infrastructure": "ENG",
    "Sanitation & Waste": "SAN",
    "Water & Sewer": "WTR",
    "Street Lighting & Power": "ELC",
    "Parks & Public Spaces": "PRK",
    "Code Enforcement & Permits": "COD",
}

COMPLETED_STATUSES = {"completed", "closed", "resolved", "done"}
ESCALATED_STATUSES = {"escalated", "overdue", "critical_hold"}

STATUS_NORMALIZATION_MAP: dict[str, str] = {
    "open": "In Progress",
    "opened": "In Progress",
    "active": "In Progress",
    "assigned": "In Progress",
    "pending": "In Progress",
    "in progress": "In Progress",
    "in_progress": "In Progress",
    "in-progress": "In Progress",
    "closed": "Completed",
    "close": "Completed",
    "closed (duplicate)": "Completed",
    "completed": "Completed",
    "complete": "Completed",
    "resolved": "Completed",
    "done": "Completed",
    "void": "On Hold",
    "voided": "On Hold",
    "on hold": "On Hold",
    "on_hold": "On Hold",
    "on-hold": "On Hold",
    "hold": "On Hold",
    "cancelled": "On Hold",
    "canceled": "On Hold",
    "deferred": "On Hold",
    "escalated": "Escalated",
    "overdue": "Escalated",
    "critical_hold": "Escalated",
}

PRIORITY_NORMALIZATION_MAP: dict[str, str] = {
    "emergency": "Critical",
    "critical": "Critical",
    "urgent": "High",
    "high": "High",
    "standard": "Medium",
    "normal": "Medium",
    "medium": "Medium",
    "routine": "Low",
    "low": "Low",
}


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        f = float(val)
        return round(f, 2) if np.isfinite(f) else default
    except (TypeError, ValueError):
        return default


def _safe_int(val: Any, default: int = 0) -> int:
    try:
        f = float(val)
        return int(round(f)) if np.isfinite(f) else default
    except (TypeError, ValueError):
        return default


def scrub_pii_text(value: str) -> tuple[str, dict[str, int]]:
    """Scrub any inline PII tokens from an operational text string."""
    counts = {
        "email": 0,
        "phone": 0,
        "address": 0,
        "gov_id": 0,
        "name_marker": 0,
        "ip_address": 0,
    }
    if not value:
        return "", counts

    text = str(value)

    def _sub(pattern: re.Pattern[str], key: str, replacement: str, target: str) -> str:
        matches = pattern.findall(target)
        if matches:
            counts[key] += len(matches)
            return pattern.sub(replacement, target)
        return target

    text = _sub(EMAIL_RE, "email", "[REDACTED-EMAIL]", text)
    text = _sub(SSN_RE, "gov_id", "[REDACTED-ID]", text)
    text = _sub(ADDRESS_RE, "address", "[REDACTED-ADDRESS]", text)
    text = _sub(PHONE_RE, "phone", "[REDACTED-PHONE]", text)
    text = _sub(TITLE_NAME_RE, "name_marker", "[REDACTED-PERSON]", text)
    text = _sub(CONTACT_PHRASE_RE, "name_marker", "[REDACTED-CONTACT]", text)
    text = _sub(IPV4_RE, "ip_address", "[REDACTED-IP]", text)
    # Clean dangling empty parens/punctuation left after scrubbing
    text = re.sub(r"\(\s*(?:callback|notify)?\s*\[REDACTED-[A-Z-]+\]\s*\)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*[-–]\s*notify\s+\[REDACTED-[A-Z-]+\]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+near\s+\[REDACTED-[A-Z-]+\]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s{2,}", " ", text).strip(" ,;-")
    return text, counts


def scan_text_for_pii(text: str) -> list[str]:
    """Return list of PII categories detected in a serialized text string."""
    if not text:
        return []
    findings: list[str] = []
    if EMAIL_RE.search(text):
        findings.append("email")
    if SSN_RE.search(text):
        findings.append("gov_id")
    if ADDRESS_RE.search(text):
        findings.append("street_address")
    if PHONE_RE.search(text):
        findings.append("phone_number")
    if TITLE_NAME_RE.search(text):
        findings.append("personal_name_title")
    if IPV4_RE.search(text):
        findings.append("ip_address")
    return findings


@dataclass
class PIIAuditReceipt:
    """Auditable privacy verification record generated by Layer 2."""

    input_rows: int = 0
    input_columns: list[str] = field(default_factory=list)
    dropped_pii_columns: list[str] = field(default_factory=list)
    retained_safe_columns: list[str] = field(default_factory=list)
    scrubbed_inline_pii: dict[str, int] = field(
        default_factory=lambda: {
            "email": 0,
            "phone": 0,
            "address": 0,
            "gov_id": 0,
            "name_marker": 0,
            "ip_address": 0,
        }
    )
    total_inline_pii_scrubbed: int = 0
    worker_ids_anonymized_count: int = 0
    post_shield_pii_leaks_detected: int = 0
    shield_status: str = "VERIFIED_ZERO_PII"

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_rows": self.input_rows,
            "input_columns": self.input_columns,
            "dropped_pii_columns": self.dropped_pii_columns,
            "retained_safe_columns": self.retained_safe_columns,
            "scrubbed_inline_pii": self.scrubbed_inline_pii,
            "total_inline_pii_scrubbed": self.total_inline_pii_scrubbed,
            "worker_ids_anonymized_count": self.worker_ids_anonymized_count,
            "post_shield_pii_leaks_detected": self.post_shield_pii_leaks_detected,
            "shield_status": self.shield_status,
        }


class PIIShield:
    """Layer 2: Zero-Trust Privacy Firewall & Worker Anonymizer."""

    def __init__(self, salt: str = "ps158-municipal-privacy-shield") -> None:
        self.salt = salt

    def _normalize_column_name(self, col: str) -> str:
        clean = re.sub(r"[^a-z0-9]+", "_", str(col).strip().lower()).strip("_")
        return COLUMN_ALIASES.get(clean, clean)

    def _clean_col_key(self, col: str) -> str:
        return re.sub(r"[^a-z0-9]+", "_", str(col).strip().lower()).strip("_")

    def _is_forbidden_column(self, raw_col: str, normalized_col: str) -> bool:
        if normalized_col in SAFE_OPERATIONAL_COLUMNS or normalized_col in INTERNAL_DERIVATION_COLUMNS:
            return False
        lower_raw = str(raw_col).strip().lower()
        return any(kw in lower_raw or kw in normalized_col for kw in FORBIDDEN_COLUMN_KEYWORDS)

    def _derive_dept_prefix(self, raw_org: str, service_category: str) -> str:
        if raw_org:
            letters = re.sub(r"[^A-Za-z]", "", raw_org).upper()
            if 2 <= len(letters) <= 5:
                return letters
            words = [w for w in re.split(r"[^A-Za-z]+", raw_org.strip()) if w]
            if len(words) >= 2:
                initials = "".join(w[0].upper() for w in words[:4])
                if 2 <= len(initials) <= 5:
                    return initials

        cat_lower = str(service_category).lower()
        for cat_name, cat_prefix in CATEGORY_PREFIX_MAP.items():
            if cat_name.lower() in cat_lower:
                return cat_prefix

        keyword_prefixes = (
            (("road", "pothole", "sidewalk", "curb", "bridge", "traffic", "paving", "alley"), "ENG"),
            (("trash", "sanit", "waste", "bulk", "dump", "litter", "recycl", "leaf"), "SAN"),
            (("water", "sewer", "hydrant", "drain", "pipe", "leak"), "WTR"),
            (("light", "lamp", "signal", "power", "electric", "outage"), "ELC"),
            (("tree", "park", "grass", "forestry", "graffiti"), "PRK"),
            (("code", "permit", "inspect", "parking", "abandoned", "enforcement"), "COD"),
        )
        for keywords, code in keyword_prefixes:
            if any(kw in cat_lower for kw in keywords):
                return code

        return "DEPT"

    def _anonymize_worker_id(
        self,
        raw_worker: Any,
        service_category: str,
        request_id: str = "",
        district_zone: str = "",
        from_org_col: bool = False,
    ) -> tuple[str, bool]:
        """Ensure worker identifier strictly matches ANON format (e.g., ENG-042 or DEPT-01..12)."""
        val = "" if raw_worker is None or (isinstance(raw_worker, float) and np.isnan(raw_worker)) else str(raw_worker).strip()
        if val.lower() in {"", "nan", "none", "null", "unassigned", "na", "n/a"}:
            val = ""

        upper = val.upper()
        if val and ANON_WORKER_ID_RE.match(upper):
            return upper, False

        # Missing worker ID OR agency/department-level code (e.g. DPW, DDOT) -> deterministic DEPT-01..DEPT-12
        if not val or from_org_col:
            prefix = self._derive_dept_prefix(val, service_category)
            slot_seed = f"{self.salt}:{prefix}:{request_id}:{district_zone}"
            slot = (int(hashlib.sha256(slot_seed.encode("utf-8")).hexdigest()[:6], 16) % 12) + 1
            return f"{prefix}-{slot:02d}", True

        # Raw individual staff name/email/identifier -> 1-to-1 salted SHA-256 anonymized token
        prefix = self._derive_dept_prefix("", service_category)
        if prefix == "DEPT":
            prefix = "WRK"
        digest = hashlib.sha256(f"{self.salt}:{val}".encode("utf-8")).hexdigest()
        numeric_code = int(digest[:6], 16) % 900 + 100  # 100..999
        return f"{prefix}-{numeric_code:03d}", True

    @staticmethod
    def _normalize_status(raw_status: Any) -> str:
        val = "" if raw_status is None or (isinstance(raw_status, float) and np.isnan(raw_status)) else str(raw_status).strip()
        if not val or val.lower() in {"nan", "none", "null"}:
            return "In Progress"
        mapped = STATUS_NORMALIZATION_MAP.get(val.lower())
        return mapped if mapped else val.title()

    @staticmethod
    def _normalize_priority(raw_priority: Any) -> str:
        val = "" if raw_priority is None or (isinstance(raw_priority, float) and np.isnan(raw_priority)) else str(raw_priority).strip()
        if not val or val.lower() in {"nan", "none", "null"}:
            return "Medium"
        mapped = PRIORITY_NORMALIZATION_MAP.get(val.lower())
        return mapped if mapped else val.title()

    @staticmethod
    def _synthesize_action_taken(status: str, has_worker: bool, resolution_hours: float) -> str:
        if status == "Completed":
            return "Completed: Field inspection & resolution logged"
        if status == "On Hold":
            return "On Hold: Voided or pending administrative review"
        if status == "Escalated":
            return "Escalated: Priority crew dispatch required"
        if has_worker or resolution_hours >= 48.0:
            return "Assigned: Pending field verification"
        return "No action taken"

    def sanitize(self, raw_df: pd.DataFrame) -> tuple[pd.DataFrame, PIIAuditReceipt]:
        """Sanitize an uploaded or generated municipal dataset.

        Drops all citizen PII & free-text columns, scrubs residual inline PII
        from operational text, normalizes worker IDs to anonymized DEPT-NNN
        or DEPT-01..12 tokens, and verifies zero PII survival.
        """
        if raw_df is None or raw_df.empty:
            raise ValueError("Input dataset is empty; at least one municipal request record is required.")

        receipt = PIIAuditReceipt(
            input_rows=int(len(raw_df)),
            input_columns=[str(c) for c in raw_df.columns],
        )

        # 1. Column-level firewall with priority-ordered alias resolution
        allowed_targets = set(SAFE_OPERATIONAL_COLUMNS) | set(INTERNAL_DERIVATION_COLUMNS)
        candidates_by_norm: dict[str, list[tuple[str, str]]] = {}
        dropped_cols: list[str] = []

        for raw_col in raw_df.columns:
            raw_str = str(raw_col)
            clean_key = self._clean_col_key(raw_str)
            norm = COLUMN_ALIASES.get(clean_key, clean_key)
            if self._is_forbidden_column(raw_str, norm) or norm not in allowed_targets:
                dropped_cols.append(raw_str)
            else:
                candidates_by_norm.setdefault(norm, []).append((raw_str, clean_key))

        renamed_cols: dict[str, str] = {}
        worker_source_clean_key: str | None = None

        for norm, pairs in candidates_by_norm.items():
            priority_order = CANONICAL_ALIAS_PRIORITY.get(norm)
            if priority_order:
                pairs_sorted = sorted(
                    pairs,
                    key=lambda item: priority_order.index(item[1]) if item[1] in priority_order else len(priority_order),
                )
            else:
                pairs_sorted = pairs

            chosen_raw, chosen_clean = pairs_sorted[0]
            renamed_cols[chosen_raw] = norm
            if norm == "worker_id":
                worker_source_clean_key = chosen_clean
            for dup_raw, _ in pairs_sorted[1:]:
                dropped_cols.append(dup_raw)

        receipt.dropped_pii_columns = dropped_cols
        safe_df = raw_df[list(renamed_cols.keys())].rename(columns=renamed_cols).copy()

        # 2. Validate mandatory date column & fill missing optional operational columns
        if "created_at" not in safe_df.columns:
            raise ValueError("Dataset must contain a date/created_at column for time-period analysis.")
        if "request_id" not in safe_df.columns:
            safe_df["request_id"] = [f"REQ-{i + 1:05d}" for i in range(len(safe_df))]
        if "resolved_at" not in safe_df.columns:
            safe_df["resolved_at"] = ""
        if "service_category" not in safe_df.columns:
            safe_df["service_category"] = "General Municipal Services"
        if "priority" not in safe_df.columns:
            safe_df["priority"] = "Medium"
        if "status" not in safe_df.columns:
            safe_df["status"] = "Open"

        worker_col_present = "worker_id" in safe_df.columns
        if not worker_col_present:
            safe_df["worker_id"] = ""

        action_col_present = "action_taken" in safe_df.columns
        if not action_col_present:
            safe_df["action_taken"] = ""

        if "district_zone" not in safe_df.columns:
            safe_df["district_zone"] = "Zone-01"

        # 3. Parse timestamps (timezone-uniform UTC naive) and compute SLA & resolution hours
        safe_df["created_at"] = pd.to_datetime(safe_df["created_at"], errors="coerce", format="mixed", utc=True).dt.tz_localize(None)
        safe_df = safe_df.dropna(subset=["created_at"]).copy()
        if safe_df.empty:
            raise ValueError("No valid timestamps found in created_at column.")

        safe_df["resolved_dt"] = pd.to_datetime(safe_df["resolved_at"], errors="coerce", format="mixed", utc=True).dt.tz_localize(None)

        if "sla_target_hours" in safe_df.columns:
            safe_df["sla_target_hours"] = pd.to_numeric(safe_df["sla_target_hours"], errors="coerce").fillna(72.0)
        elif "sla_days" in safe_df.columns:
            safe_df["sla_target_hours"] = (pd.to_numeric(safe_df["sla_days"], errors="coerce").fillna(3.0) * 24.0)
        elif "due_at" in safe_df.columns:
            due_dt = pd.to_datetime(safe_df["due_at"], errors="coerce", format="mixed", utc=True).dt.tz_localize(None)
            due_hours = (due_dt - safe_df["created_at"]).dt.total_seconds() / 3600.0
            safe_df["sla_target_hours"] = np.where(due_hours.notna() & (due_hours > 0), due_hours, 72.0)
        else:
            safe_df["sla_target_hours"] = 72.0
        safe_df["sla_target_hours"] = np.clip(safe_df["sla_target_hours"].astype(float), 4.0, 720.0)

        if "resolution_hours" not in safe_df.columns:
            diff_hours = (safe_df["resolved_dt"] - safe_df["created_at"]).dt.total_seconds() / 3600.0
            max_resolved = safe_df["resolved_dt"].max()
            anchor = max(safe_df["created_at"].max(), max_resolved) if pd.notna(max_resolved) else safe_df["created_at"].max()
            open_hours = (anchor - safe_df["created_at"]).dt.total_seconds() / 3600.0
            safe_df["resolution_hours"] = np.where(diff_hours.notna() & (diff_hours >= 0), diff_hours, open_hours)
        else:
            safe_df["resolution_hours"] = pd.to_numeric(safe_df["resolution_hours"], errors="coerce").fillna(24.0)
        safe_df["resolution_hours"] = np.clip(safe_df["resolution_hours"].astype(float), 0.2, 2400.0)

        # 4. Normalize categorical fields (including DC 311 OPEN/CLOSED/VOID statuses)
        safe_df["service_category"] = (
            safe_df["service_category"].fillna("General Municipal Services").astype(str).str.strip()
        )
        safe_df["service_category"] = safe_df["service_category"].replace({"": "General Municipal Services", "nan": "General Municipal Services"})
        safe_df["priority"] = [self._normalize_priority(v) for v in safe_df["priority"].tolist()]
        safe_df["status"] = [self._normalize_status(v) for v in safe_df["status"].tolist()]

        cleaned_zones: list[str] = []
        for idx, z in enumerate(safe_df["district_zone"].tolist()):
            z_str = "" if z is None or (isinstance(z, float) and np.isnan(z)) else str(z).strip()
            if not z_str or z_str.lower() in {"nan", "none", "null"}:
                cleaned_zones.append("Zone-01")
            elif re.fullmatch(r"\d+(?:\.0+)?", z_str):
                cleaned_zones.append(f"Ward {int(float(z_str))}")
            else:
                cleaned_zones.append(z_str)
        safe_df["district_zone"] = cleaned_zones

        cleaned_req_ids: list[str] = []
        for idx, rid in enumerate(safe_df["request_id"].tolist()):
            r_str = "" if rid is None or (isinstance(rid, float) and np.isnan(rid)) else str(rid).strip()
            cleaned_req_ids.append(r_str if r_str and r_str.lower() not in {"nan", "none"} else f"REQ-{idx + 1:05d}")
        safe_df["request_id"] = cleaned_req_ids

        # 5. Scrub inline PII in action_taken, district_zone, request_id, and service_category
        raw_worker_list = safe_df["worker_id"].tolist()
        for text_col in ("action_taken", "district_zone", "request_id", "service_category"):
            cleaned_values: list[str] = []
            for idx, raw_val in enumerate(safe_df[text_col].tolist()):
                val_str = "" if raw_val is None or (isinstance(raw_val, float) and np.isnan(raw_val)) else str(raw_val).strip()
                if val_str.lower() in {"nan", "none", "null"}:
                    val_str = ""
                cleaned, counts = scrub_pii_text(val_str) if val_str else ("", {})
                for k, v in counts.items():
                    receipt.scrubbed_inline_pii[k] += v

                if text_col == "action_taken" and not cleaned:
                    raw_w_str = "" if raw_worker_list[idx] is None else str(raw_worker_list[idx]).strip()
                    has_w = bool(raw_w_str and raw_w_str.lower() not in {"nan", "none", "null", "unassigned", ""})
                    cleaned = self._synthesize_action_taken(
                        status=str(safe_df["status"].iloc[idx]),
                        has_worker=has_w,
                        resolution_hours=float(safe_df["resolution_hours"].iloc[idx]),
                    )
                elif not cleaned:
                    cleaned = "General Municipal Services" if text_col == "service_category" else "Standard Operational Record"

                cleaned_values.append(cleaned)
            safe_df[text_col] = cleaned_values

        # 6. Anonymize worker IDs strictly
        from_org_col = bool(worker_source_clean_key and worker_source_clean_key in ORG_LEVEL_WORKER_ALIASES)
        anon_workers: list[str] = []
        anonymized_count = 0
        for raw_w, cat, rid, zone in zip(
            raw_worker_list,
            safe_df["service_category"].tolist(),
            safe_df["request_id"].tolist(),
            safe_df["district_zone"].tolist(),
        ):
            anon_id, was_hashed = self._anonymize_worker_id(
                raw_w,
                cat,
                request_id=str(rid),
                district_zone=str(zone),
                from_org_col=from_org_col,
            )
            if was_hashed:
                anonymized_count += 1
            anon_workers.append(anon_id)
        safe_df["worker_id"] = anon_workers
        receipt.worker_ids_anonymized_count = anonymized_count

        # Keep only canonical columns
        final_cols = [c for c in SAFE_OPERATIONAL_COLUMNS if c in safe_df.columns]
        safe_df = safe_df[final_cols].copy()
        receipt.retained_safe_columns = final_cols
        receipt.total_inline_pii_scrubbed = sum(receipt.scrubbed_inline_pii.values())

        # 7. Post-shield verification sweep across all surviving string values
        leaks = 0
        for col in ("service_category", "priority", "status", "worker_id", "action_taken", "district_zone"):
            sample_concat = " | ".join(safe_df[col].astype(str).tolist())
            if scan_text_for_pii(sample_concat):
                leaks += 1
        receipt.post_shield_pii_leaks_detected = leaks
        receipt.shield_status = "VERIFIED_ZERO_PII" if leaks == 0 else "PII_WARNING"

        return safe_df.reset_index(drop=True), receipt


class WorkloadAnalyticsEngine:
    """Layer 3: Quantitative Pandas/NumPy Aggregation & Accountability Engine."""

    def analyze(
        self,
        safe_df: pd.DataFrame,
        granularity: str = "week",
        category_filter: str | None = None,
        status_filter: str | None = None,
        priority_filter: str | None = None,
    ) -> dict[str, Any]:
        """Compute KPIs, period trends, category breakdowns, and worker audit metrics."""
        if safe_df.empty:
            raise ValueError("Sanitized dataset contains zero rows.")

        df = safe_df.copy()

        # Capture available filter dimensions before slicing
        all_categories = sorted(df["service_category"].unique().tolist())
        all_statuses = sorted(df["status"].unique().tolist())
        all_priorities = sorted(df["priority"].unique().tolist())

        if category_filter and category_filter.lower() != "all":
            df = df[df["service_category"] == category_filter]
        if status_filter and status_filter.lower() != "all":
            df = df[df["status"] == status_filter]
        if priority_filter and priority_filter.lower() != "all":
            df = df[df["priority"] == priority_filter]

        if df.empty:
            return {
                "empty": True,
                "available_filters": {
                    "categories": all_categories,
                    "statuses": all_statuses,
                    "priorities": all_priorities,
                },
                "kpis": {
                    "total_requests": 0,
                    "completed_count": 0,
                    "remaining_count": 0,
                    "escalated_count": 0,
                    "overdue_remaining_count": 0,
                    "completion_rate_pct": 0.0,
                    "avg_resolution_hours": 0.0,
                    "median_resolution_hours": 0.0,
                    "p90_resolution_hours": 0.0,
                    "sla_compliance_pct": 0.0,
                    "sla_breach_count": 0,
                    "active_worker_count": 0,
                    "backlog_to_throughput_ratio": 0.0,
                    "date_range": {"start": "", "end": ""},
                },
                "time_series": [],
                "trend_metrics": {
                    "granularity": granularity,
                    "intake_slope_per_period": 0.0,
                    "backlog_slope_per_period": 0.0,
                    "projected_next_period_requests": 0,
                    "latest_volume_delta_pct": 0.0,
                },
                "categories": [],
                "status_breakdown": [],
                "priority_breakdown": [],
                "actions_rollup": [],
                "worker_audit": [],
            }

        df["created_at"] = pd.to_datetime(df["created_at"])
        status_lower = df["status"].str.lower()
        df["is_completed"] = status_lower.isin(COMPLETED_STATUSES)
        df["is_escalated"] = status_lower.isin(ESCALATED_STATUSES)
        df["sla_met"] = df["resolution_hours"] <= df["sla_target_hours"]
        df["is_overdue_open"] = (~df["is_completed"]) & (~df["sla_met"])

        total_requests = int(len(df))
        completed_count = int(df["is_completed"].sum())
        remaining_count = int(total_requests - completed_count)
        escalated_count = int(df["is_escalated"].sum())
        overdue_remaining_count = int(df["is_overdue_open"].sum())
        completion_rate = _safe_float((completed_count / total_requests) * 100.0) if total_requests else 0.0

        res_arr = df["resolution_hours"].to_numpy(dtype=float)
        completed_res_arr = df.loc[df["is_completed"], "resolution_hours"].to_numpy(dtype=float)
        eval_res_arr = completed_res_arr if len(completed_res_arr) > 0 else res_arr

        avg_res = _safe_float(np.mean(eval_res_arr))
        median_res = _safe_float(np.median(eval_res_arr))
        p90_res = _safe_float(np.percentile(eval_res_arr, 90))
        sla_compliance_pct = _safe_float(df["sla_met"].mean() * 100.0)
        sla_breach_count = int((~df["sla_met"]).sum())
        active_worker_count = int(df["worker_id"].nunique())

        # Period grouping (week or month)
        gran = "month" if str(granularity).lower() == "month" else "week"
        if gran == "month":
            df["period"] = df["created_at"].dt.strftime("%Y-%m")
        else:
            # ISO week start (Monday)
            week_start = df["created_at"] - pd.to_timedelta(df["created_at"].dt.day_of_week, unit="D")
            df["period"] = week_start.dt.strftime("%Y-%m-%d")

        period_grouped = (
            df.groupby("period", as_index=False)
            .agg(
                total_requests=("request_id", "count"),
                completed=("is_completed", "sum"),
                escalated=("is_escalated", "sum"),
                avg_resolution_hours=("resolution_hours", "mean"),
                sla_compliance_pct=("sla_met", "mean"),
            )
            .sort_values("period")
            .reset_index(drop=True)
        )
        period_grouped["remaining"] = period_grouped["total_requests"] - period_grouped["completed"]
        period_grouped["cumulative_backlog"] = period_grouped["remaining"].cumsum()

        time_series: list[dict[str, Any]] = []
        for _, row in period_grouped.iterrows():
            tot = int(row["total_requests"])
            comp = int(row["completed"])
            rem = int(row["remaining"])
            time_series.append(
                {
                    "period": str(row["period"]),
                    "total_requests": tot,
                    "completed": comp,
                    "remaining": rem,
                    "escalated": int(row["escalated"]),
                    "completion_rate_pct": _safe_float((comp / tot) * 100.0) if tot else 0.0,
                    "avg_resolution_hours": _safe_float(row["avg_resolution_hours"]),
                    "sla_compliance_pct": _safe_float(row["sla_compliance_pct"] * 100.0),
                    "cumulative_backlog": int(row["cumulative_backlog"]),
                }
            )

        # NumPy linear trend analysis on period series
        intake_vals = period_grouped["total_requests"].to_numpy(dtype=float)
        rem_vals = period_grouped["remaining"].to_numpy(dtype=float)
        if len(intake_vals) >= 2:
            x = np.arange(len(intake_vals), dtype=float)
            intake_slope = _safe_float(np.polyfit(x, intake_vals, 1)[0])
            backlog_slope = _safe_float(np.polyfit(x, rem_vals, 1)[0])
            projected_next = max(0, _safe_int(np.polyval(np.polyfit(x, intake_vals, 1), len(intake_vals))))
            prev_vol = float(intake_vals[-2])
            curr_vol = float(intake_vals[-1])
            latest_delta_pct = _safe_float(((curr_vol - prev_vol) / prev_vol) * 100.0) if prev_vol > 0 else 0.0
        else:
            intake_slope = 0.0
            backlog_slope = 0.0
            projected_next = int(intake_vals[-1]) if len(intake_vals) == 1 else 0
            latest_delta_pct = 0.0

        avg_completed_per_period = float(np.mean(period_grouped["completed"].to_numpy(dtype=float))) if len(period_grouped) else 1.0
        backlog_to_throughput_ratio = _safe_float(remaining_count / max(avg_completed_per_period, 1.0))

        # Service Category aggregation
        categories_list: list[dict[str, Any]] = []
        for cat_name, cat_df in df.groupby("service_category"):
            tot = int(len(cat_df))
            comp = int(cat_df["is_completed"].sum())
            rem = int(tot - comp)
            top_acts = [
                {"action": str(act), "count": int(cnt)}
                for act, cnt in cat_df["action_taken"].value_counts().head(3).items()
            ]
            crit_high = int(cat_df["priority"].isin(["Critical", "High"]).sum())
            categories_list.append(
                {
                    "service_category": str(cat_name),
                    "total_requests": tot,
                    "completed": comp,
                    "remaining": rem,
                    "completion_rate_pct": _safe_float((comp / tot) * 100.0) if tot else 0.0,
                    "avg_resolution_hours": _safe_float(cat_df["resolution_hours"].mean()),
                    "sla_target_avg_hours": _safe_float(cat_df["sla_target_hours"].mean()),
                    "sla_compliance_pct": _safe_float(cat_df["sla_met"].mean() * 100.0),
                    "critical_high_count": crit_high,
                    "top_actions": top_acts,
                }
            )
        categories_list.sort(key=lambda item: item["total_requests"], reverse=True)

        # Status & Priority breakdowns
        status_breakdown = [
            {
                "status": str(st),
                "count": int(cnt),
                "pct": _safe_float((cnt / total_requests) * 100.0),
            }
            for st, cnt in df["status"].value_counts().items()
        ]
        priority_breakdown = [
            {
                "priority": str(pr),
                "count": int(cnt),
                "pct": _safe_float((cnt / total_requests) * 100.0),
            }
            for pr, cnt in df["priority"].value_counts().items()
        ]

        # Actions Taken rollup
        actions_rollup: list[dict[str, Any]] = []
        for act_name, act_df in df.groupby("action_taken"):
            tot = int(len(act_df))
            comp = int(act_df["is_completed"].sum())
            actions_rollup.append(
                {
                    "action_taken": str(act_name),
                    "count": tot,
                    "completed": comp,
                    "remaining": int(tot - comp),
                    "completion_rate_pct": _safe_float((comp / tot) * 100.0) if tot else 0.0,
                }
            )
        actions_rollup.sort(key=lambda item: item["count"], reverse=True)
        actions_rollup = actions_rollup[:15]

        # Worker Accountability & Actions Audit (strictly anonymized worker IDs)
        worker_rows: list[dict[str, Any]] = []
        worker_groups = list(df.groupby("worker_id"))
        assigned_counts = np.array([len(g) for _, g in worker_groups], dtype=float)
        mean_assigned = float(np.mean(assigned_counts)) if len(assigned_counts) > 0 else 0.0
        std_assigned = float(np.std(assigned_counts)) if len(assigned_counts) > 1 else 0.0

        for worker_id, w_df in worker_groups:
            assigned = int(len(w_df))
            comp = int(w_df["is_completed"].sum())
            rem = int(assigned - comp)
            esc = int(w_df["is_escalated"].sum())
            comp_pct = _safe_float((comp / assigned) * 100.0) if assigned else 0.0
            avg_hrs = _safe_float(w_df["resolution_hours"].mean())
            sla_pct = _safe_float(w_df["sla_met"].mean() * 100.0)
            primary_cat = str(w_df["service_category"].mode().iloc[0])
            z_score = _safe_float((assigned - mean_assigned) / std_assigned) if std_assigned > 0 else 0.0

            actions_summary = [
                {"action": str(act), "count": int(cnt)}
                for act, cnt in w_df["action_taken"].value_counts().head(4).items()
            ]

            if (rem >= 8 and comp_pct < 68.0) or (z_score >= 1.1 and sla_pct < 68.0):
                flag = "Overloaded / Bottleneck"
            elif sla_pct < 68.0 or comp_pct < 65.0:
                flag = "SLA Watch"
            elif comp_pct >= 88.0 and sla_pct >= 82.0:
                flag = "Top Performer"
            else:
                flag = "On Track"

            worker_rows.append(
                {
                    "worker_id": str(worker_id),
                    "primary_category": primary_cat,
                    "assigned_count": assigned,
                    "completed_count": comp,
                    "remaining_count": rem,
                    "escalated_count": esc,
                    "completion_rate_pct": comp_pct,
                    "avg_resolution_hours": avg_hrs,
                    "sla_compliance_pct": sla_pct,
                    "workload_z_score": z_score,
                    "accountability_flag": flag,
                    "actions_summary": actions_summary,
                    "primary_action": actions_summary[0]["action"] if actions_summary else "Standard Processing",
                }
            )

        # Sort bottlenecks & high-workload workers cleanly (remaining desc, then assigned desc)
        worker_rows.sort(key=lambda w: (w["remaining_count"], w["assigned_count"]), reverse=True)

        return {
            "empty": False,
            "available_filters": {
                "categories": all_categories,
                "statuses": all_statuses,
                "priorities": all_priorities,
            },
            "kpis": {
                "total_requests": total_requests,
                "completed_count": completed_count,
                "remaining_count": remaining_count,
                "escalated_count": escalated_count,
                "overdue_remaining_count": overdue_remaining_count,
                "completion_rate_pct": completion_rate,
                "avg_resolution_hours": avg_res,
                "median_resolution_hours": median_res,
                "p90_resolution_hours": p90_res,
                "sla_compliance_pct": sla_compliance_pct,
                "sla_breach_count": sla_breach_count,
                "active_worker_count": active_worker_count,
                "backlog_to_throughput_ratio": backlog_to_throughput_ratio,
                "date_range": {
                    "start": df["created_at"].min().strftime("%Y-%m-%d"),
                    "end": df["created_at"].max().strftime("%Y-%m-%d"),
                },
            },
            "time_series": time_series,
            "trend_metrics": {
                "granularity": gran,
                "period_count": len(time_series),
                "intake_slope_per_period": intake_slope,
                "backlog_slope_per_period": backlog_slope,
                "projected_next_period_requests": projected_next,
                "latest_volume_delta_pct": latest_delta_pct,
            },
            "categories": categories_list,
            "status_breakdown": status_breakdown,
            "priority_breakdown": priority_breakdown,
            "actions_rollup": actions_rollup,
            "worker_audit": worker_rows,
        }
