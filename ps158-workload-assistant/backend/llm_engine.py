"""Layer 4: Gemini API Cognitive Engine & Strict Privacy/Grounding Guardrails.

Only strictly aggregated Layer 3 statistical summaries and anonymized worker IDs
(e.g., ENG-042, SAN-108) are ever serialized into LLM prompts. Includes pre-flight
PII assertions, Gemini structured synthesis, post-generation PII/grounding
verification, and an offline deterministic fallback narrative generator.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any

from privacy_analytics import ANON_WORKER_ID_RE, scan_text_for_pii, scrub_pii_text

try:
    from google import genai
    from google.genai import types as genai_types

    GENAI_SDK_AVAILABLE = True
except ImportError:  # pragma: no cover - optional at import time
    genai = None
    genai_types = None
    GENAI_SDK_AVAILABLE = False


class PrivacyGuardrailViolation(RuntimeError):
    """Raised when pre-flight or post-output checks detect potential PII."""


FORBIDDEN_PAYLOAD_KEYS = {
    "citizen_name",
    "citizen_phone",
    "citizen_email",
    "street_address",
    "free_text_complaint",
    "raw_rows",
    "caller_name",
    "resident_name",
    "email",
    "phone",
    "address",
}

WORKER_ID_IN_TEXT_RE = re.compile(r"\b[A-Z]{2,5}-\d{2,4}\b")


def build_safe_llm_payload(analytics: dict[str, Any], focus_area: str = "") -> dict[str, Any]:
    """Construct the minimal, strictly aggregated, zero-PII JSON sent to Layer 4."""
    kpis = analytics.get("kpis", {})
    trend = analytics.get("trend_metrics", {})
    categories = analytics.get("categories", [])
    workers = analytics.get("worker_audit", [])
    time_series = analytics.get("time_series", [])
    actions = analytics.get("actions_rollup", [])

    # Condense worker audit to anonymized IDs and statistical operational metrics only
    safe_workers = []
    for w in workers[:30]:
        wid = str(w.get("worker_id", "WRK-000")).upper()
        if not ANON_WORKER_ID_RE.match(wid):
            raise PrivacyGuardrailViolation(f"Non-anonymized worker identifier blocked before Layer 4: {wid}")
        safe_workers.append(
            {
                "worker_id": wid,
                "primary_category": w.get("primary_category"),
                "assigned_count": w.get("assigned_count"),
                "completed_count": w.get("completed_count"),
                "remaining_count": w.get("remaining_count"),
                "escalated_count": w.get("escalated_count"),
                "completion_rate_pct": w.get("completion_rate_pct"),
                "avg_resolution_hours": w.get("avg_resolution_hours"),
                "sla_compliance_pct": w.get("sla_compliance_pct"),
                "workload_z_score": w.get("workload_z_score"),
                "accountability_flag": w.get("accountability_flag"),
                "top_actions": w.get("actions_summary", [])[:3],
            }
        )

    clean_focus, _ = scrub_pii_text(focus_area.strip()) if focus_area else ("", {})

    payload = {
        "administrative_focus": clean_focus or "Comprehensive executive workload & worker accountability briefing",
        "kpis": kpis,
        "trend_metrics": trend,
        "recent_periods": time_series[-8:],
        "service_categories": categories,
        "top_operational_actions": actions[:8],
        "anonymized_worker_audit": safe_workers,
    }
    return payload


def assert_zero_pii_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Pre-flight Layer 4 firewall: inspect keys and serialized text for any PII."""

    def _check_keys(obj: Any) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if str(k).lower() in FORBIDDEN_PAYLOAD_KEYS:
                    raise PrivacyGuardrailViolation(f"Forbidden key detected in Layer 4 payload: {k}")
                _check_keys(v)
        elif isinstance(obj, list):
            for item in obj:
                _check_keys(item)

    _check_keys(payload)
    serialized = json.dumps(payload, ensure_ascii=False)
    findings = scan_text_for_pii(serialized)
    if findings:
        raise PrivacyGuardrailViolation(f"Pre-flight PII scan blocked payload due to patterns: {findings}")

    return {
        "preflight_passed": True,
        "payload_bytes": len(serialized.encode("utf-8")),
        "detected_patterns": [],
        "contains_raw_citizen_records": False,
    }


def _generate_deterministic_narrative(payload: dict[str, Any], reason: str) -> dict[str, Any]:
    """Data-grounded fallback narrative engine when Gemini API is unavailable."""
    kpis = payload.get("kpis", {})
    trend = payload.get("trend_metrics", {})
    categories = payload.get("service_categories", [])
    workers = payload.get("anonymized_worker_audit", [])
    focus = payload.get("administrative_focus", "")

    total = kpis.get("total_requests", 0)
    completed = kpis.get("completed_count", 0)
    remaining = kpis.get("remaining_count", 0)
    comp_pct = kpis.get("completion_rate_pct", 0.0)
    sla_pct = kpis.get("sla_compliance_pct", 0.0)
    avg_hrs = kpis.get("avg_resolution_hours", 0.0)
    overdue = kpis.get("overdue_remaining_count", 0)
    date_range = kpis.get("date_range", {})
    start_d = date_range.get("start", "N/A")
    end_d = date_range.get("end", "N/A")

    slope = trend.get("intake_slope_per_period", 0.0)
    projected = trend.get("projected_next_period_requests", 0)
    gran = trend.get("granularity", "week")
    trend_dir = "expanding" if slope > 0.5 else ("contracting" if slope < -0.5 else "stabilizing")

    sorted_cats_backlog = sorted(categories, key=lambda c: c.get("remaining", 0), reverse=True)
    top_cat = sorted_cats_backlog[0] if sorted_cats_backlog else {}
    second_cat = sorted_cats_backlog[1] if len(sorted_cats_backlog) > 1 else {}

    bottlenecks: list[dict[str, str]] = []
    for cat in sorted_cats_backlog[:3]:
        top_act = (cat.get("top_actions") or [{}])[0].get("action", "Pending dispatch")
        bottlenecks.append(
            {
                "category": str(cat.get("service_category", "Unknown")),
                "evidence": (
                    f"{cat.get('remaining', 0)} open/remaining out of {cat.get('total_requests', 0)} "
                    f"({cat.get('completion_rate_pct', 0)}% complete, {cat.get('sla_compliance_pct', 0)}% SLA)."
                ),
                "operational_driver": f"Primary queue concentration around '{top_act}' with {cat.get('avg_resolution_hours', 0)}h avg turnaround.",
                "recommended_action": f"Rebalance field dispatch capacity into {cat.get('service_category')} and prioritize {cat.get('critical_high_count', 0)} high/critical tickets.",
            }
        )

    overloaded = [w for w in workers if w.get("accountability_flag") == "Overloaded / Bottleneck"]
    sla_watch = [w for w in workers if w.get("accountability_flag") == "SLA Watch"]
    top_performers = sorted(
        [w for w in workers if w.get("accountability_flag") == "Top Performer"],
        key=lambda w: w.get("completion_rate_pct", 0.0),
        reverse=True,
    )

    overloaded_str = (
        ", ".join(
            f"{w['worker_id']} ({w['remaining_count']} remaining, {w['completion_rate_pct']}% completion, {w['sla_compliance_pct']}% SLA)"
            for w in overloaded[:4]
        )
        or "No personnel exceeded overload thresholds"
    )
    top_str = (
        ", ".join(
            f"{w['worker_id']} ({w['completed_count']} completed, {w['completion_rate_pct']}% completion, {w['sla_compliance_pct']}% SLA)"
            for w in top_performers[:4]
        )
        or "Standard balanced performance across active workers"
    )
    watch_str = (
        ", ".join(f"{w['worker_id']} ({w['sla_compliance_pct']}% SLA)" for w in sla_watch[:3])
        if sla_watch
        else "None flagged"
    )

    exec_summary = (
        f"Between {start_d} and {end_d}, municipal departments processed {total} anonymized service requests, "
        f"completing {completed} ({comp_pct}%) while carrying {remaining} remaining open or escalated tickets "
        f"({overdue} past SLA target). Overall SLA compliance stands at {sla_pct}% with an average resolution "
        f"turnaround of {avg_hrs} hours. Address focus: {focus}."
    )

    workload_analysis = (
        f"Request intake across {trend.get('period_count', 0)} {gran}ly periods is {trend_dir} "
        f"(intake slope {slope:+.2f} requests/{gran}; latest period volume change {trend.get('latest_volume_delta_pct', 0.0):+.1f}%), "
        f"with linear trend modeling projecting {projected} requests in the upcoming {gran}. "
        f"Backlog pressure is concentrated in {top_cat.get('service_category', 'core operations')} "
        f"({top_cat.get('remaining', 0)} remaining) and {second_cat.get('service_category', 'secondary queues')} "
        f"({second_cat.get('remaining', 0)} remaining)."
    )

    worker_narrative = (
        f"Personnel audit across {kpis.get('active_worker_count', 0)} anonymized worker IDs identifies strong closure throughput from "
        f"{top_str}. Conversely, acute backlog accumulation appears on {overloaded_str}. "
        f"Additional SLA monitoring is advised for: {watch_str}. All findings reference anonymized staff IDs exclusively."
    )

    recommendations = [
        {
            "priority": "Immediate (0–7 Days)",
            "action": f"Reallocate overflow queue from overloaded IDs ({', '.join(w['worker_id'] for w in overloaded[:3]) or 'peak queues'}) to peer capacity within the same service categories.",
            "expected_impact": f"Reduces {overdue} overdue remaining tickets and stabilizes SLA compliance above 85%.",
        },
        {
            "priority": "Short-Term (8–30 Days)",
            "action": f"Clear procurement and escalation holds in {top_cat.get('service_category', 'top bottleneck category')} where {top_cat.get('remaining', 0)} tickets remain open.",
            "expected_impact": "Lowers backlog-to-throughput ratio and cuts p90 turnaround latency.",
        },
        {
            "priority": "Operational Governance (30–60 Days)",
            "action": "Standardize weekly z-score workload balancing across anonymized worker rosters ahead of projected intake surges.",
            "expected_impact": f"Prepares field teams for projected {projected} requests in the next {gran}.",
        },
    ]

    return {
        "executive_summary": exec_summary,
        "workload_and_backlog_analysis": workload_analysis,
        "category_bottlenecks": bottlenecks,
        "worker_accountability_audit": worker_narrative,
        "administrative_recommendations": recommendations,
        "privacy_attestation": (
            "Zero citizen PII (names, phones, emails, street addresses, or free-text narratives) entered Layer 4. "
            "All personnel references use anonymized municipal worker IDs exclusively."
        ),
        "generation_note": reason,
    }


def verify_and_sanitize_output(
    narrative: dict[str, Any],
    analytics: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Post-generation Layer 4 guardrail verifying zero PII and data grounding."""
    valid_workers = {str(w["worker_id"]).upper() for w in analytics.get("worker_audit", [])}
    serialized = json.dumps(narrative, ensure_ascii=False)

    # 1. Scan & scrub any accidental PII pattern in LLM output
    leaked_patterns = scan_text_for_pii(serialized)
    redactions_applied = 0

    def _recursive_scrub(node: Any) -> Any:
        nonlocal redactions_applied
        if isinstance(node, str):
            cleaned, counts = scrub_pii_text(node)
            redactions_applied += sum(counts.values())
            return cleaned
        if isinstance(node, list):
            return [_recursive_scrub(item) for item in node]
        if isinstance(node, dict):
            return {k: _recursive_scrub(v) for k, v in node.items()}
        return node

    clean_narrative = _recursive_scrub(narrative)
    clean_serialized = json.dumps(clean_narrative, ensure_ascii=False)

    # 2. Verify every cited worker ID exists in Layer 3 audit table (no hallucinated IDs)
    cited_worker_ids = sorted(set(WORKER_ID_IN_TEXT_RE.findall(clean_serialized)))
    # Exclude standard non-worker prefixes like REQ-2026 or SLA-90 if ever matched
    cited_worker_ids = [wid for wid in cited_worker_ids if not wid.startswith(("REQ-", "SLA-", "KPI-"))]
    unrecognized_ids = [wid for wid in cited_worker_ids if wid not in valid_workers]

    # 3. Verify key KPI figures appear faithfully or match ground truth
    kpis = analytics.get("kpis", {})
    total_str = str(kpis.get("total_requests", ""))
    completed_str = str(kpis.get("completed_count", ""))
    remaining_str = str(kpis.get("remaining_count", ""))

    grounding_report = {
        "output_pii_scan_passed": len(leaked_patterns) == 0 and redactions_applied == 0,
        "initial_pii_flags_detected": leaked_patterns,
        "post_output_redactions_applied": redactions_applied,
        "cited_worker_ids": cited_worker_ids,
        "unrecognized_worker_ids": unrecognized_ids,
        "worker_id_grounding_passed": len(unrecognized_ids) == 0,
        "kpi_numbers_referenced": {
            "total_requests_cited": total_str in clean_serialized,
            "completed_count_cited": completed_str in clean_serialized,
            "remaining_count_cited": remaining_str in clean_serialized,
        },
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    return clean_narrative, grounding_report


class GeminiCognitiveEngine:
    """Layer 4 Cognitive Engine powered by Gemini API with strict privacy guardrails."""

    def __init__(self, default_model: str | None = None) -> None:
        self.default_model = default_model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    def is_gemini_configured(self, api_key_override: str | None = None) -> bool:
        key = (api_key_override or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
        return bool(key) and GENAI_SDK_AVAILABLE

    def generate_report(
        self,
        analytics: dict[str, Any],
        focus_area: str = "",
        api_key_override: str | None = None,
        model_override: str | None = None,
    ) -> dict[str, Any]:
        """Run Layer 4 pipeline: safe serialization -> pre-flight firewall -> Gemini/fallback -> output guardrails."""
        if analytics.get("empty"):
            raise ValueError("Cannot generate executive narrative for an empty filtered slice.")

        safe_payload = build_safe_llm_payload(analytics, focus_area=focus_area)
        preflight = assert_zero_pii_payload(safe_payload)

        api_key = (api_key_override or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
        model_name = (model_override or self.default_model).strip() or "gemini-2.5-flash"

        mode = "deterministic_fallback"
        raw_narrative: dict[str, Any] | None = None
        fallback_reason = ""

        if api_key and GENAI_SDK_AVAILABLE:
            system_instruction = (
                "You are PS 158: Public Service Workload Narrative Assistant, an executive municipal operations analyst. "
                "STRICT PRIVACY RULE: Zero citizen PII may ever be inferred, reconstructed, or output. "
                "Refer to municipal personnel ONLY by their exact anonymized worker IDs (e.g., ENG-042, SAN-108). "
                "Cite only numbers, categories, actions, and worker IDs present in the provided JSON. "
                "Return valid JSON matching this exact schema:\n"
                "{\n"
                '  "executive_summary": "string (concise 3-4 sentence overview citing total, completed, remaining, SLA %, avg hours)",\n'
                '  "workload_and_backlog_analysis": "string (time-period intake, completion velocity, backlog trajectory & projection)",\n'
                '  "category_bottlenecks": [\n'
                '    {"category": "string", "evidence": "string", "operational_driver": "string", "recommended_action": "string"}\n'
                "  ],\n"
                '  "worker_accountability_audit": "string (audit of anonymized worker IDs: top performers, overloaded IDs, actions taken)",\n'
                '  "administrative_recommendations": [\n'
                '    {"priority": "string", "action": "string", "expected_impact": "string"}\n'
                "  ],\n"
                '  "privacy_attestation": "string"\n'
                "}"
            )
            prompt = (
                "Analyze this strictly aggregated, PII-free municipal workload summary and produce the executive JSON briefing:\n\n"
                + json.dumps(safe_payload, indent=2)
            )
            try:
                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=genai_types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.2,
                        response_mime_type="application/json",
                    ),
                )
                text = (response.text or "").strip()
                # Strip markdown code fences if present
                if text.startswith("```"):
                    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.DOTALL).strip()
                parsed = json.loads(text)
                if isinstance(parsed, dict) and "executive_summary" in parsed:
                    raw_narrative = parsed
                    mode = "gemini_live"
                else:
                    fallback_reason = "Gemini response omitted expected schema keys; used grounded fallback synthesis."
            except Exception as exc:  # pragma: no cover - network/API error path
                fallback_reason = f"Gemini API fallback ({type(exc).__name__}): {str(exc)[:160]}"
        elif not api_key:
            fallback_reason = "GEMINI_API_KEY not configured; running in Data-Grounded Deterministic Fallback mode."
        else:
            fallback_reason = "google-genai package unavailable; running in Data-Grounded Deterministic Fallback mode."

        if raw_narrative is None:
            raw_narrative = _generate_deterministic_narrative(safe_payload, reason=fallback_reason)

        verified_narrative, grounding_report = verify_and_sanitize_output(raw_narrative, analytics)

        return {
            "mode": mode,
            "model": model_name if mode == "gemini_live" else "deterministic-grounded-v1",
            "narrative": verified_narrative,
            "guardrails": {
                "preflight": preflight,
                "post_output": grounding_report,
            },
            "llm_payload_preview": safe_payload,
        }

