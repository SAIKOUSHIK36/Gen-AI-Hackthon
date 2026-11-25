# PS 158: Public Service Workload Narrative Assistant

An end-to-end, privacy-first GenAI web application that transforms municipal public service request logs into executive administrative workload reports, completed-vs-remaining backlog tracking, and anonymized government worker accountability audits.

---

## 4-Layer Privacy-First System Architecture

```text
[Layer 1: Data Ingestion & React UI]
   CSV / JSON Upload or 640+ Row Synthetic Generator
        │
        ▼
[Layer 2: Zero-Trust PII Shield  (backend/privacy_analytics.py)]
   • Strict allowlist column firewall drops citizen_name, phone, email, address, free_text
   • Inline regex scrubber strips accidental emails, phones, street addresses, SSNs, IPs
   • Worker ID anonymizer enforces DEPT-NNN format (e.g., ENG-042, SAN-108) via SHA-256
   • Generates auditable PII Receipt (post-shield verification = 0 leaks)
        │
        ▼
[Layer 3: Pandas & NumPy Analytics Engine  (backend/privacy_analytics.py)]
   • Time-period intake, completed vs. remaining backlog, & linear NumPy projections
   • Department / service category SLA compliance & turnaround percentiles (avg/med/p90)
   • Worker accountability roster with peer workload z-scores & standardized action rollups
        │
        ▼
[Layer 4: Gemini Cognitive Engine + Guardrails  (backend/llm_engine.py)]
   • Pre-Flight Firewall: asserts zero forbidden keys or PII patterns in aggregated JSON
   • Gemini API (google-genai) or Data-Grounded Deterministic Fallback synthesis
   • Post-Output Guardrail: scans narrative for zero PII + verifies worker ID grounding
   • Executive ReportLab PDF Export (backend/pdf_generator.py)
```

---

## Strict Privacy Guarantees

1. **Zero Citizen PII Anywhere Beyond Layer 2:** Columns such as `citizen_name`, `citizen_phone`, `citizen_email`, `street_address`, and `free_text_complaint` are immediately discarded on ingest.
2. **Inline Scrubbing:** Operational columns (`action_taken`, `district_zone`, `request_id`) are scrubbed with compiled regex detectors for emails, phone numbers, street addresses, titles/names, SSNs, and IPv4 strings.
3. **Anonymized Personnel Only:** Only anonymized worker tokens (`ENG-042`, `SAN-108`, `WTR-019`, etc.) are retained. Raw staff identifiers uploaded via CSV are deterministically hashed into `<DEPT>-<NNN>` format.
4. **No Raw Rows Sent to LLM:** Layer 4 serializes strictly aggregated JSON metrics and anonymized audit summaries, verifiable directly in the UI via **"Inspect Sanitized LLM Input"**.

---

## Repository Structure

```text
ps158-workload-assistant/
├── backend/
│   ├── main.py                  # FastAPI server & REST endpoints
│   ├── privacy_analytics.py     # Layer 2 (PII Shield) + Layer 3 (Pandas/NumPy engine)
│   ├── llm_engine.py            # Layer 4 (Gemini API Cognitive Engine + Guardrails)
│   ├── pdf_generator.py         # ReportLab executive PDF export
│   ├── generate_sample_data.py  # Synthetic dataset generator (500+ rows)
│   ├── tests/test_pipeline.py   # Automated verification suite
│   ├── .env.example             # Gemini API key template
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Main Dashboard UI
│   │   ├── api.js               # Typed API client
│   │   └── components/          # ArchitectureBanner, DataUploadBar, KpiCards,
│   │                            # WorkloadCharts, WorkerAuditTable, AiNarrativePanel,
│   │                            # PrivacyShieldModal
│   └── package.json
├── start.ps1                    # Single start script (Windows PowerShell)
├── start.sh                     # Single start script (Linux/macOS)
└── README.md
```

---

## Quick Start

### 1. Configure Environment (Optional for Live Gemini Mode)
Copy `backend/.env.example` to `backend/.env` and set `GEMINI_API_KEY`:
```env
GEMINI_API_KEY=your_google_ai_studio_key
GEMINI_MODEL=gemini-2.5-flash
```
> If `GEMINI_API_KEY` is omitted, Layer 4 automatically runs in **Data-Grounded Deterministic Fallback** mode so all analytics, guardrails, and PDF exports remain fully operational offline. You can also enter a session key directly in the UI.

### 2. Run with Single Start Script
On Windows (PowerShell):
```powershell
.\start.ps1
```
On macOS/Linux:
```bash
chmod +x start.sh && ./start.sh
```
This launches:
- **FastAPI Backend:** `http://127.0.0.1:8000` (Swagger docs at `/docs`)
- **React Dashboard:** `http://localhost:5173` (or served at `:8000` if `frontend/dist` is built)

### 3. Generate Sample Data or Run Tests
```powershell
cd backend
python generate_sample_data.py --rows 640
pytest -v
```

