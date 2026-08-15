# Google & DuckDuckGo Search Script

This is a Python utility that lets you programmatically query search engines and return structured results (title, link, and description/snippet). 

Since Google actively blocks direct automated scraping using CAPTCHAs and JavaScript redirections, this script provides three distinct execution strategies to suit different environments and requirements:

---

## Features & Search Methods

### 1. DuckDuckGo Search (`--method ddg` - Default)
*   **Cost**: Free
*   **API Key**: None required
*   **Reliability**: High (Uses the `duckduckgo-search` package)
*   **Description**: Queries DuckDuckGo, which provides highly relevant results similar to Google without aggressive rate-limiting or anti-bot checks. Perfect for local prototyping, CLI scripting, and testing.

### 2. Official Google Custom Search API (`--method api`)
*   **Cost**: Free (up to 100 queries/day), paid for higher volumes
*   **API Key**: Required
*   **Reliability**: 100% stable
*   **Description**: The officially supported and robust way to search Google programmatically. It requires a Google Cloud API Key and a Programmable Search Engine ID (CX).

### 3. Direct Google HTML Scraper (`--method scrape`)
*   **Cost**: Free
*   **API Key**: None required
*   **Reliability**: Extremely Low
*   **Description**: Fetches Google Search directly using `requests` and parses with `BeautifulSoup`. **Note**: Google will frequently block this strategy with a CAPTCHA screen or require browser-like JavaScript execution, resulting in empty responses. It is kept for educational/demonstrative purposes.

---

## Installation

Ensure you have Python 3 installed. Then, install the required packages:

```bash
pip install requests beautifulsoup4 duckduckgo-search
```

---

## Usage

### Simple CLI Search (Using DuckDuckGo - Default)
```bash
python search.py "python programming" -n 5
```

### Official Google Custom Search API
To use the official Google Search API, you need:
1. A **Google Custom Search API Key** (obtainable from the [Google Cloud Console](https://console.cloud.google.com/)).
2. A **Search Engine ID (CX)** (created via the [Google Custom Search Engine Console](https://cse.google.com/cse/)). Make sure you configure the search engine to search the entire web rather than a specific site.

Run the search using your credentials:
```bash
python search.py "python programming" --method api --key "YOUR_GOOGLE_API_KEY" --cx "YOUR_SEARCH_ENGINE_ID" -n 5
```

### JSON Structured Output
To return raw JSON (great for integration into other scripts or saving to files):
```bash
python search.py "python programming" --json
```

Output format:
```json
[
  {
    "position": 1,
    "title": "Welcome to Python.org",
    "link": "https://www.python.org/",
    "snippet": "The official home of the Python Programming Language..."
  },
  ...
]
```

### Help Menu
To view all available options:
```bash
python search.py --help
```

---

## Email Extraction (`extract_emails.py`)

This helper script parses the search results (from an existing JSON file or by running a live query) and extracts unique email addresses using regular expressions. It can also save them to a text file.

### 1. Extract Emails from a Live Search Query:
This runs the search query, fetches the results, parses them, and prints any extracted email addresses along with their source URLs:
```bash
python extract_emails.py --query 'site:twitch.com * "@gmail.com"' -n 50
```

### 2. Extract Emails from a Pre-saved JSON File:
This lets you run searches independently and parse the cached file:
```bash
# Step 1: Save search results to a JSON file
python search.py 'site:twitch.com * "@gmail.com"' -n 50 --json > results.json

# Step 2: Extract emails from the JSON file
python extract_emails.py --file results.json
```

### 3. Save Extracted Emails to a CSV File:
To output a clean, unique list of email addresses directly to a CSV file (where each row contains a single email), use the `--output` argument (which defaults to `emails.csv` if omitted):
```bash
python extract_emails.py --query 'site:twitch.com * "@gmail.com"' -n 100 --output emails.csv
```---

## Flask Direct Inferencing REST API (`app.py`)

A full-featured, lightweight REST API server built with Flask that exposes direct inferencing endpoints for web search, text email extraction, search result parsing, automated platform dorking, and lead database management.

### Starting the Server

```bash
# Install Flask if not already installed
pip install flask

# Start the Flask API server (runs on port 5000 by default)
python app.py

# Or specify custom host, port, or debug mode
python app.py --host 0.0.0.0 --port 5000 --debug
```

Once running, access:
* **Interactive Studio & Web UI**: [http://127.0.0.1:5000/](http://127.0.0.1:5000/)
* **OpenAPI Documentation**: [http://127.0.0.1:5000/api/docs](http://127.0.0.1:5000/api/docs)
* **Health & Stats**: [http://127.0.0.1:5000/api/health](http://127.0.0.1:5000/api/health)

---

### REST API Endpoints

#### 1. Direct Search (`POST /api/search`)
Query DuckDuckGo, Google API, or direct scraper programmatically.
```bash
curl -X POST http://127.0.0.1:5000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "python backend engineer", "method": "ddg", "num_results": 10}'
```

#### 2. Direct Text Email Extractor (`POST /api/extract/text`)
Extract emails directly from raw text strings (handles email obfuscations such as `[at]` or `(at)`).
```bash
curl -X POST http://127.0.0.1:5000/api/extract/text \
  -H "Content-Type: application/json" \
  -d '{"text": "Contact our sales team at sales@company.com or founder (at) startup.io"}'
```

#### 3. Search Results Extractor (`POST /api/extract/results`)
Parse structured search results and map extracted emails to source URLs.
```bash
curl -X POST http://127.0.0.1:5000/api/extract/results \
  -H "Content-Type: application/json" \
  -d '{"results": [{"title": "Bio", "link": "https://twitter.com/dev", "snippet": "Email: dev@gmail.com"}]}'
```

#### 4. End-to-End Lead Generation Pipeline (`POST /api/leadgen`)
Executes search query, parses emails, maps sources, deduplicates against database, and optionally appends new leads to `emails.csv`.
```bash
curl -X POST http://127.0.0.1:5000/api/leadgen \
  -H "Content-Type: application/json" \
  -d '{
    "query": "site:instagram.com \"fitness trainer\" \"@gmail.com\"",
    "num_results": 50,
    "method": "ddg",
    "save_to_csv": true
  }'
```

#### 5. Platform Preset Lead Gen (`POST /api/leadgen/platform`)
Automatically constructs dorks and executes lead extraction for supported platforms (`instagram`, `linkedin`, `twitter`, `facebook`, `tiktok`, `youtube`, `onlyfans`, `patreon`, `linktree`).
```bash
curl -X POST http://127.0.0.1:5000/api/leadgen/platform \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "linkedin",
    "niche": "real estate agent",
    "num_results": 30,
    "save_to_csv": true
  }'
```

#### 6. Database Leads Management (`GET`, `POST`, `DELETE /api/leads`)
* **List leads (with search & pagination)**:
  ```bash
  curl "http://127.0.0.1:5000/api/leads?page=1&limit=50&q=gmail"
  ```
* **Add lead manually**:
  ```bash
  curl -X POST http://127.0.0.1:5000/api/leads \
    -H "Content-Type: application/json" \
    -d '{"emails": ["partner@company.com"]}'
  ```
* **Delete lead or clear database**:
  ```bash
  curl -X DELETE http://127.0.0.1:5000/api/leads \
    -H "Content-Type: application/json" \
    -d '{"email": "partner@company.com"}'
  ```
* **Export CSV**:
  ```bash
  curl -O http://127.0.0.1:5000/api/leads/export
  ```

---

## Running Automated Tests

```bash
python test_app.py
```
