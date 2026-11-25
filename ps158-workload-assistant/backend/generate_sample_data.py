"""Synthetic municipal public service request generator (Layer 1 test/demo dataset).

Generates 500+ realistic municipal service records spanning multiple months and
service categories, using anonymized worker IDs (e.g., ENG-042, SAN-108).
Optionally includes synthetic placeholder citizen PII columns and edge-case
inline PII strings so Layer 2 (PII Shield) can actively demonstrate column-level
dropping and inline regex redaction before any record reaches Layer 3 or Layer 4.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

SERVICE_CATEGORIES: dict[str, dict[str, Any]] = {
    "Roads & Infrastructure": {
        "prefix": "ENG",
        "sla_hours": 72,
        "base_weight": 0.24,
        "workers": ["ENG-042", "ENG-071", "ENG-104", "ENG-118", "ENG-156"],
        "actions": [
            "Resurfaced Roadway Patch",
            "Cleared Storm Drain Culvert",
            "Repaired Sidewalk Curb",
            "Placed Hazard Barricades",
            "Escalated to Structural Engineering",
            "Awaiting Asphalt Crew Dispatch",
        ],
    },
    "Sanitation & Waste": {
        "prefix": "SAN",
        "sla_hours": 36,
        "base_weight": 0.22,
        "workers": ["SAN-108", "SAN-112", "SAN-145", "SAN-189", "SAN-203"],
        "actions": [
            "Completed Bulk Waste Pickup",
            "Cleared Illegal Dumping Site",
            "Replaced Damaged Receptacle",
            "Sanitized Alleyway Corridor",
            "Dispatched Overflow Route Truck",
            "Pending Roll-Off Container",
        ],
    },
    "Water & Sewer": {
        "prefix": "WTR",
        "sla_hours": 24,
        "base_weight": 0.18,
        "workers": ["WTR-019", "WTR-034", "WTR-052", "WTR-088"],
        "actions": [
            "Isolated & Repaired Main Leak",
            "Flushed Fire Hydrant Line",
            "Cleared Sewer Lateral Blockage",
            "Replaced Meter Vault Valve",
            "Escalated to Pump Station Team",
            "Awaiting Excavation Clearance",
        ],
    },
    "Street Lighting & Power": {
        "prefix": "ELC",
        "sla_hours": 48,
        "base_weight": 0.14,
        "workers": ["ELC-027", "ELC-063", "ELC-091"],
        "actions": [
            "Replaced LED Luminaire Ballast",
            "Restored Underground Conduit Feed",
            "Reset Traffic Signal Controller",
            "Tested Photocell Relay",
            "Awaiting Utility Pole Parts",
        ],
    },
    "Parks & Public Spaces": {
        "prefix": "PRK",
        "sla_hours": 96,
        "base_weight": 0.12,
        "workers": ["PRK-015", "PRK-049", "PRK-077"],
        "actions": [
            "Removed Fallen Tree Limb",
            "Repaired Playground Fixture",
            "Mowed & Cleared Sightline",
            "Restored Park Irrigation Valve",
            "Scheduled Forestry Crew",
        ],
    },
    "Code Enforcement & Permits": {
        "prefix": "COD",
        "sla_hours": 120,
        "base_weight": 0.10,
        "workers": ["COD-031", "COD-066", "COD-094"],
        "actions": [
            "Conducted Site Compliance Audit",
            "Issued Administrative Notice",
            "Verified Remediation Photos",
            "Closed Permit Inspection",
            "Scheduled Follow-Up Inspection",
        ],
    },
}

WORKER_PROFILES: dict[str, dict[str, float]] = {
    # High performers
    "ENG-042": {"completion_bias": 0.94, "speed_mult": 0.72, "load_mult": 1.25},
    "SAN-108": {"completion_bias": 0.95, "speed_mult": 0.68, "load_mult": 1.30},
    "WTR-019": {"completion_bias": 0.92, "speed_mult": 0.75, "load_mult": 1.15},
    "ELC-027": {"completion_bias": 0.91, "speed_mult": 0.80, "load_mult": 1.00},
    "PRK-015": {"completion_bias": 0.93, "speed_mult": 0.78, "load_mult": 1.05},
    "COD-031": {"completion_bias": 0.90, "speed_mult": 0.82, "load_mult": 1.00},
    # Overloaded / bottlenecked personnel
    "ENG-156": {"completion_bias": 0.56, "speed_mult": 1.55, "load_mult": 1.55},
    "WTR-088": {"completion_bias": 0.58, "speed_mult": 1.62, "load_mult": 1.45},
    "SAN-203": {"completion_bias": 0.62, "speed_mult": 1.48, "load_mult": 1.40},
    "ELC-091": {"completion_bias": 0.61, "speed_mult": 1.42, "load_mult": 1.20},
}

PRIORITIES = ["Critical", "High", "Medium", "Low"]
PRIORITY_WEIGHTS = [0.10, 0.28, 0.44, 0.18]
DISTRICT_ZONES = [
    "Zone-01 North",
    "Zone-02 Central",
    "Zone-03 East",
    "Zone-04 West",
    "Zone-05 South",
    "Zone-06 Harbor",
]

# Synthetic placeholder tokens solely to exercise Layer 2 PII Shield redaction
_FAKE_FIRST = ["Jordan", "Taylor", "Morgan", "Casey", "Riley", "Avery", "Quinn", "Skyler"]
_FAKE_LAST = ["Miller", "Patel", "Garcia", "Chen", "Brooks", "Kim", "Diaz", "Nguyen"]
_FAKE_STREETS = ["Oak Ridge Ave", "Maple Crest Rd", "Cedar Park Blvd", "Pine Valley St", "Riverfront Ln"]


def generate_synthetic_dataset(
    num_rows: int = 640,
    seed: int = 158,
    include_simulated_pii: bool = True,
    end_date: datetime | None = None,
) -> pd.DataFrame:
    """Generate a synthetic municipal service request dataset.

    Args:
        num_rows: Number of service requests to generate (minimum 500 recommended).
        seed: Deterministic RNG seed for reproducibility.
        include_simulated_pii: When True, includes synthetic citizen PII columns
            and occasional inline PII patterns in operational fields so Layer 2
            PII Shield scrubbing can be visibly audited.
        end_date: Anchor end timestamp (defaults to 2026-11-24T18:00:00).

    Returns:
        pandas.DataFrame of raw municipal service requests.
    """
    rng = np.random.default_rng(seed)
    anchor_end = end_date or datetime(2026, 11, 24, 18, 0, 0)
    span_days = 168  # 24 weeks (~6 months)

    categories = list(SERVICE_CATEGORIES.keys())
    cat_weights = np.array([SERVICE_CATEGORIES[c]["base_weight"] for c in categories])
    cat_weights = cat_weights / cat_weights.sum()

    rows: list[dict[str, Any]] = []
    for idx in range(num_rows):
        # Recent weeks receive slightly higher volume to reflect seasonal surge
        u = float(rng.beta(1.25, 0.92))
        days_ago = int(round((1.0 - u) * span_days))
        hour = int(rng.integers(7, 20))
        minute = int(rng.integers(0, 60))
        created_dt = anchor_end - timedelta(days=days_ago, hours=(18 - hour), minutes=minute)

        category = str(rng.choice(categories, p=cat_weights))
        cat_meta = SERVICE_CATEGORIES[category]
        workers = cat_meta["workers"]

        worker_weights = np.array(
            [WORKER_PROFILES.get(w, {}).get("load_mult", 1.0) for w in workers],
            dtype=float,
        )
        worker_weights /= worker_weights.sum()
        worker_id = str(rng.choice(workers, p=worker_weights))

        profile = WORKER_PROFILES.get(worker_id, {"completion_bias": 0.80, "speed_mult": 1.0})
        priority = str(rng.choice(PRIORITIES, p=PRIORITY_WEIGHTS))
        sla_base = float(cat_meta["sla_hours"])
        priority_sla_factor = {"Critical": 0.35, "High": 0.65, "Medium": 1.0, "Low": 1.4}[priority]
        sla_target_hours = round(max(6.0, sla_base * priority_sla_factor), 1)

        # Older requests have higher probability of closure; very recent ones stay open/in-progress
        recency_penalty = 0.42 if days_ago <= 10 else (0.18 if days_ago <= 24 else 0.0)
        p_complete = float(np.clip(profile["completion_bias"] - recency_penalty, 0.18, 0.97))

        roll = float(rng.random())
        if roll < p_complete:
            status = "Completed"
            action_choices = cat_meta["actions"][:-2]
            action_taken = str(rng.choice(action_choices))
            speed_noise = float(rng.lognormal(mean=0.0, sigma=0.45))
            res_hours = round(
                float(np.clip(sla_target_hours * 0.62 * profile["speed_mult"] * speed_noise, 1.2, sla_target_hours * 2.4)),
                1,
            )
            resolved_dt = created_dt + timedelta(hours=res_hours)
            if resolved_dt > anchor_end:
                resolved_dt = anchor_end - timedelta(minutes=int(rng.integers(15, 180)))
                res_hours = round(max(0.5, (resolved_dt - created_dt).total_seconds() / 3600.0), 1)
            resolved_str = resolved_dt.strftime("%Y-%m-%d %H:%M:%S")
        else:
            age_hours = max(1.0, (anchor_end - created_dt).total_seconds() / 3600.0)
            res_hours = round(age_hours, 1)
            resolved_str = ""
            if age_hours > sla_target_hours * 1.15 or priority == "Critical":
                status = str(rng.choice(["Escalated", "In Progress"], p=[0.48, 0.52]))
                action_taken = str(rng.choice(cat_meta["actions"][-3:]))
            else:
                status = str(rng.choice(["In Progress", "Open"], p=[0.58, 0.42]))
                action_taken = str(rng.choice(cat_meta["actions"][-2:]))

        # Inject occasional inline PII into operational text on ~6% of rows to test Layer 2 scrubber
        if include_simulated_pii and float(rng.random()) < 0.06:
            leak_kind = int(rng.integers(0, 3))
            if leak_kind == 0:
                action_taken = f"{action_taken} (callback 555-{int(rng.integers(200, 999))}-{int(rng.integers(1000, 9999))})"
            elif leak_kind == 1:
                fn = _FAKE_FIRST[int(rng.integers(0, len(_FAKE_FIRST)))]
                action_taken = f"{action_taken} - notify {fn.lower()}.citizen@example.org"
            else:
                st = _FAKE_STREETS[int(rng.integers(0, len(_FAKE_STREETS)))]
                action_taken = f"{action_taken} near {int(rng.integers(100, 999))} {st}"

        row: dict[str, Any] = {
            "request_id": f"REQ-2026-{idx + 1:04d}",
            "created_at": created_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "resolved_at": resolved_str,
            "service_category": category,
            "priority": priority,
            "status": status,
            "worker_id": worker_id,
            "action_taken": action_taken,
            "sla_target_hours": sla_target_hours,
            "resolution_hours": res_hours,
            "district_zone": str(rng.choice(DISTRICT_ZONES)),
        }

        if include_simulated_pii:
            first = _FAKE_FIRST[int(rng.integers(0, len(_FAKE_FIRST)))]
            last = _FAKE_LAST[int(rng.integers(0, len(_FAKE_LAST)))]
            street = _FAKE_STREETS[int(rng.integers(0, len(_FAKE_STREETS)))]
            house_num = int(rng.integers(101, 8999))
            row.update(
                {
                    "citizen_name": f"{first} {last}",
                    "citizen_phone": f"555-{int(rng.integers(200, 999))}-{int(rng.integers(1000, 9999))}",
                    "citizen_email": f"{first.lower()}.{last.lower()}{idx}@example.com",
                    "street_address": f"{house_num} {street}",
                    "free_text_complaint": (
                        f"Resident {first} {last} at {house_num} {street} reported urgent {category.lower()} "
                        f"disruption outside unit #{int(rng.integers(1, 20))}; requested call on 555-0199."
                    ),
                }
            )

        rows.append(row)

    df = pd.DataFrame(rows)
    df = df.sort_values("created_at").reset_index(drop=True)
    return df


def save_sample_csv(output_path: Path | None = None, num_rows: int = 640) -> Path:
    """Persist the synthetic sample dataset CSV to disk and return its path."""
    target = output_path or (Path(__file__).resolve().parent / "sample_data" / "municipal_service_requests.csv")
    target.parent.mkdir(parents=True, exist_ok=True)
    df = generate_synthetic_dataset(num_rows=num_rows, include_simulated_pii=True)
    df.to_csv(target, index=False)
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic PS 158 municipal workload dataset.")
    parser.add_argument("--rows", type=int, default=640, help="Number of rows to generate (default: 640)")
    parser.add_argument("--output", type=Path, default=None, help="Output CSV path")
    args = parser.parse_args()
    path = save_sample_csv(output_path=args.output, num_rows=max(500, args.rows))
    print(f"Generated {max(500, args.rows)} synthetic service request rows -> {path}")

