"""Layer 3: Quantitative Analytics, Rule-Based Delay Detection & Scikit-learn Isolation Forest Engine."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

INSUFFICIENT_EVIDENCE_MSG = "Reason not available – further investigation required."

CANONICAL_DELAY_REASONS: list[tuple[tuple[str, ...], str]] = [
    (("staff", "shortage of staff", "manpower", "personnel", "crew"), "Shortage of staff"),
    (("material", "parts", "supply", "supplies", "inventory"), "Lack of required materials"),
    (("approval", "permit", "budget", "authorization", "sign-off"), "Delay in department approval"),
    (("equipment", "machinery", "vehicle", "truck", "crane", "tool"), "Equipment or machinery unavailability"),
    (("inspection", "site visit", "survey", "assessment"), "Pending field inspection"),
    (("coordination", "inter-department", "utility", "external"), "Poor coordination between departments"),
    (("workload", "backlog", "volume", "overload", "capacity"), "High complaint workload"),
    (("technical", "complex", "engineering", "underground", "fault"), "Technical difficulties"),
    (("contractor", "vendor", "third-party", "subcontractor"), "Contractor-related delays"),
]

PRIORITY_SCORE_MAP = {"Critical": 4.0, "High": 3.0, "Medium": 2.0, "Low": 1.0}


def _sf(val: Any, default: float = 0.0) -> float:
    try:
        f = float(val)
        return round(f, 2) if np.isfinite(f) else default
    except (TypeError, ValueError):
        return default


def categorize_recorded_delay_reason(raw_reason: str) -> str:
    txt = (raw_reason or "").strip()
    if not txt:
        return ""
    low = txt.lower()
    for keywords, canonical in CANONICAL_DELAY_REASONS:
        if any(kw in low for kw in keywords):
            return canonical
    return f"Other recorded reason: {txt}"


class CivicPulseAnalyticsEngine:
    """Computes KPIs, Resolution Analysis, Delay Detection, Department Intelligence, and ML Anomalies."""

    def analyze(
        self,
        safe_df: pd.DataFrame,
        department_filter: str | None = None,
        category_filter: str | None = None,
        status_filter: str | None = None,
        priority_filter: str | None = None,
        granularity: str = "week",
    ) -> dict[str, Any]:
        if safe_df.empty:
            raise ValueError("Sanitized dataset contains zero rows.")

        df = safe_df.copy()
        all_departments = sorted(df["Department"].unique().tolist())
        all_categories = sorted(df["Category"].unique().tolist())
        all_statuses = sorted(df["Status"].unique().tolist())
        all_priorities = sorted(df["Priority"].unique().tolist())

        # Reference anchor date for deterministic pending/overdue calculation
        max_received = df["Date_Received"].max()
        max_resolved = df["Resolution_Date"].dropna().max() if df["Resolution_Date"].notna().any() else max_received
        max_updated = df["Last_Updated_Date"].dropna().max() if df["Last_Updated_Date"].notna().any() else max_received
        reference_date = max(max_received, max_resolved, max_updated)

        if department_filter and department_filter.lower() != "all":
            df = df[df["Department"] == department_filter]
        if category_filter and category_filter.lower() != "all":
            df = df[df["Category"] == category_filter]
        if status_filter and status_filter.lower() != "all":
            df = df[df["Status"] == status_filter]
        if priority_filter and priority_filter.lower() != "all":
            df = df[df["Priority"] == priority_filter]

        if df.empty:
            return {
                "empty": True,
                "available_filters": {
                    "departments": all_departments,
                    "categories": all_categories,
                    "statuses": all_statuses,
                    "priorities": all_priorities,
                },
                "reference_date": reference_date.strftime("%Y-%m-%d"),
            }

        # Core row-level rule calculations
        df["is_resolved"] = df["Status"] == "Resolved"
        df["is_rejected"] = df["Status"] == "Rejected"
        df["is_unresolved"] = ~(df["is_resolved"] | df["is_rejected"])

        # Days pending (unresolved -> reference_date - Date_Received; resolved -> Resolution_Date - Date_Received)
        resolved_days = (df["Resolution_Date"] - df["Date_Received"]).dt.total_seconds() / 86400.0
        open_days = (reference_date - df["Date_Received"]).dt.total_seconds() / 86400.0
        df["resolution_days"] = np.where(df["is_resolved"] & resolved_days.notna(), np.maximum(0.5, resolved_days), np.nan)
        df["days_pending"] = np.where(df["is_unresolved"], np.maximum(0.0, open_days), 0.0)

        # Deadline crossing & days overdue
        overdue_open_days = (reference_date - df["Deadline"]).dt.total_seconds() / 86400.0
        overdue_resolved_days = (df["Resolution_Date"] - df["Deadline"]).dt.total_seconds() / 86400.0
        df["is_overdue"] = df["is_unresolved"] & ((df["Status"] == "Overdue") | (reference_date > df["Deadline"]))
        df["days_overdue"] = np.where(
            df["is_overdue"],
            np.maximum(0.5, overdue_open_days),
            np.where(df["is_resolved"] & (overdue_resolved_days > 0), overdue_resolved_days, 0.0),
        )
        df["days_since_update"] = np.maximum(
            0.0,
            (reference_date - df["Last_Updated_Date"]).dt.total_seconds() / 86400.0,
        )
        df["recorded_reason_norm"] = [categorize_recorded_delay_reason(r) for r in df["Delay_Reason"].tolist()]

        # 1. Overview KPIs & Resolution Counts
        total = int(len(df))
        resolved_count = int((df["Status"] == "Resolved").sum())
        pending_status_count = int((df["Status"] == "Pending").sum())
        in_progress_count = int((df["Status"] == "In Progress").sum())
        rejected_count = int((df["Status"] == "Rejected").sum())
        overdue_status_count = int((df["Status"] == "Overdue").sum())

        total_pending_backlog = int(df["is_unresolved"].sum())
        overdue_count = int(df["is_overdue"].sum())
        high_priority_pending = int((df["is_unresolved"] & df["Priority"].isin(["Critical", "High"])).sum())

        resolution_rate_pct = _sf((resolved_count / total) * 100.0) if total else 0.0
        pending_rate_pct = _sf((total_pending_backlog / total) * 100.0) if total else 0.0

        valid_res = df["resolution_days"].dropna().to_numpy(dtype=float)
        avg_res_days = _sf(np.mean(valid_res)) if len(valid_res) > 0 else 0.0
        median_res_days = _sf(np.median(valid_res)) if len(valid_res) > 0 else 0.0

        # 2. Time Series + Scikit-learn Isolation Forest Volume Anomaly Detection
        gran = "month" if str(granularity).lower() == "month" else "week"
        if gran == "month":
            df["period"] = df["Date_Received"].dt.strftime("%Y-%m")
        else:
            ws = df["Date_Received"] - pd.to_timedelta(df["Date_Received"].dt.day_of_week, unit="D")
            df["period"] = ws.dt.strftime("%Y-%m-%d")

        period_df = (
            df.groupby("period", as_index=False)
            .agg(
                received=("Complaint_ID", "count"),
                resolved=("is_resolved", "sum"),
                pending_backlog=("is_unresolved", "sum"),
                overdue=("is_overdue", "sum"),
                high_priority=("Priority", lambda s: int(s.isin(["Critical", "High"]).sum())),
                avg_days_pending=("days_pending", "mean"),
            )
            .sort_values("period")
            .reset_index(drop=True)
        )

        volume_anomalies: set[str] = set()
        if len(period_df) >= 6:
            X_vol = period_df[["received", "overdue", "high_priority"]].to_numpy(dtype=float)
            iso_vol = IsolationForest(contamination=0.15, random_state=158)
            preds = iso_vol.fit_predict(X_vol)
            mean_rx = float(period_df["received"].mean())
            for i, p in enumerate(preds):
                if p == -1 and float(period_df.loc[i, "received"]) >= mean_rx:
                    volume_anomalies.add(str(period_df.loc[i, "period"]))

        time_series: list[dict[str, Any]] = []
        for _, row in period_df.iterrows():
            per = str(row["period"])
            time_series.append(
                {
                    "period": per,
                    "received": int(row["received"]),
                    "resolved": int(row["resolved"]),
                    "pending": int(row["pending_backlog"]),
                    "overdue": int(row["overdue"]),
                    "high_priority": int(row["high_priority"]),
                    "is_volume_anomaly": per in volume_anomalies,
                }
            )

        # 3. Department Performance Intelligence
        dept_counts = df.groupby("Department")["Complaint_ID"].count().to_dict()
        mean_dept_load = float(np.mean(list(dept_counts.values()))) if dept_counts else 1.0

        department_stats: list[dict[str, Any]] = []
        dept_anomaly_map: dict[str, dict[str, Any]] = {}

        for dept_name, d_df in df.groupby("Department"):
            d_tot = int(len(d_df))
            d_res = int(d_df["is_resolved"].sum())
            d_pen = int(d_df["is_unresolved"].sum())
            d_inp = int((d_df["Status"] == "In Progress").sum())
            d_rej = int(d_df["is_rejected"].sum())
            d_ovd = int(d_df["is_overdue"].sum())
            d_res_pct = _sf((d_res / d_tot) * 100.0) if d_tot else 0.0
            d_ovd_pct = _sf((d_ovd / max(d_pen, 1)) * 100.0) if d_pen else 0.0
            d_valid_res = d_df["resolution_days"].dropna().to_numpy(dtype=float)
            d_avg_res = _sf(np.mean(d_valid_res)) if len(d_valid_res) > 0 else 0.0
            d_avg_stale = _sf(d_df.loc[d_df["is_unresolved"], "days_since_update"].mean()) if d_pen else 0.0

            recorded_series = d_df.loc[d_df["recorded_reason_norm"] != "", "recorded_reason_norm"]
            top_reasons = [
                {"reason": str(rsn), "count": int(cnt)}
                for rsn, cnt in recorded_series.value_counts().head(3).items()
            ]
            overdue_reasons = d_df.loc[d_df["is_overdue"] & (d_df["recorded_reason_norm"] != ""), "recorded_reason_norm"]
            top_overdue_reason = (
                {"reason": str(overdue_reasons.value_counts().index[0]), "count": int(overdue_reasons.value_counts().iloc[0])}
                if len(overdue_reasons) > 0
                else None
            )

            load_ratio = _sf(d_tot / max(mean_dept_load, 1.0))
            if (d_res_pct < 62.0 and d_ovd >= 5) or (d_ovd / max(d_tot, 1) >= 0.22):
                attention = "Needs Immediate Attention"
            elif d_res_pct < 75.0 or d_ovd >= 3 or d_avg_res > avg_res_days * 1.25:
                attention = "Watchlist"
            else:
                attention = "Healthy"

            dept_obj = {
                "department": str(dept_name),
                "total_received": d_tot,
                "resolved": d_res,
                "pending_backlog": d_pen,
                "in_progress": d_inp,
                "rejected": d_rej,
                "overdue": d_ovd,
                "resolution_rate_pct": d_res_pct,
                "overdue_share_of_pending_pct": d_ovd_pct,
                "avg_resolution_days": d_avg_res,
                "avg_days_since_update": d_avg_stale,
                "workload_ratio_vs_avg": load_ratio,
                "top_recorded_reasons": top_reasons,
                "top_overdue_recorded_reason": top_overdue_reason,
                "attention_status": attention,
            }
            department_stats.append(dept_obj)
            dept_anomaly_map[str(dept_name)] = dept_obj

        department_stats.sort(key=lambda x: (x["overdue"], x["pending_backlog"]), reverse=True)

        # 4. Category Performance Breakdown
        category_stats: list[dict[str, Any]] = []
        for cat_name, c_df in df.groupby("Category"):
            c_tot = int(len(c_df))
            c_res = int(c_df["is_resolved"].sum())
            c_pen = int(c_df["is_unresolved"].sum())
            c_ovd = int(c_df["is_overdue"].sum())
            c_valid_res = c_df["resolution_days"].dropna().to_numpy(dtype=float)
            c_avg_res = _sf(np.mean(c_valid_res)) if len(c_valid_res) > 0 else 0.0
            category_stats.append(
                {
                    "category": str(cat_name),
                    "total_received": c_tot,
                    "resolved": c_res,
                    "pending_backlog": c_pen,
                    "overdue": c_ovd,
                    "resolution_rate_pct": _sf((c_res / c_tot) * 100.0) if c_tot else 0.0,
                    "avg_resolution_days": c_avg_res,
                }
            )
        category_stats.sort(key=lambda x: (x["overdue"], x["total_received"]), reverse=True)

        # 5. Ticket-Level Scikit-learn Isolation Forest Delay Anomaly Detection
        unresolved_df = df[df["is_unresolved"]].copy()
        anomalous_ticket_ids: set[str] = set()
        anomaly_scores: dict[str, float] = {}

        if len(unresolved_df) >= 10:
            unresolved_df["prio_num"] = unresolved_df["Priority"].map(PRIORITY_SCORE_MAP).fillna(2.0)
            unresolved_df["dept_load"] = unresolved_df["Department"].map(
                lambda d: dept_anomaly_map.get(d, {}).get("workload_ratio_vs_avg", 1.0)
            )
            X_tkt = unresolved_df[
                ["days_pending", "days_overdue", "days_since_update", "prio_num", "dept_load"]
            ].to_numpy(dtype=float)
            iso_tkt = IsolationForest(contamination=0.10, random_state=158)
            tkt_preds = iso_tkt.fit_predict(X_tkt)
            tkt_scores = iso_tkt.decision_function(X_tkt)
            for idx, (cid, pred, score) in enumerate(
                zip(unresolved_df["Complaint_ID"].tolist(), tkt_preds, tkt_scores)
            ):
                anomaly_scores[str(cid)] = _sf(score, 0.0)
                if pred == -1 and (
                    float(unresolved_df.iloc[idx]["days_overdue"]) > 0
                    or float(unresolved_df.iloc[idx]["days_pending"]) >= 5
                ):
                    anomalous_ticket_ids.add(str(cid))

        # 6. Strict Evidence-Separated Delay Reason Analysis
        delayed_or_pending = df[df["is_unresolved"] | (df["days_overdue"] > 0)].copy()
        recorded_df = delayed_or_pending[delayed_or_pending["recorded_reason_norm"] != ""]
        unrecorded_df = delayed_or_pending[delayed_or_pending["recorded_reason_norm"] == ""]

        recorded_reason_breakdown: list[dict[str, Any]] = []
        total_recorded = int(len(recorded_df))
        for rsn, r_df in recorded_df.groupby("recorded_reason_norm"):
            cnt = int(len(r_df))
            ovd_cnt = int(r_df["is_overdue"].sum())
            top_depts = [
                {"department": str(d), "count": int(c)}
                for d, c in r_df["Department"].value_counts().head(2).items()
            ]
            recorded_reason_breakdown.append(
                {
                    "reason": str(rsn),
                    "count": cnt,
                    "overdue_count": ovd_cnt,
                    "share_of_recorded_pct": _sf((cnt / total_recorded) * 100.0) if total_recorded else 0.0,
                    "affected_departments": top_depts,
                    "evidence_type": "RECORDED",
                }
            )
        recorded_reason_breakdown.sort(key=lambda x: x["count"], reverse=True)

        # Inferred pattern explanations ONLY when Delay_Reason is missing AND quantitative signals exist
        inferred_patterns: list[dict[str, Any]] = []
        insufficient_evidence_count = 0

        if len(unrecorded_df) > 0:
            for dept_name, u_df in unrecorded_df.groupby("Department"):
                u_cnt = int(len(u_df))
                d_meta = dept_anomaly_map.get(str(dept_name), {})
                avg_stale = float(u_df["days_since_update"].mean())
                high_prio_share = float(u_df["Priority"].isin(["Critical", "High"]).mean())
                dept_load_ratio = float(d_meta.get("workload_ratio_vs_avg", 1.0))

                signals: list[str] = []
                if dept_load_ratio >= 1.20 and u_cnt >= 3:
                    signals.append(
                        f"department workload is {dept_load_ratio:.2f}x the municipal average ({d_meta.get('total_received', 0)} complaints)"
                    )
                if avg_stale >= 5.0 and u_cnt >= 2:
                    signals.append(
                        f"records show no status updates for an average of {avg_stale:.1f} days (suggestive of pending inspection or triage hold)"
                    )
                if high_prio_share >= 0.45 and u_cnt >= 3:
                    signals.append(
                        f"{high_prio_share * 100:.0f}% of unrecorded delayed tickets in {dept_name} are High/Critical priority"
                    )

                if signals:
                    inferred_patterns.append(
                        {
                            "department": str(dept_name),
                            "unrecorded_delayed_count": u_cnt,
                            "evidence_type": "INFERRED_PATTERN",
                            "pattern_explanation": (
                                f"Possible inferred factor (unconfirmed) for {u_cnt} complaints lacking a recorded Delay_Reason in {dept_name}: "
                                + "; ".join(signals)
                                + "."
                            ),
                        }
                    )
                else:
                    insufficient_evidence_count += u_cnt

        # 7. Detailed Pending & Overdue Complaint Queue (with explicit evidence tagging)
        pending_queue: list[dict[str, Any]] = []
        inferred_dept_lookup = {item["department"]: item["pattern_explanation"] for item in inferred_patterns}

        # Sort overdue high-priority longest-waiting complaints first
        queue_sorted = unresolved_df.sort_values(
            by=["is_overdue", "days_overdue", "days_pending"],
            ascending=[False, False, False],
        )
        for _, row in queue_sorted.head(200).iterrows():
            cid = str(row["Complaint_ID"])
            rec_reason = str(row["recorded_reason_norm"]).strip()
            dept_n = str(row["Department"])
            if rec_reason:
                ev_type = "RECORDED"
                reason_display = rec_reason
            elif dept_n in inferred_dept_lookup and (float(row["days_since_update"]) >= 5.0 or float(row["days_overdue"]) > 0):
                ev_type = "INFERRED_PATTERN"
                reason_display = f"Unconfirmed pattern: {inferred_dept_lookup[dept_n]}"
            else:
                ev_type = "INSUFFICIENT_EVIDENCE"
                reason_display = INSUFFICIENT_EVIDENCE_MSG

            pending_queue.append(
                {
                    "complaint_id": cid,
                    "category": str(row["Category"]),
                    "department": dept_n,
                    "assigned_team": str(row["Assigned_Team"]),
                    "priority": str(row["Priority"]),
                    "status": str(row["Status"]),
                    "date_received": row["Date_Received"].strftime("%Y-%m-%d"),
                    "deadline": row["Deadline"].strftime("%Y-%m-%d"),
                    "last_updated": row["Last_Updated_Date"].strftime("%Y-%m-%d"),
                    "days_pending": _sf(row["days_pending"], 0.0),
                    "days_overdue": _sf(row["days_overdue"], 0.0),
                    "days_since_update": _sf(row["days_since_update"], 0.0),
                    "is_overdue": bool(row["is_overdue"]),
                    "recorded_delay_reason": rec_reason or "None recorded",
                    "evidence_type": ev_type,
                    "delay_explanation": reason_display,
                    "is_ml_anomaly": cid in anomalous_ticket_ids,
                    "ml_anomaly_score": anomaly_scores.get(cid, 0.0),
                }
            )

        status_breakdown = [
            {"status": "Resolved", "count": resolved_count, "pct": _sf((resolved_count / total) * 100.0)},
            {"status": "Pending", "count": pending_status_count, "pct": _sf((pending_status_count / total) * 100.0)},
            {"status": "In Progress", "count": in_progress_count, "pct": _sf((in_progress_count / total) * 100.0)},
            {"status": "Overdue (Status)", "count": overdue_status_count, "pct": _sf((overdue_status_count / total) * 100.0)},
            {"status": "Rejected", "count": rejected_count, "pct": _sf((rejected_count / total) * 100.0)},
        ]

        return {
            "empty": False,
            "available_filters": {
                "departments": all_departments,
                "categories": all_categories,
                "statuses": all_statuses,
                "priorities": all_priorities,
            },
            "reference_date": reference_date.strftime("%Y-%m-%d"),
            "kpis": {
                "total_received": total,
                "resolved_count": resolved_count,
                "pending_status_count": pending_status_count,
                "in_progress_count": in_progress_count,
                "rejected_count": rejected_count,
                "overdue_status_count": overdue_status_count,
                "total_pending_backlog": total_pending_backlog,
                "overdue_count": overdue_count,
                "high_priority_pending": high_priority_pending,
                "resolution_rate_pct": resolution_rate_pct,
                "pending_rate_pct": pending_rate_pct,
                "avg_resolution_days": avg_res_days,
                "median_resolution_days": median_res_days,
                "departments_needing_attention": sum(
                    1 for d in department_stats if d["attention_status"] == "Needs Immediate Attention"
                ),
                "date_range": {
                    "start": df["Date_Received"].min().strftime("%Y-%m-%d"),
                    "end": reference_date.strftime("%Y-%m-%d"),
                },
            },
            "status_breakdown": status_breakdown,
            "time_series": time_series,
            "departments": department_stats,
            "categories": category_stats,
            "delay_analysis": {
                "total_delayed_or_pending": int(len(delayed_or_pending)),
                "recorded_reason_cases": total_recorded,
                "unrecorded_reason_cases": int(len(unrecorded_df)),
                "insufficient_evidence_cases": int(insufficient_evidence_count),
                "insufficient_evidence_message": INSUFFICIENT_EVIDENCE_MSG,
                "recorded_reasons": recorded_reason_breakdown,
                "inferred_patterns": inferred_patterns,
            },
            "ml_anomalies": {
                "model": "Scikit-learn IsolationForest",
                "volume_anomaly_periods": sorted(volume_anomalies),
                "flagged_delay_ticket_count": len(anomalous_ticket_ids),
                "flagged_ticket_ids": sorted(anomalous_ticket_ids)[:25],
            },
            "pending_overdue_queue": pending_queue,
        }

