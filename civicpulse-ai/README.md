# CivicPulse AI — AI-Powered Public Complaint Resolution & Delay Analysis System

CivicPulse AI is a full-stack GenAI governance analytics platform that helps municipal and public departments understand complaint resolution performance, identify verified vs. inferred causes of delays, detect volume and delay anomalies using Scikit-learn Isolation Forest, answer administrator queries via **Ask CivicPulse AI**, and export ReportLab executive PDF reports.

---

## Core Architecture & Intelligence

1. **Zero-PII Privacy Firewall & Flexible Ingestion (`backend/privacy_shield.py`)**
   - Supports **CSV** and **Excel (`.xlsx` / `.xls`)** uploads.
   - Maps canonical CivicPulse columns (`Complaint_ID`, `Category`, `Department`, `Date_Received`, `Status`, `Deadline`, `Resolution_Date`, `Assigned_Department`, `Assigned_Team`, `Priority`, `Delay_Reason`, `Last_Updated_Date`) as well as public 311 open-data columns.
   - Automatically drops any citizen PII columns and scrubs inline PII regexes.

2. **Quantitative Analytics, Rule-Based Delay Engine & Isolation Forest (`backend/analytics_engine.py`)**
   - Computes exact counts and rates for **Resolved**, **Pending**, **In Progress**, **Rejected**, and **Overdue** complaints.
   - Calculates `days_pending`, `days_overdue`, and staleness (`days_since_update`) for unresolved cases.
   - **Strict Evidence Separation:** Separates confirmed `RECORDED` causes from the `Delay_Reason` column vs. unconfirmed `INFERRED_PATTERN` explanations, and displays `"Reason not available – further investigation required."` whenever evidence is insufficient.
   - Runs **Scikit-learn `IsolationForest`** to detect unusual intake volume spikes and ticket-level delay anomalies.

3. **Google Gemini Cognitive Layer + Anti-Hallucination Guardrails (`backend/gemini_service.py`)**
   - Python calculates all numerical metrics; Gemini explains results in plain English and generates evidence-backed recommendations (with automatic Data-Grounded Deterministic Fallback when no `GEMINI_API_KEY` is configured).
   - Powers **Ask CivicPulse AI** conversational Q&A grounded strictly in dataset statistics.

4. **SQLite Persistence & ReportLab PDF Export (`backend/database.py`, `backend/pdf_report.py`)**
   - Stores upload receipts, saved administrative reports, Q&A history, and system audit logs in `backend/civicpulse.db`.
   - Exports executive PDF briefings via ReportLab.

---

## Application Pages

1. **Dashboard** — Executive summary answering the 5 core governance questions, KPI cards, trends, and alerts.
2. **Upload Complaint Dataset** — CSV/Excel dropzone, synthetic generator, Zero-PII ingestion receipt, and anonymized preview.
3. **Complaint Resolution Analysis** — Resolution vs. pending rates, status donut, department & category benchmarks.
4. **Delay Reason Analysis** — Recorded vs. inferred delay causes, insufficient-evidence flags, and overdue complaint table.
5. **Department Performance** — Department accountability scorecard, workload ratios, and attention flags.
6. **Ask CivicPulse AI** — Conversational Q&A assistant with administrator quick-prompt chips.
7. **AI Administrative Reports** — Executive briefing generator, SQLite report history, and PDF download.
8. **Audit Logs** — SQLite audit trail of uploads, anomaly scans, AI queries, and PDF exports.

---

## Quick Start

1. *(Optional)* Copy `backend/.env.example` to `backend/.env` and set `GEMINI_API_KEY=...` (or configure it inside the sidebar **Gemini API Settings**).
2. Run the unified launcher:
   ```powershell
   .\start.ps1
   ```
   Open **http://localhost:5173** (or **http://127.0.0.1:8000** for the built bundle).

