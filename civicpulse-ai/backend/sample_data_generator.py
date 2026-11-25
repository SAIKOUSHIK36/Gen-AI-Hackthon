"""Synthetic anonymized complaint dataset generator for CivicPulse AI."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

DEPARTMENT_CATALOG: dict[str, dict[str, Any]] = {
    "Water Dept": {
        "categories": ["Water Leakage", "Water Supply", "Pipeline Burst", "Contaminated Supply"],
        "teams": ["WTR-Team-A", "WTR-Team-B", "WTR-Team-C"],
        "sla_days": 4,
        "weight": 0.23,
        "resolve_prob": 0.68,
        "reasons": [
            "Awaiting materials",
            "Staff unavailable",
            "Awaiting inspection",
            "Equipment unavailable",
            "Technical difficulties",
        ],
    },
    "Roads Dept": {
        "categories": ["Road Damage", "Pothole Repair", "Sidewalk Collapse", "Bridge Surface"],
        "teams": ["RDS-Team-01", "RDS-Team-02", "RDS-Team-03"],
        "sla_days": 8,
        "weight": 0.25,
        "resolve_prob": 0.56,  # Intentional backlog + material shortage signal
        "reasons": [
            "Awaiting materials",
            "Contractor-related delays",
            "Equipment unavailable",
            "Delay in department approval",
            "High complaint workload",
        ],
    },
    "Electricity Dept": {
        "categories": ["Electricity", "Streetlight Outage", "Transformer Fault", "Downed Wire"],
        "teams": ["ELC-Team-A", "ELC-Team-B"],
        "sla_days": 3,
        "weight": 0.18,
        "resolve_prob": 0.72,
        "reasons": [
            "Staff unavailable",
            "Awaiting materials",
            "Technical difficulties",
            "Poor coordination between departments",
        ],
    },
    "Municipal Dept": {
        "categories": ["Drainage", "Garbage Overflow", "Storm Drain Blockage", "Sanitation"],
        "teams": ["MUN-Team-01", "MUN-Team-02", "MUN-Team-03"],
        "sla_days": 5,
        "weight": 0.20,
        "resolve_prob": 0.77,
        "reasons": [
            "Equipment unavailable",
            "High complaint workload",
            "Awaiting inspection",
            "Poor coordination between departments",
        ],
    },
    "Permits & Enforcement": {
        "categories": ["Illegal Construction", "Zoning Violation", "Noise Permit", "Encroachment"],
        "teams": ["ENF-Team-A", "ENF-Team-B"],
        "sla_days": 10,
        "weight": 0.14,
        "resolve_prob": 0.79,
        "reasons": [
            "Delay in department approval",
            "Awaiting inspection",
            "Staff unavailable",
        ],
    },
}

PRIORITIES = ["Critical", "High", "Medium", "Low"]
PRIORITY_WEIGHTS = [0.12, 0.28, 0.44, 0.16]


def generate_complaint_dataset(
    num_rows: int = 620,
    seed: int = 2026,
    include_simulated_pii: bool = False,
    anchor_date: datetime | None = None,
) -> pd.DataFrame:
    """Generate a realistic synthetic public complaint dataset matching CivicPulse schema."""
    rng = np.random.default_rng(seed)
    now = anchor_date or datetime(2026, 11, 24, 16, 0, 0)
    span_days = 150

    depts = list(DEPARTMENT_CATALOG.keys())
    dept_weights = np.array([DEPARTMENT_CATALOG[d]["weight"] for d in depts], dtype=float)
    dept_weights /= dept_weights.sum()

    rows: list[dict[str, Any]] = []
    for idx in range(num_rows):
        # Create an intentional volume spike around days 18..26 ago so Isolation Forest detects it
        if idx % 14 == 0:
            days_ago = int(rng.integers(18, 25))
        else:
            u = float(rng.beta(1.2, 0.95))
            days_ago = int(round((1.0 - u) * span_days))

        date_received = (now - timedelta(days=days_ago)).replace(
            hour=int(rng.integers(8, 19)),
            minute=int(rng.integers(0, 60)),
            second=0,
        )

        dept = str(rng.choice(depts, p=dept_weights))
        meta = DEPARTMENT_CATALOG[dept]
        category = str(rng.choice(meta["categories"]))
        team = str(rng.choice(meta["teams"]))
        priority = str(rng.choice(PRIORITIES, p=PRIORITY_WEIGHTS))

        sla_mult = {"Critical": 0.5, "High": 0.75, "Medium": 1.0, "Low": 1.35}[priority]
        sla_days = max(2, int(round(meta["sla_days"] * sla_mult)))
        deadline = date_received + timedelta(days=sla_days)

        # Older complaints resolve more often; recent ones stay Pending/In Progress
        recency_penalty = 0.40 if days_ago <= 8 else (0.16 if days_ago <= 18 else 0.0)
        p_resolve = float(np.clip(meta["resolve_prob"] - recency_penalty, 0.22, 0.92))

        roll = float(rng.random())
        if roll < p_resolve:
            status = "Resolved"
            delay_factor = float(rng.lognormal(mean=-0.2, sigma=0.55))
            res_days = max(1, int(round(sla_days * delay_factor)))
            resolution_dt = min(now, date_received + timedelta(days=res_days))
            resolution_str = resolution_dt.strftime("%Y-%m-%d")
            last_updated = resolution_dt
            # Occasionally resolved late with recorded delay reason
            if resolution_dt > deadline and float(rng.random()) < 0.65:
                delay_reason = str(rng.choice(meta["reasons"]))
            else:
                delay_reason = "None"
        elif roll < p_resolve + 0.04:
            status = "Rejected"
            resolution_dt = min(now, date_received + timedelta(days=int(rng.integers(1, 5))))
            resolution_str = resolution_dt.strftime("%Y-%m-%d")
            last_updated = resolution_dt
            delay_reason = "None"
        else:
            resolution_str = ""
            is_past_deadline = now > deadline
            if is_past_deadline and float(rng.random()) < 0.35:
                status = "Overdue"
            elif float(rng.random()) < 0.45:
                status = "In Progress"
            else:
                status = "Pending"

            # Stale update simulation on severely delayed tickets
            if is_past_deadline and float(rng.random()) < 0.55:
                stale_days = int(rng.integers(4, max(5, min(20, days_ago + 1))))
                last_updated = max(date_received, now - timedelta(days=stale_days))
            else:
                last_updated = max(date_received, now - timedelta(days=int(rng.integers(0, 4))))

            # Recorded Delay_Reason present on ~74% of delayed/pending rows, omitted on ~26%
            # so UI clearly distinguishes Recorded Reasons vs Inferred Patterns vs Insufficient Evidence!
            if is_past_deadline:
                if dept == "Roads Dept" and float(rng.random()) < 0.52:
                    delay_reason = "Awaiting materials"
                elif float(rng.random()) < 0.76:
                    delay_reason = str(rng.choice(meta["reasons"]))
                else:
                    delay_reason = ""  # Deliberately blank to exercise inferred/insufficient logic
            else:
                delay_reason = str(rng.choice(meta["reasons"])) if float(rng.random()) < 0.42 else ""

        row: dict[str, Any] = {
            "Complaint_ID": f"C{idx + 1:04d}",
            "Category": category,
            "Department": dept,
            "Date_Received": date_received.strftime("%Y-%m-%d"),
            "Status": status,
            "Deadline": deadline.strftime("%Y-%m-%d"),
            "Resolution_Date": resolution_str,
            "Assigned_Department": dept,
            "Assigned_Team": team,
            "Priority": priority,
            "Delay_Reason": delay_reason,
            "Last_Updated_Date": last_updated.strftime("%Y-%m-%d"),
        }

        if include_simulated_pii:
            row["Citizen_Name"] = f"Sample Citizen {idx + 1}"
            row["Citizen_Phone"] = f"555-01{(idx % 90) + 10:02d}"
            row["Citizen_Email"] = f"resident{idx + 1}@example.org"
            row["Street_Address"] = f"{100 + idx} Sample Oak Street"

        rows.append(row)

    df = pd.DataFrame(rows).sort_values("Date_Received").reset_index(drop=True)
    return df


def save_sample_csv(output_path: Path | None = None, num_rows: int = 620) -> Path:
    target = output_path or (Path(__file__).resolve().parent / "sample_data" / "civicpulse_complaints_sample.csv")
    target.parent.mkdir(parents=True, exist_ok=True)
    df = generate_complaint_dataset(num_rows=num_rows, include_simulated_pii=False)
    df.to_csv(target, index=False)
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic CivicPulse AI complaint dataset.")
    parser.add_argument("--rows", type=int, default=620)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    out = save_sample_csv(output_path=args.output, num_rows=args.rows)
    print(f"Generated {args.rows} synthetic complaint rows -> {out}")

