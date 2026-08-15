<div align="center">

# ⚡ LOCAL SEARCH INFERENCE & SERP API
### *High-Performance, Open-Source & Self-Hosted Search Inference Engine*

[![Python Version](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask REST API](https://img.shields.io/badge/Flask-REST%20API-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)
[![Cost](https://img.shields.io/badge/Cost-$0%20Free-emerald?style=for-the-badge&logo=cashapp&logoColor=white)]()
[![Privacy](https://img.shields.io/badge/Privacy-100%25%20Local-blueviolet?style=for-the-badge&logo=lock&logoColor=white)]()
[![Build](https://img.shields.io/badge/Standalone%20EXE-Ready-orange?style=for-the-badge&logo=windows&logoColor=white)]()

<br/>

<p align="center">
  <b>A drop-in, zero-cost, privacy-first alternative to expensive cloud SERP APIs (SerpApi, Serper, BrightData).</b><br/>
  Empower your <b>AI Agents</b>, <b>RAG Pipelines</b>, <b>LLM tools</b>, <b>scrapers</b>, and <b>lead gen workflows</b> with unlimited local search inferencing.
</p>

<p align="center">
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-why-local-serp-api">Why This Engine?</a> •
  <a href="#-rest-api-documentation">REST API Specs</a> •
  <a href="#-bonus-lead-gen--contact-extractor">Lead Gen Bonus</a> •
  <a href="#-python-sdk-usage">Python SDK</a> •
  <a href="#-web-dashboard">Web Studio</a>
</p>

---

</div>

<br/>

## 🌟 Overview

**Local Search Inference** is a lightweight, local-first search execution engine and SERP (Search Engine Results Page) API server. It allows developers to programmatically execute web search queries, fetch real-time structured rankings (titles, URLs, snippets), parse arbitrary text for contacts, and build autonomous agents—**without paid subscriptions, rate limits, or API key barriers**.

```
                           ┌───────────────────────────────┐
                           │   AI Agents / RAG / Scripts   │
                           └───────────────┬───────────────┘
                                           │  HTTP POST / JSON
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        LOCAL SEARCH INFERENCE ENGINE (:5000)                           │
│                                                                                        │
│  ┌──────────────────────────┐  ┌──────────────────────────┐  ┌───────────────────────┐  │
│  │   DuckDuckGo Inference   │  │    Official Google API   │  │  Direct HTML Scraper  │  │
│  │  (Zero-Key / Unlimited)  │  │  (Cloud CSE / Key / CX)  │  │ (Fallback Web Parser) │  │
│  └─────────────┬────────────┘  └────────────┬─────────────┘  └───────────┬───────────┘  │
│                │                            │                            │              │
│                └────────────────────┬───────┴────────────────────────────┘              │
│                                     ▼                                                   │
│                        Structured SERP Output (JSON)                                    │
│                                     │                                                   │
│                     ┌───────────────┴───────────────┐                                   │
│                     ▼                               ▼                                   │
│       Raw SERP Results / JSON          Contact & Lead Extraction Pipeline               │
│                                        (Email Parser, Deduplication, CSV DB)            │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🥊 Comparison: Local Engine vs. Cloud SERP APIs

| Feature | 🚫 Cloud SERP APIs (SerpApi / Serper) | ⚡ Local Search Inference (This Tool) |
| :--- | :--- | :--- |
| **Pricing** | $50 - $500 / month | **$0.00 (100% Free & Open Source)** |
| **API Keys** | Mandatory signup & credit card | **None required (Default DDG Engine)** |
| **Query Limits** | Capped monthly credits | **Unlimited Local Execution** |
| **Data Privacy** | All queries logged by third-party | **100% Local on your machine/server** |
| **Built-in Contact Parser** | ❌ No (Requires custom code) | **✅ Yes (Regex + Obfuscation Decoder)** |
| **Platform Dorking** | ❌ No | **✅ Yes (Instagram, LinkedIn, X, etc.)** |
| **Visual Testing Studio** | Basic / Cloud console | **✅ Built-in Glassmorphism Web UI** |

---

## 🚀 Quick Start

### 1. Installation

Clone repository and install dependencies:

```bash
git clone https://github.com/paulfruitful/mail-lead-gen.git
cd mail-lead-gen

# Install core packages
pip install flask requests beautifulsoup4 duckduckgo-search
```

### 2. Launch Local SERP API Server

```bash
python app.py
```

* 🌐 **Interactive Studio & Web UI**: `http://127.0.0.1:5000/`
* 📖 **OpenAPI JSON Spec**: `http://127.0.0.1:5000/api/docs`
* 🩺 **Health & Metrics**: `http://127.0.0.1:5000/api/health`

---

## ⚡ Direct Search Inferencing (CLI & API)

### CLI One-Liners

```bash
# Basic search (DuckDuckGo engine, 5 results)
python search.py "latest artificial intelligence papers" -n 5

# JSON formatted search output (perfect for piping into jq, scripts, or LLMs)
python search.py "site:github.com local serp api" --json

# Official Google Custom Search API mode
python search.py "quantum computing" --method api --key "YOUR_KEY" --cx "YOUR_CX" -n 10
```

---

## 📡 REST API Documentation

The server exposes low-latency endpoints for direct inferencing, extraction, and database management.

<details open>
<summary><b>1. Direct Search Endpoint (<code>POST /api/search</code>)</b></summary>

Execute search queries across engines and receive structured SERP data.

```bash
curl -X POST http://127.0.0.1:5000/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "fastapi vs flask 2026 benchmarks",
    "method": "ddg",
    "num_results": 10
  }'
```

**Response (`200 OK`):**
```json
{
  "success": true,
  "query": "fastapi vs flask 2026 benchmarks",
  "method": "ddg",
  "count": 10,
  "results": [
    {
      "position": 1,
      "title": "FastAPI vs Flask Performance Review",
      "link": "https://example.com/benchmark",
      "snippet": "In-depth speed comparisons between asynchronous FastAPI and Flask..."
    }
  ]
}
```
</details>

<details>
<summary><b>2. Direct Text Contact Extractor (<code>POST /api/extract/text</code>)</b></summary>

Extract email addresses from arbitrary text snippets, HTML strings, or bio data (automatically decodes `[at]`, `(at)` obfuscations).

```bash
curl -X POST http://127.0.0.1:5000/api/extract/text \
  -H "Content-Type: application/json" \
  -d '{
    "text": "For developer inquiries contact support@api.io or alex.dev [at] gmail.com."
  }'
```

**Response (`200 OK`):**
```json
{
  "success": true,
  "count": 2,
  "emails": [
    "alex.dev@gmail.com",
    "support@api.io"
  ]
}
```
</details>

<details>
<summary><b>3. Search Results Email Parser (<code>POST /api/extract/results</code>)</b></summary>

Pass structured SERP result objects to extract contacts and map them directly to their source URLs.

```bash
curl -X POST http://127.0.0.1:5000/api/extract/results \
  -H "Content-Type: application/json" \
  -d '{
    "results": [
      {
        "title": "Bio",
        "link": "https://x.com/creator",
        "snippet": "AI Builder & Founder. Inquiries: founder@startup.co"
      }
    ]
  }'
```
</details>

<details>
<summary><b>4. End-to-End Search & Lead Gen Pipeline (<code>POST /api/leadgen</code>)</b></summary>

One-shot inferencing: runs web search, parses contacts, maps URLs, deduplicates against local database, and updates `emails.csv`.

```bash
curl -X POST http://127.0.0.1:5000/api/leadgen \
  -H "Content-Type: application/json" \
  -d '{
    "query": "site:twitter.com \"machine learning engineer\" \"@gmail.com\"",
    "num_results": 50,
    "method": "ddg",
    "save_to_csv": true
  }'
```
</details>

<details>
<summary><b>5. Social Platform Dork Inferencing (<code>POST /api/leadgen/platform</code>)</b></summary>

Generates platform-specific dorks automatically and executes lead extraction.

```bash
curl -X POST http://127.0.0.1:5000/api/leadgen/platform \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "linkedin",
    "niche": "cloud architect",
    "num_results": 50,
    "save_to_csv": true
  }'
```

*Supported platforms:* `instagram`, `linkedin`, `twitter`, `facebook`, `tiktok`, `youtube`, `onlyfans`, `patreon`, `linktree`.
</details>

<details>
<summary><b>6. Database Leads Management (<code>GET</code>, <code>POST</code>, <code>DELETE /api/leads</code>)</b></summary>

* **List Stored Leads:** `GET /api/leads?q=gmail&page=1&limit=50`
* **Insert Leads Manually:** `POST /api/leads` with `{"emails": ["lead@domain.com"]}`
* **Delete Lead or Clear DB:** `DELETE /api/leads` with `{"email": "lead@domain.com"}` or `{"clear_all": true}`
* **Download Raw Database:** `GET /api/leads/export` (CSV file) or `GET /api/leads/export?format=json`
</details>

---

## 🎁 Bonus: Lead Gen & Contact Extraction Engine

While this engine functions as a generic local SERP API, it includes a dedicated, battle-tested contact extraction pipeline:

1. **Interactive Terminal TUI Controller (`controller.py`)**:
   ```bash
   python controller.py
   ```
   Select from 10 platform presets, enter your niche, and watch it stream and deduplicate verified email leads into `emails.csv`.

2. **Dork Extraction CLI (`extract_emails.py`)**:
   ```bash
   # Live query extraction
   python extract_emails.py --query 'site:github.com "maintainer" "@gmail.com"' -n 50 --output emails.csv

   # Parse from cached JSON
   python extract_emails.py --file results.json --output emails.csv
   ```

---

## 💻 Python SDK Usage

Import search and extraction methods directly into your Python scripts:

```python
import search
import extract_emails

# 1. Execute direct search inference (returns list of result dicts)
results = search.search_ddg("autonomous ai agents github", num_results=10)
for r in results:
    print(f"[{r['position']}] {r['title']} -> {r['link']}")

# 2. Extract emails from raw text
emails = extract_emails.extract_emails_from_text("Say hello at dev (at) python.org or team@ai.com")
print("Extracted emails:", emails)

# 3. Parse search results with source URL mapping
lead_map = extract_emails.parse_results(results)
print("Mapped leads:", lead_map)
```

---

## 🖥 Web Dashboard & Testing Studio

Start `python app.py` and open **`http://127.0.0.1:5000/`** to access the built-in UI:

* 🎯 **Platform Lead Studio** — Select target social channels, input niche, and trigger automated searches.
* ⚡ **Custom Dork Studio** — Compose advanced search queries and monitor incoming matches in real time.
* 🔍 **Text Parser Studio** — Paste scraped HTML or text blobs to test regex extraction.
* 🌐 **Raw SERP Explorer** — Inspect structured title/link/snippet JSON payloads.
* 🗄 **Leads Database Manager** — Search, view, delete, and download stored CSV leads.

---

## 🧪 Testing & Verification

Run the automated test suite to verify search parsing, API routes, and database operations:

```bash
python test_app.py
```

```text
Ran 9 tests in 0.18s
OK (All endpoints, regex parsing, and CRUD verified)
```

---

## 📦 Building Standalone Executable (Windows)

Compile into a single standalone `.exe` that runs without requiring Python installed:

```powershell
.\build.ps1
```
The compiled binary will be placed in `.\dist\MailLeadGen.exe`.

---

## 📜 License

Distributed under the **MIT License**. Free for personal, academic, and commercial use.
