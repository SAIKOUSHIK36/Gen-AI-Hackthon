"""Layer 4: Google Gemini Cognitive Engine, Grounded Q&A ("Ask CivicPulse AI"), and Anti-Hallucination Guardrails."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any

from analytics_engine import INSUFFICIENT_EVIDENCE_MSG
from privacy_shield import scan_text_for_pii, scrub_pii_text

try:
    from google import genai
    from google.genai import types as genai_types

    GENAI_AVAILABLE = True
except ImportError:  # pragma: no cover
    genai = None
    genai_types = None
    GENAI_AVAILABLE = False


class GuardrailViolation(RuntimeError):
    """Raised when pre-flight privacy or grounding assertions fail."""


def build_grounded_context(analytics: dict[str, Any]) -> dict[str, Any]:
    """Serialize ONLY Python-calculated statistics and anonymized complaint summaries."""
    kpis = analytics.get("kpis", {})
    departments = analytics.get("departments", [])
    categories = analytics.get("categories", [])
    delay = analytics.get("delay_analysis", {})
    ml = analytics.get("ml_anomalies", {})
    top_overdue = [
        {
            "complaint_id": q["complaint_id"],
            "department": q["department"],
            "category": q["category"],
            "priority": q["priority"],
            "status": q["status"],
            "days_pending": q["days_pending"],
            "days_overdue": q["days_overdue"],
            "recorded_delay_reason": q["recorded_delay_reason"],
            "evidence_type": q["evidence_type"],
            "is_ml_anomaly": q["is_ml_anomaly"],
        }
        for q in analytics.get("pending_overdue_queue", [])[:15]
    ]

    return {
        "reference_date": analytics.get("reference_date"),
        "kpis": kpis,
        "status_breakdown": analytics.get("status_breakdown", []),
        "departments": departments,
        "categories": categories[:10],
        "delay_analysis": delay,
        "ml_anomalies": ml,
        "top_overdue_complaints": top_overdue,
    }


def _assert_zero_pii(payload: dict[str, Any]) -> None:
    serialized = json.dumps(payload, ensure_ascii=False)
    hits = scan_text_for_pii(serialized)
    if hits:
        raise GuardrailViolation(f"Blocked Layer 4 payload due to detected PII patterns: {hits}")


def _deterministic_report_fallback(ctx: dict[str, Any], focus_prompt: str, reason: str) -> dict[str, Any]:
    kpis = ctx.get("kpis", {})
    depts = ctx.get("departments", [])
    delay = ctx.get("delay_analysis", {})
    ml = ctx.get("ml_anomalies", {})
    recorded = delay.get("recorded_reasons", [])
    inferred = delay.get("inferred_patterns", [])

    total = kpis.get("total_received", 0)
    resolved = kpis.get("resolved_count", 0)
    pending = kpis.get("total_pending_backlog", 0)
    overdue = kpis.get("overdue_count", 0)
    res_pct = kpis.get("resolution_rate_pct", 0.0)
    avg_days = kpis.get("avg_resolution_days", 0.0)

    top_dept = depts[0] if depts else {}
    top_dept_name = top_dept.get("department", "Primary Department")
    top_dept_rec = (top_dept.get("top_overdue_recorded_reason") or {})
    top_reason_obj = recorded[0] if recorded else {}

    dept_summary_text = (
        f"{top_dept_name} received {top_dept.get('total_received', 0)} complaints, with {top_dept.get('resolved', 0)} resolved, "
        f"{top_dept.get('pending_backlog', 0)} pending, and {top_dept.get('overdue', 0)} having crossed their deadlines "
        f"(average resolution time: {top_dept.get('avg_resolution_days', 0)} days). "
    )
    if top_dept_rec:
        dept_summary_text += (
            f"The available records show that '{top_dept_rec.get('reason')}' is a recorded reason for delays in "
            f"{top_dept_rec.get('count')} overdue cases in {top_dept_name}. "
        )
    else:
        dept_summary_text += f"For unrecorded overdue cases, {INSUFFICIENT_EVIDENCE_MSG} "

    exec_summary = (
        f"Across {kpis.get('date_range', {}).get('start', 'N/A')} to {kpis.get('date_range', {}).get('end', 'N/A')}, "
        f"departments received {total} complaints: {resolved} resolved ({res_pct}%), {pending} currently pending/in-progress "
        f"({kpis.get('pending_rate_pct', 0)}%), and {overdue} overdue past their deadlines. Average resolution time is {avg_days} days."
    )
    if focus_prompt:
        exec_summary += f" Briefing focus: {focus_prompt}."

    recorded_findings = [
        {
            "reason": r["reason"],
            "evidence": f"Confirmed in {r['count']} delayed/pending records ({r['overdue_count']} overdue; {r['share_of_recorded_pct']}% of recorded reasons).",
            "departments": ", ".join(f"{d['department']} ({d['count']})" for d in r.get("affected_departments", [])),
            "evidence_type": "RECORDED",
        }
        for r in recorded[:5]
    ]

    inferred_findings = [
        {
            "department": p["department"],
            "explanation": p["pattern_explanation"],
            "evidence_type": "INFERRED_PATTERN",
        }
        for p in inferred
    ]
    if delay.get("insufficient_evidence_cases", 0) > 0:
        inferred_findings.append(
            {
                "department": "Multiple / Unattributed",
                "explanation": f"{delay['insufficient_evidence_cases']} delayed complaint(s) have no recorded Delay_Reason and insufficient supporting pattern data: {INSUFFICIENT_EVIDENCE_MSG}",
                "evidence_type": "INSUFFICIENT_EVIDENCE",
            }
        )

    recommendations = [
        {
            "priority": "High Priority",
            "recommendation": f"Prioritize the {overdue} overdue complaints that have crossed deadlines, starting with {top_dept_name} ({top_dept.get('overdue', 0)} overdue).",
            "basis": f"Python deadline audit identified {kpis.get('high_priority_pending', 0)} high/critical priority pending complaints.",
        },
    ]
    if top_reason_obj:
        recommendations.append(
            {
                "priority": "Resource & Process",
                "recommendation": f"Address '{top_reason_obj['reason']}' across affected departments (recorded in {top_reason_obj['count']} cases).",
                "basis": "Confirmed top recorded delay factor in uploaded Delay_Reason records.",
            }
        )
    recommendations.extend(
        [
            {
                "priority": "Monitoring & Staffing",
                "recommendation": "Review staff allocation and follow up on stale/pending field inspections for departments flagged 'Needs Immediate Attention'.",
                "basis": f"Isolation Forest detected {ml.get('flagged_delay_ticket_count', 0)} anomalous delay records and {len(ml.get('volume_anomaly_periods', []))} intake spike period(s).",
            },
            {
                "priority": "Data Governance",
                "recommendation": f"Mandate structured Delay_Reason logging for {delay.get('unrecorded_reason_cases', 0)} unrecorded delayed complaints so future root causes are confirmed rather than inferred.",
                "basis": "Evidence-completeness audit of pending/overdue records.",
            },
        ]
    )

    return {
        "executive_summary": exec_summary,
        "department_performance_narrative": dept_summary_text,
        "recorded_delay_findings": recorded_findings,
        "inferred_delay_patterns": inferred_findings,
        "anomaly_summary": (
            f"Scikit-learn Isolation Forest flagged {ml.get('flagged_delay_ticket_count', 0)} statistically unusual delay tickets "
            f"and {len(ml.get('volume_anomaly_periods', []))} unusual intake volume period(s): "
            f"{', '.join(ml.get('volume_anomaly_periods', [])) or 'None'}."
        ),
        "administrative_recommendations": recommendations,
        "privacy_and_grounding_note": (
            "All counts and rates were computed deterministically by Python/Pandas/Scikit-learn. "
            "Zero citizen PII was processed. Recorded reasons are strictly separated from unconfirmed inferred patterns."
        ),
        "engine_note": reason,
    }


def _deterministic_qa_answer(question: str, ctx: dict[str, Any]) -> str:
    q = question.lower().strip()
    kpis = ctx.get("kpis", {})
    depts = ctx.get("departments", [])
    delay = ctx.get("delay_analysis", {})
    recorded = delay.get("recorded_reasons", [])
    inferred = delay.get("inferred_patterns", [])
    top_overdue = ctx.get("top_overdue_complaints", [])

    if "resolved" in q and "how many" in q:
        return (
            f"Out of {kpis.get('total_received', 0)} total complaints received, **{kpis.get('resolved_count', 0)} complaints have been resolved** "
            f"(a **{kpis.get('resolution_rate_pct', 0)}%** resolution rate), with an average resolution time of **{kpis.get('avg_resolution_days', 0)} days**."
        )

    if ("pending" in q or "remaining" in q) and ("how many" in q or "count" in q):
        return (
            f"There are currently **{kpis.get('total_pending_backlog', 0)} pending/unresolved complaints** "
            f"({kpis.get('pending_rate_pct', 0)}% of total): specifically {kpis.get('pending_status_count', 0)} in 'Pending' status, "
            f"{kpis.get('in_progress_count', 0)} 'In Progress', and {kpis.get('overdue_status_count', 0)} explicitly marked 'Overdue'. "
            f"In total across unresolved records, **{kpis.get('overdue_count', 0)} complaints have crossed their deadlines**."
        )

    if "main" in q and ("reason" in q or "delay" in q):
        if recorded:
            top = recorded[0]
            runner = f" Followed by '{recorded[1]['reason']}' ({recorded[1]['count']} cases)." if len(recorded) > 1 else ""
            return (
                f"Based on confirmed `Delay_Reason` records ({delay.get('recorded_reason_cases', 0)} documented cases), "
                f"the main recorded reason for delays is **'{top['reason']}'**, appearing in **{top['count']} delayed/pending complaints** "
                f"({top['overdue_count']} overdue; {top['share_of_recorded_pct']}% of recorded reasons).{runner}"
            )
        return f"No confirmed Delay_Reason values were recorded in the dataset. {INSUFFICIENT_EVIDENCE_MSG}"

    if "why" in q and "delay" in q:
        parts = []
        if recorded:
            top3 = "; ".join(f"{r['reason']} ({r['count']} cases, {r['overdue_count']} overdue)" for r in recorded[:3])
            parts.append(f"**Confirmed Recorded Delay Reasons:** {top3}.")
        if inferred:
            inf_txt = " ".join(p["pattern_explanation"] for p in inferred[:2])
            parts.append(f"**Possible Inferred Patterns (unconfirmed, for cases missing Delay_Reason):** {inf_txt}")
        if delay.get("insufficient_evidence_cases", 0) > 0:
            parts.append(
                f"For {delay['insufficient_evidence_cases']} unrecorded cases without clear pattern signals: *{INSUFFICIENT_EVIDENCE_MSG}*"
            )
        return "\n\n".join(parts) if parts else INSUFFICIENT_EVIDENCE_MSG

    if ("which department" in q or "most overdue" in q or "poorly" in q or "worst" in q) and depts:
        worst = max(depts, key=lambda d: (d["overdue"], -d["resolution_rate_pct"]))
        low_res = min(depts, key=lambda d: d["resolution_rate_pct"])
        rec_note = (
            f"Its top recorded overdue delay reason is '{worst['top_overdue_recorded_reason']['reason']}' "
            f"({worst['top_overdue_recorded_reason']['count']} cases)."
            if worst.get("top_overdue_recorded_reason")
            else INSUFFICIENT_EVIDENCE_MSG
        )
        return (
            f"**{worst['department']}** has the highest overdue volume (**{worst['overdue']} overdue** out of {worst['pending_backlog']} pending, "
            f"with a {worst['resolution_rate_pct']}% resolution rate and {worst['avg_resolution_days']} avg resolution days). "
            f"{low_res['department']} has the lowest overall resolution rate at **{low_res['resolution_rate_pct']}%**. {rec_note}"
        )

    if "immediate attention" in q or ("which complaints" in q):
        urgent = [c for c in top_overdue if c["is_overdue"]][:5]
        if not urgent:
            return "There are currently zero overdue complaints in the active slice."
        lines = "\n".join(
            f"- **{c['complaint_id']}** ({c['department']} / {c['category']}, {c['priority']}): {c['days_overdue']}d overdue — Recorded reason: {c['recorded_delay_reason']}"
            for c in urgent
        )
        return f"The top overdue complaints requiring immediate administrative follow-up are:\n{lines}"

    if "reduce" in q or "faster" in q or "recommend" in q or "action" in q:
        worst = depts[0] if depts else {}
        top_r = recorded[0]["reason"] if recorded else None
        action_r = (
            f"Address '{top_r}' (recorded in {recorded[0]['count']} delayed cases)."
            if top_r
            else "Enforce mandatory Delay_Reason logging on open tickets."
        )
        return (
            f"Recommended evidence-based actions:\n"
            f"1. **Prioritize {kpis.get('overdue_count', 0)} Overdue Tickets:** Triage the {kpis.get('high_priority_pending', 0)} High/Critical pending complaints first, focusing on {worst.get('department', 'top backlog departments')} ({worst.get('overdue', 0)} overdue).\n"
            f"2. **Resolve Top Recorded Bottleneck:** {action_r}\n"
            f"3. **Follow Up on Stale Tickets & Spikes:** Review the {ctx.get('ml_anomalies', {}).get('flagged_delay_ticket_count', 0)} delay anomalies flagged by Isolation Forest and reallocate staff across high-workload queues."
        )

    # General overview fallback
    worst = depts[0] if depts else {}
    top_r = recorded[0]["reason"] if recorded else INSUFFICIENT_EVIDENCE_MSG
    return (
        f"**CivicPulse Summary:** Received **{kpis.get('total_received', 0)}** complaints — **{kpis.get('resolved_count', 0)}** resolved "
        f"({kpis.get('resolution_rate_pct', 0)}%), **{kpis.get('total_pending_backlog', 0)}** pending, and **{kpis.get('overdue_count', 0)}** overdue "
        f"(avg resolution: {kpis.get('avg_resolution_days', 0)} days). "
        f"Highest overdue backlog: **{worst.get('department', 'N/A')}** ({worst.get('overdue', 0)} overdue). "
        f"Top recorded delay factor: **{top_r}**."
    )


class CivicPulseGeminiService:
    """Google Gemini API Cognitive Layer with strict numerical grounding & PII guardrails."""

    def __init__(self, default_model: str | None = None) -> None:
        self.default_model = default_model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    def is_configured(self, api_key: str | None = None) -> bool:
        key = (api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
        return bool(key) and GENAI_AVAILABLE

    def generate_executive_report(
        self,
        analytics: dict[str, Any],
        focus_prompt: str = "",
        api_key: str | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        ctx = build_grounded_context(analytics)
        _assert_zero_pii(ctx)

        clean_focus, _ = scrub_pii_text(focus_prompt) if focus_prompt else ("", {})
        resolved_key = (api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
        resolved_model = (model or self.default_model).strip() or "gemini-2.5-flash"

        mode = "deterministic_fallback"
        report_json: dict[str, Any] | None = None
        note = ""

        if resolved_key and GENAI_AVAILABLE:
            sys_prompt = (
                "You are CivicPulse AI, an executive government complaint resolution & delay analyst. "
                "STRICT GROUNDING RULES:\n"
                "1. Use ONLY numbers, departments, complaint IDs, and recorded delay reasons present in the provided JSON. Never invent statistics.\n"
                "2. Clearly separate confirmed RECORDED Delay_Reason evidence from unconfirmed INFERRED_PATTERN explanations.\n"
                f"3. When evidence is missing/insufficient, explicitly write: '{INSUFFICIENT_EVIDENCE_MSG}'. Never present guesses as facts.\n"
                "4. Zero citizen PII may ever appear.\n"
                "Return valid JSON with keys: executive_summary, department_performance_narrative, "
                "recorded_delay_findings (list of {reason, evidence, departments, evidence_type}), "
                "inferred_delay_patterns (list of {department, explanation, evidence_type}), "
                "anomaly_summary, administrative_recommendations (list of {priority, recommendation, basis}), privacy_and_grounding_note."
            )
            prompt = (
                f"Focus: {clean_focus or 'Comprehensive administrative delay & performance briefing'}\n\n"
                f"Python-calculated analytics JSON:\n{json.dumps(ctx, indent=2)}"
            )
            try:
                client = genai.Client(api_key=resolved_key)
                resp = client.models.generate_content(
                    model=resolved_model,
                    contents=prompt,
                    config=genai_types.GenerateContentConfig(
                        system_instruction=sys_prompt,
                        temperature=0.2,
                        response_mime_type="application/json",
                    ),
                )
                txt = (resp.text or "").strip()
                if txt.startswith("```"):
                    txt = re.sub(r"^```(?:json)?\s*|\s*```$", "", txt, flags=re.DOTALL).strip()
                parsed = json.loads(txt)
                if isinstance(parsed, dict) and "executive_summary" in parsed:
                    report_json = parsed
                    mode = "gemini_live"
                else:
                    note = "Gemini response missed expected keys; used deterministic grounded engine."
            except Exception as exc:  # pragma: no cover
                note = f"Gemini API fallback ({type(exc).__name__}): {str(exc)[:140]}"
        elif not resolved_key:
            note = "GEMINI_API_KEY not configured; running in Data-Grounded Deterministic Mode."
        else:
            note = "google-genai package unavailable; running in Data-Grounded Deterministic Mode."

        if report_json is None:
            report_json = _deterministic_report_fallback(ctx, clean_focus, note)

        # Output PII check
        out_leaks = scan_text_for_pii(json.dumps(report_json, ensure_ascii=False))
        return {
            "mode": mode,
            "model": resolved_model if mode == "gemini_live" else "deterministic-grounded-v1",
            "report": report_json,
            "guardrails": {
                "zero_pii_verified": len(out_leaks) == 0,
                "detected_output_pii": out_leaks,
                "grounded_stats_only": True,
                "verified_at_utc": datetime.now(timezone.utc).isoformat(),
            },
        }

    def answer_question(
        self,
        question: str,
        analytics: dict[str, Any],
        history: list[dict[str, str]] | None = None,
        api_key: str | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        clean_q, _ = scrub_pii_text(question.strip())
        if not clean_q:
            raise ValueError("Please enter a valid administrative question.")

        ctx = build_grounded_context(analytics)
        _assert_zero_pii(ctx)

        resolved_key = (api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
        resolved_model = (model or self.default_model).strip() or "gemini-2.5-flash"

        mode = "deterministic_fallback"
        answer = ""

        if resolved_key and GENAI_AVAILABLE:
            sys_prompt = (
                "You are 'Ask CivicPulse AI', an analytical assistant for government administrators. "
                "Answer ONLY using the Python-calculated complaint analytics JSON provided. "
                "Never invent counts, percentages, or delay reasons. Explicitly distinguish recorded Delay_Reason facts "
                f"from unconfirmed inferred patterns, and state '{INSUFFICIENT_EVIDENCE_MSG}' if evidence is lacking."
            )
            recent_hist = "\n".join(f"{h.get('role', 'user').upper()}: {h.get('message', '')}" for h in (history or [])[-4:])
            prompt = (
                f"Analytics Context:\n{json.dumps(ctx)}\n\n"
                f"Recent Conversation:\n{recent_hist}\n\n"
                f"Administrator Question: {clean_q}"
            )
            try:
                client = genai.Client(api_key=resolved_key)
                resp = client.models.generate_content(
                    model=resolved_model,
                    contents=prompt,
                    config=genai_types.GenerateContentConfig(
                        system_instruction=sys_prompt,
                        temperature=0.15,
                    ),
                )
                candidate = (resp.text or "").strip()
                if candidate:
                    answer = candidate
                    mode = "gemini_live"
            except Exception:  # pragma: no cover
                answer = ""

        if not answer:
            answer = _deterministic_qa_answer(clean_q, ctx)

        cleaned_answer, _ = scrub_pii_text(answer)
        return {
            "question": clean_q,
            "answer": cleaned_answer,
            "mode": mode,
            "model": resolved_model if mode == "gemini_live" else "deterministic-grounded-v1",
        }

