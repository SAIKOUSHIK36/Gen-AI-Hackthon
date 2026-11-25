# Gen-AI Hackathon Projects

Two full-stack GenAI web applications built for the hackathon.

---

## 📁 Project 1: PS 158 — Public Service Workload Narrative Assistant

**Location:** `ps158-workload-assistant/`

A privacy-first municipal workload analytics system that processes public service request data to generate executive administrative reports.

### Key Features
- 🛡️ **Zero-Trust PII Shield** — Zero citizen data ever reaches the LLM
- 📊 **Pandas/NumPy Analytics Engine** — Completed vs remaining work tracking
- 🤖 **Gemini AI Narrative Engine** — Natural language executive reports
- 📄 **PDF Export** — ReportLab executive PDF reports
- 🗺️ **Real-world DC 311 CSV support** — Flexible column auto-mapping

### Tech Stack
- **Backend:** FastAPI, Python, Pandas, NumPy, Google Gemini API, ReportLab
- **Frontend:** React, Vite, Tailwind CSS, Recharts

### Quick Start
```powershell
cd ps158-workload-assistant
powershell -ExecutionPolicy Bypass -File start.ps1
```
Then open: http://localhost:5173

---

## 📁 Project 2: CivicPulse AI — Complaint Resolution & Delay Analysis

**Location:** `civicpulse-ai/`

An intelligent public complaint analysis system that helps government departments understand their complaint resolution performance and identify delay patterns.

### Key Features
- 📂 **CSV/Excel Upload** — Upload any complaint dataset
- ✅ **Instant Results** — Pending / Solved / Overdue counts at a glance
- 🔍 **AI Delay Analysis** — Evidence-based delay reason detection (RECORDED vs INFERRED vs INSUFFICIENT)
- 🏛️ **Department Performance** — Identify departments needing attention
- 💬 **Ask CivicPulse AI** — Conversational Q&A about your data
- 📄 **AI Administrative Reports** — Gemini-powered PDF reports
- 🔒 **Privacy Shield** — Automatic citizen PII removal

### Tech Stack
- **Backend:** FastAPI, Python, Pandas, Scikit-learn (Isolation Forest), Google Gemini API, ReportLab, SQLite
- **Frontend:** React, Vite, Tailwind CSS, Recharts

### Quick Start
```powershell
cd civicpulse-ai
powershell -ExecutionPolicy Bypass -File start.ps1
```
Then open: http://localhost:5173

### Supported CSV Columns
| Column | Description |
|--------|-------------|
| `Status` | Complaint status (Resolved / Pending / In Progress) |
| `Category` | Type of complaint |
| `Department` | Responsible department |
| `Delay_Reason` | Recorded reason for delay (optional) |
| `Deadline` | Resolution deadline |
| `Date_Received` | Date complaint was filed |
| `Priority` | Priority level |

---

## Setup — Gemini API Key (Optional but recommended)

Both projects work without a Gemini API key (deterministic fallback mode). To enable AI-powered narratives:

1. Get a free key at: https://aistudio.google.com/app/apikey
2. Create a `.env` file in the backend folder:
   ```
   GEMINI_API_KEY=AIza...your-key-here
   ```

---

## Privacy Commitment

> ⚠️ Neither application ever processes, stores, or transmits citizen PII (names, phone numbers, email addresses, home addresses). All data is anonymized at the ingestion layer before any analysis or AI processing.

