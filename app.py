#!/usr/bin/env python3
"""
Mail Lead Gen - Flask Direct Inferencing API Server

Provides REST API endpoints for:
- Direct search inferencing (DDG, Google API, Scraper)
- Regex-based text email extraction
- Search result email extraction & URL mapping
- End-to-end Lead Generation pipeline
- Platform Dork generator (Instagram, LinkedIn, Twitter/X, TikTok, YouTube, etc.)
- Database (CSV) leads management (CRUD & Export)
"""

import sys
import os
import csv
import json
import re
import argparse
from typing import List, Dict, Any, Set, Optional
from flask import Flask, request, jsonify, render_template_string, send_file, Response

# Ensure UTF-8 stdout on Windows
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass

# Ensure directory is on path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import search
import extract_emails

app = Flask(__name__)
DEFAULT_CSV_PATH = os.path.join(SCRIPT_DIR, "emails.csv")

# Supported Platform configurations
PLATFORMS = {
    "instagram": {
        "id": "instagram",
        "name": "Instagram",
        "domain": "instagram.com",
        "description": "Extract creator, influencer, and business emails from Instagram profiles and posts",
        "default_providers": ["@gmail.com", "@yahoo.com", "@hotmail.com", "@outlook.com"]
    },
    "linkedin": {
        "id": "linkedin",
        "name": "LinkedIn",
        "domain": "linkedin.com",
        "description": "Extract professional and business emails from LinkedIn profiles",
        "default_providers": ["@gmail.com", "@yahoo.com", "@hotmail.com", "@outlook.com"]
    },
    "twitter": {
        "id": "twitter",
        "name": "Twitter / X",
        "domain": "twitter.com",
        "description": "Extract emails from bios, tweets, and creator profiles on Twitter / X",
        "default_providers": ["@gmail.com", "@yahoo.com", "@hotmail.com", "@outlook.com"]
    },
    "facebook": {
        "id": "facebook",
        "name": "Facebook",
        "domain": "facebook.com",
        "description": "Extract emails from public pages, groups, and business accounts on Facebook",
        "default_providers": ["@gmail.com", "@yahoo.com", "@hotmail.com", "@outlook.com"]
    },
    "tiktok": {
        "id": "tiktok",
        "name": "TikTok",
        "domain": "tiktok.com",
        "description": "Extract creator and influencer contact emails from TikTok bios and video captions",
        "default_providers": ["@gmail.com", "@yahoo.com", "@hotmail.com", "@outlook.com"]
    },
    "youtube": {
        "id": "youtube",
        "name": "YouTube",
        "domain": "youtube.com",
        "description": "Extract creator business inquiries from YouTube channel descriptions and 'About' sections",
        "default_providers": ["@gmail.com", "@yahoo.com", "@hotmail.com", "@outlook.com"]
    },
    "onlyfans": {
        "id": "onlyfans",
        "name": "OnlyFans (Creator)",
        "domain": "onlyfans.com",
        "description": "Extract creator and model emails associated with OnlyFans profiles",
        "default_providers": ["@gmail.com", "@yahoo.com", "@hotmail.com", "@outlook.com"]
    },
    "patreon": {
        "id": "patreon",
        "name": "Patreon (Creator)",
        "domain": "patreon.com",
        "description": "Extract creator and patron community emails from Patreon pages",
        "default_providers": ["@gmail.com", "@yahoo.com", "@hotmail.com", "@outlook.com"]
    },
    "linktree": {
        "id": "linktree",
        "name": "Linktree (Creator)",
        "domain": "linktr.ee",
        "description": "Extract bio link contact emails aggregated on Linktree profiles",
        "default_providers": ["@gmail.com", "@yahoo.com", "@hotmail.com", "@outlook.com"]
    }
}


# ==========================================
# Helper Functions
# ==========================================

def resolve_csv_path(custom_path: Optional[str] = None) -> str:
    """Resolve the absolute path to the CSV leads database."""
    if custom_path:
        if os.path.isabs(custom_path):
            return custom_path
        return os.path.join(SCRIPT_DIR, custom_path)
    return DEFAULT_CSV_PATH


def load_seen_emails(csv_path: Optional[str] = None) -> Set[str]:
    """Load already discovered emails from the CSV file as a set of lowercase strings."""
    path = resolve_csv_path(csv_path)
    seen = set()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                for row in reader:
                    if row and row[0].strip():
                        email = row[0].strip().lower()
                        # validate it's an email format
                        if extract_emails.EMAIL_REGEX.match(email):
                            seen.add(email)
        except Exception as e:
            print(f"[!] Error reading {path}: {e}", file=sys.stderr)
    return seen


def save_new_emails(new_emails: Set[str], csv_path: Optional[str] = None) -> int:
    """Append new unique emails to the CSV database. Returns the number of emails added."""
    if not new_emails:
        return 0
    path = resolve_csv_path(csv_path)
    existing = load_seen_emails(path)
    to_add = [e.lower().strip() for e in new_emails if e.lower().strip() not in existing]
    if not to_add:
        return 0
    
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        for email in sorted(to_add):
            writer.writerow([email])
    return len(to_add)


def delete_emails_from_db(emails_to_remove: Set[str], csv_path: Optional[str] = None) -> int:
    """Remove specific emails from the CSV database. Returns number of removed emails."""
    path = resolve_csv_path(csv_path)
    if not os.path.exists(path):
        return 0
    existing = load_seen_emails(path)
    to_remove = {e.lower().strip() for e in emails_to_remove}
    remaining = existing - to_remove
    removed_count = len(existing) - len(remaining)
    
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        for email in sorted(remaining):
            writer.writerow([email])
    return removed_count


def clear_all_emails(csv_path: Optional[str] = None) -> int:
    """Clear all records from the CSV database."""
    path = resolve_csv_path(csv_path)
    if not os.path.exists(path):
        return 0
    existing = load_seen_emails(path)
    count = len(existing)
    with open(path, "w", encoding="utf-8", newline="") as f:
        pass
    return count


def execute_search(query: str, method: str = "ddg", num_results: int = 10,
                   key: Optional[str] = None, cx: Optional[str] = None) -> List[Dict[str, Any]]:
    """Execute search query using specified engine method."""
    method = method.lower() if method else "ddg"
    if method == "api":
        if not key or not cx:
            raise ValueError("The 'api' method requires both 'key' (Google API Key) and 'cx' (Google Search Engine ID).")
        return search.search_api(query, key, cx, num_results=num_results)
    elif method == "scrape":
        return search.search_scrape(query, num_results=num_results)
    else:
        return search.search_ddg(query, num_results=num_results)


def build_platform_dork(platform_key: str, niche: str, providers: Optional[List[str]] = None) -> str:
    """Construct a Google/DDG dork query for a specific platform and niche."""
    platform_key = platform_key.lower().strip()
    if platform_key not in PLATFORMS:
        raise ValueError(f"Unknown platform '{platform_key}'. Available: {list(PLATFORMS.keys())}")
    
    config = PLATFORMS[platform_key]
    domain = config["domain"]
    
    if not providers:
        providers = config["default_providers"]
        
    formatted_providers = " OR ".join([f'"{p.strip()}"' if not p.startswith('"') else p.strip() for p in providers if p.strip()])
    if not formatted_providers:
        formatted_providers = '"@gmail.com" OR "@yahoo.com" OR "@hotmail.com" OR "@outlook.com"'
        
    return f'site:{domain} "{niche.strip()}" {formatted_providers}'


# ==========================================
# CORS and Response Handling
# ==========================================

@app.after_request
def apply_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With, Accept"
    return response


@app.errorhandler(404)
def not_found(e):
    return jsonify({"success": False, "error": "Endpoint not found"}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"success": False, "error": f"Internal server error: {str(e)}"}), 500


# ==========================================
# REST API Endpoints
# ==========================================

@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint providing status and database stats."""
    db_count = len(load_seen_emails())
    return jsonify({
        "success": True,
        "status": "healthy",
        "service": "Mail Lead Gen Inferencing API",
        "version": "1.0.0",
        "database": {
            "leads_count": db_count,
            "csv_path": DEFAULT_CSV_PATH,
            "exists": os.path.exists(DEFAULT_CSV_PATH)
        },
        "platforms_supported": list(PLATFORMS.keys())
    })


@app.route("/api/platforms", methods=["GET"])
def get_platforms():
    """List all supported social/creator platforms and their default search configurations."""
    return jsonify({
        "success": True,
        "count": len(PLATFORMS),
        "platforms": PLATFORMS
    })


@app.route("/api/search", methods=["POST", "OPTIONS"])
def search_endpoint():
    """
    Direct Search Inferencing Endpoint.
    Runs web searches via DuckDuckGo, Google API, or Google Scraper.
    
    Request JSON:
    {
        "query": "python developer @gmail.com",  (required)
        "method": "ddg",                        (optional, 'ddg'|'api'|'scrape', default 'ddg')
        "num_results": 20,                       (optional, default 10, max 200)
        "key": "GOOGLE_API_KEY",                (optional, required for 'api')
        "cx": "GOOGLE_CX"                       (optional, required for 'api')
    }
    """
    if request.method == "OPTIONS":
        return jsonify({"success": True}), 200

    data = request.get_json(silent=True) or {}
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"success": False, "error": "Missing required field: 'query'"}), 400

    method = data.get("method", "ddg").lower()
    num_results = min(int(data.get("num_results", 10)), 200)
    key = data.get("key")
    cx = data.get("cx")

    try:
        results = execute_search(query, method=method, num_results=num_results, key=key, cx=cx)
        return jsonify({
            "success": True,
            "query": query,
            "method": method,
            "count": len(results),
            "results": results
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/extract/text", methods=["POST", "OPTIONS"])
def extract_text_endpoint():
    """
    Extract email addresses directly from arbitrary text strings or scraped snippets.
    
    Request JSON:
    {
        "text": "For partnerships email contact@company.com or ceo [at] brand.co"
    }
    """
    if request.method == "OPTIONS":
        return jsonify({"success": True}), 200

    data = request.get_json(silent=True) or {}
    text = data.get("text", "")
    if not text:
        return jsonify({"success": False, "error": "Missing or empty field: 'text'"}), 400

    emails = extract_emails.extract_emails_from_text(text)
    return jsonify({
        "success": True,
        "count": len(emails),
        "emails": sorted(list(emails))
    })


@app.route("/api/extract/results", methods=["POST", "OPTIONS"])
def extract_results_endpoint():
    """
    Extract emails from structured search result objects and map each email to its source URLs.
    
    Request JSON:
    {
        "results": [
            {"title": "Dev Bio", "link": "https://example.com/bio", "snippet": "Reach me at dev@mail.com"}
        ]
    }
    """
    if request.method == "OPTIONS":
        return jsonify({"success": True}), 200

    data = request.get_json(silent=True) or {}
    results = data.get("results")
    if results is None or not isinstance(results, list):
        return jsonify({"success": False, "error": "Missing or invalid field: 'results' (must be a JSON array)"}), 400

    email_map = extract_emails.parse_results(results)
    
    # Format for JSON response
    formatted_map = {email: sorted(list(sources)) for email, sources in email_map.items()}
    
    return jsonify({
        "success": True,
        "count": len(formatted_map),
        "emails": formatted_map
    })


@app.route("/api/leadgen", methods=["POST", "OPTIONS"])
def leadgen_pipeline_endpoint():
    """
    One-Shot Lead Generation Inferencing Pipeline.
    Runs search -> extracts emails & source URLs -> deduplicates against database -> optionally saves to CSV.
    
    Request JSON:
    {
        "query": "site:instagram.com \"fitness coach\" \"@gmail.com\"", (required)
        "num_results": 50,                                             (optional, default 50)
        "method": "ddg",                                               (optional, 'ddg'|'api'|'scrape')
        "key": "GOOGLE_API_KEY",                                       (optional)
        "cx": "GOOGLE_CX",                                             (optional)
        "save_to_csv": true,                                           (optional, default true)
        "csv_path": "emails.csv",                                      (optional)
        "deduplicate": true                                            (optional, default true)
    }
    """
    if request.method == "OPTIONS":
        return jsonify({"success": True}), 200

    data = request.get_json(silent=True) or {}
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"success": False, "error": "Missing required field: 'query'"}), 400

    num_results = min(int(data.get("num_results", 50)), 200)
    method = data.get("method", "ddg").lower()
    key = data.get("key")
    cx = data.get("cx")
    save_to_csv = data.get("save_to_csv", True)
    csv_path = data.get("csv_path")
    deduplicate = data.get("deduplicate", True)

    try:
        # Step 1: Perform Search
        results = execute_search(query, method=method, num_results=num_results, key=key, cx=cx)
        
        # Step 2: Extract Emails and Map Sources
        email_map = extract_emails.parse_results(results)
        
        # Step 3: Deduplicate against CSV database
        seen_emails = load_seen_emails(csv_path) if deduplicate else set()
        new_emails = set(email_map.keys()) - seen_emails if deduplicate else set(email_map.keys())
        
        # Step 4: Save new leads to CSV if requested
        saved_count = 0
        if save_to_csv and new_emails:
            saved_count = save_new_emails(new_emails, csv_path)

        # Step 5: Format response leads
        leads_list = []
        for email, sources in sorted(email_map.items()):
            leads_list.append({
                "email": email,
                "sources": sorted(list(sources)),
                "is_new": email in new_emails
            })

        total_db_count = len(load_seen_emails(csv_path))

        return jsonify({
            "success": True,
            "query": query,
            "method": method,
            "total_search_results": len(results),
            "total_emails_found": len(email_map),
            "new_emails_count": len(new_emails),
            "leads": leads_list,
            "saved_to_csv": save_to_csv,
            "saved_count": saved_count,
            "csv_path": resolve_csv_path(csv_path),
            "database_total": total_db_count
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/leadgen/platform", methods=["POST", "OPTIONS"])
def platform_leadgen_endpoint():
    """
    Platform Preset Lead Generation Inferencing.
    Builds targeted social dorks automatically and executes lead generation.
    
    Request JSON:
    {
        "platform": "instagram",                                       (required, e.g. 'instagram', 'linkedin', 'twitter')
        "niche": "real estate agent",                                  (required)
        "email_providers": ["@gmail.com", "@yahoo.com"],               (optional, defaults to preset)
        "num_results": 50,                                             (optional, default 50)
        "method": "ddg",                                               (optional, default 'ddg')
        "save_to_csv": true,                                           (optional, default true)
        "csv_path": "emails.csv"                                       (optional)
    }
    """
    if request.method == "OPTIONS":
        return jsonify({"success": True}), 200

    data = request.get_json(silent=True) or {}
    platform = data.get("platform", "").strip()
    niche = data.get("niche", "").strip()

    if not platform:
        return jsonify({"success": False, "error": "Missing required field: 'platform'"}), 400
    if not niche:
        return jsonify({"success": False, "error": "Missing required field: 'niche'"}), 400

    try:
        providers = data.get("email_providers")
        dork_query = build_platform_dork(platform, niche, providers)
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400

    # Delegate to leadgen pipeline
    num_results = min(int(data.get("num_results", 50)), 200)
    method = data.get("method", "ddg").lower()
    key = data.get("key")
    cx = data.get("cx")
    save_to_csv = data.get("save_to_csv", True)
    csv_path = data.get("csv_path")
    deduplicate = data.get("deduplicate", True)

    try:
        results = execute_search(dork_query, method=method, num_results=num_results, key=key, cx=cx)
        email_map = extract_emails.parse_results(results)
        
        seen_emails = load_seen_emails(csv_path) if deduplicate else set()
        new_emails = set(email_map.keys()) - seen_emails if deduplicate else set(email_map.keys())
        
        saved_count = 0
        if save_to_csv and new_emails:
            saved_count = save_new_emails(new_emails, csv_path)

        leads_list = []
        for email, sources in sorted(email_map.items()):
            leads_list.append({
                "email": email,
                "sources": sorted(list(sources)),
                "is_new": email in new_emails
            })

        total_db_count = len(load_seen_emails(csv_path))

        return jsonify({
            "success": True,
            "platform": platform,
            "niche": niche,
            "generated_dork": dork_query,
            "method": method,
            "total_search_results": len(results),
            "total_emails_found": len(email_map),
            "new_emails_count": len(new_emails),
            "leads": leads_list,
            "saved_to_csv": save_to_csv,
            "saved_count": saved_count,
            "csv_path": resolve_csv_path(csv_path),
            "database_total": total_db_count
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/leads", methods=["GET", "POST", "DELETE", "OPTIONS"])
def leads_database_endpoint():
    """
    CRUD Endpoint for Stored Leads Database (emails.csv).
    
    GET:
      Params:
        - q: search filter (optional)
        - page: int (default 1)
        - limit: int (default 100, 0 for all)
        - csv_path: custom csv path (optional)
        
    POST:
      JSON:
        - emails: list of email strings OR email: single string
        - csv_path: custom csv path (optional)
        
    DELETE:
      JSON:
        - emails: list of email strings to remove OR
        - clear_all: true (to wipe database)
        - csv_path: custom csv path (optional)
    """
    if request.method == "OPTIONS":
        return jsonify({"success": True}), 200

    csv_path = request.args.get("csv_path")

    # GET: List leads
    if request.method == "GET":
        q = request.args.get("q", "").strip().lower()
        page = max(int(request.args.get("page", 1)), 1)
        limit = int(request.args.get("limit", 100))

        all_emails = sorted(list(load_seen_emails(csv_path)))
        
        if q:
            all_emails = [e for e in all_emails if q in e]

        total = len(all_emails)
        
        if limit > 0:
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            paged_emails = all_emails[start_idx:end_idx]
        else:
            paged_emails = all_emails

        return jsonify({
            "success": True,
            "total": total,
            "page": page,
            "limit": limit,
            "returned_count": len(paged_emails),
            "leads": paged_emails,
            "csv_path": resolve_csv_path(csv_path)
        })

    # POST: Add leads manually
    elif request.method == "POST":
        data = request.get_json(silent=True) or {}
        custom_csv = data.get("csv_path", csv_path)
        emails = data.get("emails", [])
        single_email = data.get("email")
        
        if single_email and isinstance(single_email, str):
            emails.append(single_email)
            
        if not emails or not isinstance(emails, list):
            return jsonify({"success": False, "error": "Missing or invalid 'emails' list"}), 400

        valid_emails = set()
        for e in emails:
            if isinstance(e, str) and extract_emails.EMAIL_REGEX.match(e.strip()):
                valid_emails.add(e.strip().lower())

        if not valid_emails:
            return jsonify({"success": False, "error": "No valid email addresses found in payload"}), 400

        added_count = save_new_emails(valid_emails, custom_csv)
        total_db_count = len(load_seen_emails(custom_csv))

        return jsonify({
            "success": True,
            "added_count": added_count,
            "database_total": total_db_count,
            "csv_path": resolve_csv_path(custom_csv)
        })

    # DELETE: Remove leads or clear
    elif request.method == "DELETE":
        data = request.get_json(silent=True) or {}
        custom_csv = data.get("csv_path", csv_path)
        clear_all = data.get("clear_all", False)
        
        if clear_all:
            removed = clear_all_emails(custom_csv)
            return jsonify({
                "success": True,
                "action": "cleared_all",
                "removed_count": removed,
                "database_total": 0,
                "csv_path": resolve_csv_path(custom_csv)
            })

        emails = data.get("emails", [])
        single_email = data.get("email")
        if single_email:
            emails.append(single_email)

        if not emails:
            return jsonify({"success": False, "error": "Must provide 'emails' array to delete or 'clear_all': true"}), 400

        removed_count = delete_emails_from_db(set(emails), custom_csv)
        total_db_count = len(load_seen_emails(custom_csv))

        return jsonify({
            "success": True,
            "action": "delete",
            "removed_count": removed_count,
            "database_total": total_db_count,
            "csv_path": resolve_csv_path(custom_csv)
        })


@app.route("/api/leads/export", methods=["GET"])
def export_leads_endpoint():
    """
    Download or stream the stored leads CSV file.
    Optionally specify ?format=json to download as JSON array.
    """
    csv_path = request.args.get("csv_path")
    fmt = request.args.get("format", "csv").lower()
    path = resolve_csv_path(csv_path)

    if not os.path.exists(path):
        return jsonify({"success": False, "error": "No leads database found at path"}), 404

    if fmt == "json":
        emails = sorted(list(load_seen_emails(csv_path)))
        return jsonify({
            "success": True,
            "total": len(emails),
            "leads": emails
        })

    return send_file(
        path,
        mimetype="text/csv",
        as_attachment=True,
        download_name="emails.csv"
    )


@app.route("/api/docs", methods=["GET"])
def api_docs_endpoint():
    """Returns OpenAPI-style JSON documentation describing all available endpoints."""
    return jsonify({
        "title": "Mail Lead Gen Direct Inferencing REST API",
        "version": "1.0.0",
        "description": "High performance API for automated lead generation, web dork inferencing, search extraction, and email parsing.",
        "endpoints": {
            "GET /api/health": {
                "summary": "Check system health and active database stats",
                "response": "{ success, status, version, database: { leads_count, csv_path } }"
            },
            "GET /api/platforms": {
                "summary": "List available target platforms for lead generation dorks",
                "response": "{ success, count, platforms: { [platform]: { id, name, domain, default_providers } } }"
            },
            "POST /api/search": {
                "summary": "Direct search inferencing (DuckDuckGo, Google API, or Scraper)",
                "body": {
                    "query": "string (required)",
                    "method": "'ddg' | 'api' | 'scrape' (default 'ddg')",
                    "num_results": "integer (default 10)",
                    "key": "string (optional for Google API)",
                    "cx": "string (optional for Google API)"
                }
            },
            "POST /api/extract/text": {
                "summary": "Extract unique email addresses from raw text",
                "body": {
                    "text": "string (required)"
                }
            },
            "POST /api/extract/results": {
                "summary": "Extract emails from structured search result objects and map source links",
                "body": {
                    "results": "[{ title, link, snippet }]"
                }
            },
            "POST /api/leadgen": {
                "summary": "One-shot lead gen inferencing: search -> extract -> deduplicate -> save to database",
                "body": {
                    "query": "string (required dork or keyword query)",
                    "num_results": "integer (default 50)",
                    "method": "'ddg' | 'api' | 'scrape' (default 'ddg')",
                    "save_to_csv": "boolean (default true)",
                    "deduplicate": "boolean (default true)"
                }
            },
            "POST /api/leadgen/platform": {
                "summary": "Preset platform lead generation (Instagram, LinkedIn, Twitter/X, TikTok, YouTube, etc.)",
                "body": {
                    "platform": "string (required, e.g. 'instagram', 'linkedin', 'twitter')",
                    "niche": "string (required, e.g. 'software engineer', 'fitness')",
                    "email_providers": "string[] (optional, e.g. ['@gmail.com', '@yahoo.com'])",
                    "num_results": "integer (default 50)",
                    "save_to_csv": "boolean (default true)"
                }
            },
            "GET /api/leads": {
                "summary": "Retrieve saved leads database with search and pagination",
                "params": {
                    "q": "search filter (optional)",
                    "page": "page number (default 1)",
                    "limit": "results per page (default 100, 0 for all)"
                }
            },
            "POST /api/leads": {
                "summary": "Manually append emails to leads database with automatic deduplication",
                "body": {
                    "emails": "string[] or email: string"
                }
            },
            "DELETE /api/leads": {
                "summary": "Delete specific leads or clear entire database",
                "body": {
                    "emails": "string[] (emails to remove) OR clear_all: true"
                }
            },
            "GET /api/leads/export": {
                "summary": "Download emails.csv directly or export as JSON (?format=json)"
            }
        }
    })


# ==========================================
# Interactive Web UI & Dashboard
# ==========================================

INDEX_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Mail Lead Gen — Direct Inferencing Studio</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-base: #0a0d14;
      --bg-surface: #111726;
      --bg-card: rgba(19, 26, 43, 0.75);
      --bg-card-hover: rgba(27, 36, 60, 0.85);
      --border-color: rgba(255, 255, 255, 0.08);
      --border-focus: rgba(99, 102, 241, 0.5);
      --primary: #6366f1;
      --primary-hover: #4f46e5;
      --primary-glow: rgba(99, 102, 241, 0.25);
      --accent-cyan: #06b6d4;
      --accent-emerald: #10b981;
      --accent-amber: #f59e0b;
      --accent-rose: #f43f5e;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --text-dim: #64748b;
      --font-sans: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      background-color: var(--bg-base);
      color: var(--text-main);
      font-family: var(--font-sans);
      min-height: 100vh;
      background-image: 
        radial-gradient(circle at 15% 15%, rgba(99, 102, 241, 0.12) 0%, transparent 40%),
        radial-gradient(circle at 85% 85%, rgba(6, 182, 212, 0.08) 0%, transparent 40%);
      background-attachment: fixed;
      line-height: 1.5;
    }

    /* Top Navigation Bar */
    header {
      background: rgba(10, 13, 20, 0.85);
      backdrop-filter: blur(16px);
      border-bottom: 1px solid var(--border-color);
      position: sticky;
      top: 0;
      z-index: 100;
      padding: 0.85rem 2rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .brand-icon {
      width: 36px;
      height: 36px;
      background: linear-gradient(135deg, var(--primary), var(--accent-cyan));
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.1rem;
      box-shadow: 0 0 15px var(--primary-glow);
    }

    .brand-title {
      font-weight: 800;
      font-size: 1.15rem;
      letter-spacing: -0.02em;
      background: linear-gradient(to right, #ffffff, #cbd5e1);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    .brand-badge {
      font-size: 0.7rem;
      font-weight: 700;
      text-transform: uppercase;
      background: rgba(99, 102, 241, 0.15);
      color: #818cf8;
      border: 1px solid rgba(99, 102, 241, 0.3);
      padding: 0.15rem 0.5rem;
      border-radius: 20px;
      letter-spacing: 0.05em;
    }

    .nav-actions {
      display: flex;
      align-items: center;
      gap: 1rem;
    }

    .db-status-pill {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      padding: 0.4rem 0.85rem;
      border-radius: 8px;
      font-size: 0.85rem;
      color: var(--text-muted);
    }

    .db-count {
      color: var(--accent-emerald);
      font-weight: 700;
      font-family: var(--font-mono);
    }

    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 0.5rem;
      font-family: var(--font-sans);
      font-size: 0.875rem;
      font-weight: 600;
      padding: 0.6rem 1.25rem;
      border-radius: 8px;
      border: none;
      cursor: pointer;
      transition: all 0.2s ease;
      text-decoration: none;
    }

    .btn-primary {
      background: linear-gradient(135deg, var(--primary), var(--primary-hover));
      color: #ffffff;
      box-shadow: 0 4px 14px var(--primary-glow);
    }
    .btn-primary:hover {
      transform: translateY(-1px);
      box-shadow: 0 6px 20px var(--primary-glow);
    }

    .btn-secondary {
      background: var(--bg-surface);
      color: var(--text-main);
      border: 1px solid var(--border-color);
    }
    .btn-secondary:hover {
      background: var(--bg-card-hover);
      border-color: rgba(255, 255, 255, 0.2);
    }

    .btn-sm {
      padding: 0.35rem 0.75rem;
      font-size: 0.8rem;
    }

    /* Container Layout */
    .container {
      max-width: 1380px;
      margin: 2rem auto;
      padding: 0 1.5rem;
    }

    /* Tabs Bar */
    .tabs-bar {
      display: flex;
      gap: 0.5rem;
      border-bottom: 1px solid var(--border-color);
      margin-bottom: 1.75rem;
      overflow-x: auto;
      padding-bottom: 0.5rem;
    }

    .tab-btn {
      background: transparent;
      border: none;
      color: var(--text-muted);
      font-family: var(--font-sans);
      font-weight: 600;
      font-size: 0.925rem;
      padding: 0.65rem 1.25rem;
      border-radius: 8px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      transition: all 0.2s ease;
    }

    .tab-btn:hover {
      color: var(--text-main);
      background: rgba(255, 255, 255, 0.04);
    }

    .tab-btn.active {
      color: #ffffff;
      background: var(--primary);
      box-shadow: 0 2px 10px var(--primary-glow);
    }

    /* Main Grid */
    .view-panel {
      display: none;
    }
    .view-panel.active {
      display: block;
      animation: fadeIn 0.25s ease;
    }

    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(4px); }
      to { opacity: 1; transform: translateY(0); }
    }

    .grid-2col {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1.5rem;
    }

    @media (max-width: 960px) {
      .grid-2col {
        grid-template-columns: 1fr;
      }
    }

    /* Glass Cards */
    .card {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 14px;
      backdrop-filter: blur(12px);
      padding: 1.5rem;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.35);
    }

    .card-header {
      margin-bottom: 1.25rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .card-title {
      font-size: 1.1rem;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .card-desc {
      font-size: 0.85rem;
      color: var(--text-muted);
      margin-top: 0.25rem;
    }

    /* Forms */
    .form-group {
      margin-bottom: 1.25rem;
    }

    label {
      display: block;
      font-size: 0.85rem;
      font-weight: 600;
      color: var(--text-muted);
      margin-bottom: 0.4rem;
    }

    input[type="text"], input[type="number"], select, textarea {
      width: 100%;
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 0.65rem 0.9rem;
      color: var(--text-main);
      font-family: var(--font-sans);
      font-size: 0.9rem;
      transition: all 0.2s ease;
    }

    input:focus, select:focus, textarea:focus {
      outline: none;
      border-color: var(--primary);
      box-shadow: 0 0 0 3px var(--primary-glow);
    }

    textarea {
      resize: vertical;
      font-family: var(--font-mono);
      font-size: 0.85rem;
    }

    .form-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1rem;
    }

    .checkbox-group {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      cursor: pointer;
      font-size: 0.875rem;
      color: var(--text-muted);
    }

    .checkbox-group input {
      accent-color: var(--primary);
      width: 16px;
      height: 16px;
    }

    /* Platform Picker Cards */
    .platform-picker {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
      gap: 0.6rem;
      margin-bottom: 1.25rem;
    }

    .platform-chip {
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 0.6rem 0.75rem;
      text-align: center;
      cursor: pointer;
      transition: all 0.2s ease;
      font-size: 0.85rem;
      font-weight: 600;
      color: var(--text-muted);
    }

    .platform-chip:hover {
      border-color: rgba(255, 255, 255, 0.2);
      color: var(--text-main);
    }

    .platform-chip.selected {
      background: rgba(99, 102, 241, 0.15);
      border-color: var(--primary);
      color: #818cf8;
      box-shadow: 0 0 10px var(--primary-glow);
    }

    /* Output Section */
    .output-box {
      background: #07090e;
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 1rem;
      font-family: var(--font-mono);
      font-size: 0.825rem;
      color: #cbd5e1;
      max-height: 520px;
      overflow-y: auto;
      white-space: pre-wrap;
      word-break: break-all;
    }

    /* Leads Table */
    .table-wrapper {
      overflow-x: auto;
      margin-top: 1rem;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      text-align: left;
      font-size: 0.875rem;
    }

    th {
      background: var(--bg-surface);
      padding: 0.75rem 1rem;
      color: var(--text-muted);
      font-weight: 600;
      border-bottom: 1px solid var(--border-color);
    }

    td {
      padding: 0.75rem 1rem;
      border-bottom: 1px solid rgba(255, 255, 255, 0.04);
      color: var(--text-main);
    }

    tr:hover td {
      background: rgba(255, 255, 255, 0.02);
    }

    .badge {
      display: inline-block;
      padding: 0.2rem 0.5rem;
      border-radius: 4px;
      font-size: 0.75rem;
      font-weight: 600;
    }

    .badge-new {
      background: rgba(16, 185, 129, 0.15);
      color: var(--accent-emerald);
      border: 1px solid rgba(16, 185, 129, 0.3);
    }

    .badge-cached {
      background: rgba(148, 163, 184, 0.1);
      color: var(--text-muted);
      border: 1px solid rgba(148, 163, 184, 0.2);
    }

    /* Loading Spinner */
    .spinner {
      display: inline-block;
      width: 16px;
      height: 16px;
      border: 2px solid rgba(255, 255, 255, 0.3);
      border-radius: 50%;
      border-top-color: #fff;
      animation: spin 0.8s linear infinite;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    .stat-cards {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 1rem;
      margin-bottom: 1.5rem;
    }

    @media (max-width: 768px) {
      .stat-cards { grid-template-columns: repeat(2, 1fr); }
    }

    .stat-card {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 10px;
      padding: 1rem 1.25rem;
    }

    .stat-num {
      font-size: 1.5rem;
      font-weight: 800;
      font-family: var(--font-mono);
      margin-top: 0.25rem;
    }
  </style>
</head>
<body>

  <!-- Top Navigation Header -->
  <header>
    <div class="brand">
      <div class="brand-icon">✉</div>
      <div>
        <div class="brand-title">Mail Lead Gen</div>
      </div>
      <span class="brand-badge">REST API v1.0</span>
    </div>
    <div class="nav-actions">
      <div class="db-status-pill">
        <span>Database Leads:</span>
        <span class="db-count" id="header-db-count">-</span>
      </div>
      <a href="/api/leads/export" class="btn btn-secondary btn-sm" download>⬇ Export CSV</a>
      <a href="/api/docs" target="_blank" class="btn btn-secondary btn-sm">📖 OpenAPI Docs</a>
    </div>
  </header>

  <div class="container">
    <!-- Navigation Tabs -->
    <div class="tabs-bar">
      <button class="tab-btn active" onclick="switchTab('platform-tab', this)">🎯 Platform Lead Gen</button>
      <button class="tab-btn" onclick="switchTab('custom-tab', this)">⚡ Custom Dork Inferencing</button>
      <button class="tab-btn" onclick="switchTab('extract-tab', this)">🔍 Text / Result Extractor</button>
      <button class="tab-btn" onclick="switchTab('search-tab', this)">🌐 Raw Search</button>
      <button class="tab-btn" onclick="switchTab('database-tab', this); loadDatabaseLeads();">🗄 Leads Database</button>
    </div>

    <!-- TAB 1: Platform Preset Lead Gen -->
    <div id="platform-tab" class="view-panel active">
      <div class="grid-2col">
        <div class="card">
          <div class="card-header">
            <div>
              <div class="card-title">Platform Direct Lead Gen</div>
              <div class="card-desc">Select a target social/creator platform, enter your niche, and extract leads automatically.</div>
            </div>
          </div>

          <form id="platform-form" onsubmit="handlePlatformLeadgen(event)">
            <label>Select Target Platform</label>
            <div class="platform-picker" id="platform-chips">
              <!-- Dynamically populated from JS -->
            </div>
            <input type="hidden" id="selected-platform" value="instagram">

            <div class="form-group">
              <label for="platform-niche">Target Niche / Keyword</label>
              <input type="text" id="platform-niche" placeholder="e.g. real estate agent, fitness coach, crypto trader" required value="fitness coach">
            </div>

            <div class="form-row">
              <div class="form-group">
                <label for="platform-num">Results to Fetch</label>
                <input type="number" id="platform-num" value="30" min="5" max="200">
              </div>
              <div class="form-group">
                <label for="platform-method">Search Method</label>
                <select id="platform-method">
                  <option value="ddg" selected>DuckDuckGo (Free & Reliable)</option>
                  <option value="api">Google Custom Search API</option>
                  <option value="scrape">Direct Google Scraper</option>
                </select>
              </div>
            </div>

            <div class="form-group">
              <label class="checkbox-group">
                <input type="checkbox" id="platform-save-csv" checked>
                <span>Automatically save new leads to database (emails.csv)</span>
              </label>
            </div>

            <button type="submit" class="btn btn-primary" id="platform-submit-btn" style="width: 100%;">
              <span>⚡ Execute Platform Inference</span>
            </button>
          </form>
        </div>

        <div class="card">
          <div class="card-header">
            <div>
              <div class="card-title">Inference Results</div>
              <div class="card-desc" id="platform-result-desc">Output will appear here after execution.</div>
            </div>
            <button class="btn btn-secondary btn-sm" onclick="copyOutput('platform-output')">Copy JSON</button>
          </div>
          <div class="output-box" id="platform-output">Ready. Select a platform and click "Execute Platform Inference".</div>
        </div>
      </div>
    </div>

    <!-- TAB 2: Custom Dork Lead Gen -->
    <div id="custom-tab" class="view-panel">
      <div class="grid-2col">
        <div class="card">
          <div class="card-header">
            <div>
              <div class="card-title">Custom Dork Lead Gen</div>
              <div class="card-desc">Execute arbitrary search dorks and extract emails end-to-end.</div>
            </div>
          </div>

          <form id="custom-form" onsubmit="handleCustomLeadgen(event)">
            <div class="form-group">
              <label for="custom-query">Search Query / Dork String</label>
              <textarea id="custom-query" rows="4" placeholder='site:linkedin.com "CTO" "@gmail.com" OR "@yahoo.com"' required>site:twitter.com "founder" "@gmail.com"</textarea>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label for="custom-num">Results to Fetch</label>
                <input type="number" id="custom-num" value="30" min="5" max="200">
              </div>
              <div class="form-group">
                <label for="custom-method">Search Method</label>
                <select id="custom-method">
                  <option value="ddg" selected>DuckDuckGo (Free & Reliable)</option>
                  <option value="api">Google Custom Search API</option>
                  <option value="scrape">Direct Google Scraper</option>
                </select>
              </div>
            </div>

            <div class="form-group">
              <label class="checkbox-group">
                <input type="checkbox" id="custom-save-csv" checked>
                <span>Save newly discovered unique emails to CSV</span>
              </label>
            </div>

            <button type="submit" class="btn btn-primary" id="custom-submit-btn" style="width: 100%;">
              <span>⚡ Run Custom Pipeline</span>
            </button>
          </form>
        </div>

        <div class="card">
          <div class="card-header">
            <div>
              <div class="card-title">Pipeline Output</div>
              <div class="card-desc" id="custom-result-desc">Awaiting custom dork execution...</div>
            </div>
            <button class="btn btn-secondary btn-sm" onclick="copyOutput('custom-output')">Copy JSON</button>
          </div>
          <div class="output-box" id="custom-output">Ready. Enter your query dork and click "Run Custom Pipeline".</div>
        </div>
      </div>
    </div>

    <!-- TAB 3: Text & Results Email Extractor -->
    <div id="extract-tab" class="view-panel">
      <div class="grid-2col">
        <div class="card">
          <div class="card-header">
            <div>
              <div class="card-title">Direct Text Extractor</div>
              <div class="card-desc">Paste raw text, HTML snippets, or bio descriptions to parse emails.</div>
            </div>
          </div>

          <form id="extract-form" onsubmit="handleExtractText(event)">
            <div class="form-group">
              <label for="extract-text">Raw Text Content</label>
              <textarea id="extract-text" rows="8" placeholder="Paste unformatted text containing emails (supports [at], (at) obfuscations)..." required>Hello! For collaborations email support@domain.com or reach me on alex.dev (at) gmail.com. Our sales rep is sales@agency.io.</textarea>
            </div>

            <button type="submit" class="btn btn-primary" id="extract-submit-btn" style="width: 100%;">
              <span>🔍 Extract Emails from Text</span>
            </button>
          </form>
        </div>

        <div class="card">
          <div class="card-header">
            <div>
              <div class="card-title">Extracted Emails</div>
              <div class="card-desc" id="extract-result-desc">Extracted email list will appear here.</div>
            </div>
            <button class="btn btn-secondary btn-sm" onclick="copyOutput('extract-output')">Copy JSON</button>
          </div>
          <div class="output-box" id="extract-output">Awaiting input...</div>
        </div>
      </div>
    </div>

    <!-- TAB 4: Raw Search -->
    <div id="search-tab" class="view-panel">
      <div class="grid-2col">
        <div class="card">
          <div class="card-header">
            <div>
              <div class="card-title">Direct Web Search</div>
              <div class="card-desc">Test search engine queries directly without email parsing.</div>
            </div>
          </div>

          <form id="search-form" onsubmit="handleRawSearch(event)">
            <div class="form-group">
              <label for="search-query">Search Query</label>
              <input type="text" id="search-query" placeholder="e.g. Python web scraping tutorial" required value="Python web development tutorials">
            </div>

            <div class="form-row">
              <div class="form-group">
                <label for="search-num">Results to Retrieve</label>
                <input type="number" id="search-num" value="10" min="1" max="100">
              </div>
              <div class="form-group">
                <label for="search-method">Search Method</label>
                <select id="search-method">
                  <option value="ddg" selected>DuckDuckGo (Free)</option>
                  <option value="api">Google Custom Search API</option>
                  <option value="scrape">Direct Google Scraper</option>
                </select>
              </div>
            </div>

            <button type="submit" class="btn btn-primary" id="search-submit-btn" style="width: 100%;">
              <span>🌐 Query Search Engine</span>
            </button>
          </form>
        </div>

        <div class="card">
          <div class="card-header">
            <div>
              <div class="card-title">Search Results JSON</div>
              <div class="card-desc" id="search-result-desc">Results will render below.</div>
            </div>
            <button class="btn btn-secondary btn-sm" onclick="copyOutput('search-output')">Copy JSON</button>
          </div>
          <div class="output-box" id="search-output">Ready to query...</div>
        </div>
      </div>
    </div>

    <!-- TAB 5: Leads Database Explorer -->
    <div id="database-tab" class="view-panel">
      <div class="stat-cards">
        <div class="stat-card">
          <div style="font-size: 0.8rem; color: var(--text-muted); font-weight: 600;">Total Saved Leads</div>
          <div class="stat-num" id="db-total-stat" style="color: var(--accent-emerald);">-</div>
        </div>
        <div class="stat-card">
          <div style="font-size: 0.8rem; color: var(--text-muted); font-weight: 600;">Storage Format</div>
          <div class="stat-num" style="font-size: 1.15rem; color: #818cf8; margin-top: 0.5rem;">CSV (emails.csv)</div>
        </div>
        <div class="stat-card">
          <div style="font-size: 0.8rem; color: var(--text-muted); font-weight: 600;">Export Options</div>
          <div style="margin-top: 0.5rem; display: flex; gap: 0.5rem;">
            <a href="/api/leads/export" class="btn btn-secondary btn-sm" download>CSV</a>
            <a href="/api/leads/export?format=json" class="btn btn-secondary btn-sm" target="_blank">JSON</a>
          </div>
        </div>
        <div class="stat-card">
          <div style="font-size: 0.8rem; color: var(--text-muted); font-weight: 600;">Database Actions</div>
          <div style="margin-top: 0.5rem;">
            <button class="btn btn-secondary btn-sm" style="color: var(--accent-rose);" onclick="clearDatabase()">Clear DB</button>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <div class="card-title">Stored Leads Browser</div>
          <div style="display: flex; gap: 0.5rem; align-items: center;">
            <input type="text" id="db-search-input" placeholder="Search email..." style="width: 240px; padding: 0.4rem 0.75rem;" oninput="loadDatabaseLeads()">
            <button class="btn btn-secondary btn-sm" onclick="loadDatabaseLeads()">🔄 Refresh</button>
          </div>
        </div>

        <div class="table-wrapper">
          <table>
            <thead>
              <tr>
                <th style="width: 60px;">#</th>
                <th>Email Address</th>
                <th style="width: 140px;">Status</th>
                <th style="width: 100px; text-align: right;">Action</th>
              </tr>
            </thead>
            <tbody id="leads-table-body">
              <tr><td colspan="4" style="text-align: center; color: var(--text-muted);">Loading database leads...</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

  </div>

  <script>
    const PLATFORMS_DATA = {{ platforms_json|safe }};

    function initPlatforms() {
      const container = document.getElementById('platform-chips');
      container.innerHTML = '';
      Object.keys(PLATFORMS_DATA).forEach((key, idx) => {
        const p = PLATFORMS_DATA[key];
        const chip = document.createElement('div');
        chip.className = `platform-chip ${idx === 0 ? 'selected' : ''}`;
        chip.innerText = p.name;
        chip.onclick = () => selectPlatform(key, chip);
        container.appendChild(chip);
      });
    }

    function selectPlatform(key, element) {
      document.querySelectorAll('.platform-chip').forEach(c => c.classList.remove('selected'));
      element.classList.add('selected');
      document.getElementById('selected-platform').value = key;
    }

    function switchTab(tabId, btn) {
      document.querySelectorAll('.view-panel').forEach(p => p.classList.remove('active'));
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.getElementById(tabId).classList.add('active');
      btn.classList.add('active');
    }

    async function fetchHealth() {
      try {
        const res = await fetch('/api/health');
        const data = await res.json();
        if (data.success) {
          const count = data.database.leads_count;
          document.getElementById('header-db-count').innerText = count;
          document.getElementById('db-total-stat').innerText = count;
        }
      } catch (err) {
        console.error('Health fetch error:', err);
      }
    }

    async function handlePlatformLeadgen(e) {
      e.preventDefault();
      const btn = document.getElementById('platform-submit-btn');
      const out = document.getElementById('platform-output');
      const desc = document.getElementById('platform-result-desc');

      const platform = document.getElementById('selected-platform').value;
      const niche = document.getElementById('platform-niche').value;
      const num_results = parseInt(document.getElementById('platform-num').value);
      const method = document.getElementById('platform-method').value;
      const save_to_csv = document.getElementById('platform-save-csv').checked;

      btn.disabled = true;
      btn.innerHTML = '<span class="spinner"></span> <span>Running Inference...</span>';
      desc.innerText = 'Searching & parsing leads...';
      out.innerText = 'Executing query across target platform...';

      try {
        const res = await fetch('/api/leadgen/platform', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ platform, niche, num_results, method, save_to_csv })
        });
        const data = await res.json();
        out.innerText = JSON.stringify(data, null, 2);
        if (data.success) {
          desc.innerText = `Extracted ${data.total_emails_found} emails (${data.new_emails_count} new leads added).`;
          fetchHealth();
        } else {
          desc.innerText = `Error: ${data.error}`;
        }
      } catch (err) {
        out.innerText = `Network/Execution Error: ${err.message}`;
      } finally {
        btn.disabled = false;
        btn.innerHTML = '<span>⚡ Execute Platform Inference</span>';
      }
    }

    async function handleCustomLeadgen(e) {
      e.preventDefault();
      const btn = document.getElementById('custom-submit-btn');
      const out = document.getElementById('custom-output');
      const desc = document.getElementById('custom-result-desc');

      const query = document.getElementById('custom-query').value;
      const num_results = parseInt(document.getElementById('custom-num').value);
      const method = document.getElementById('custom-method').value;
      const save_to_csv = document.getElementById('custom-save-csv').checked;

      btn.disabled = true;
      btn.innerHTML = '<span class="spinner"></span> <span>Executing Pipeline...</span>';
      desc.innerText = 'Searching & parsing dork...';
      out.innerText = 'Running custom search pipeline...';

      try {
        const res = await fetch('/api/leadgen', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query, num_results, method, save_to_csv })
        });
        const data = await res.json();
        out.innerText = JSON.stringify(data, null, 2);
        if (data.success) {
          desc.innerText = `Found ${data.total_emails_found} emails (${data.new_emails_count} new leads).`;
          fetchHealth();
        } else {
          desc.innerText = `Error: ${data.error}`;
        }
      } catch (err) {
        out.innerText = `Network/Execution Error: ${err.message}`;
      } finally {
        btn.disabled = false;
        btn.innerHTML = '<span>⚡ Run Custom Pipeline</span>';
      }
    }

    async function handleExtractText(e) {
      e.preventDefault();
      const btn = document.getElementById('extract-submit-btn');
      const out = document.getElementById('extract-output');
      const desc = document.getElementById('extract-result-desc');
      const text = document.getElementById('extract-text').value;

      btn.disabled = true;
      btn.innerHTML = '<span class="spinner"></span> <span>Extracting...</span>';

      try {
        const res = await fetch('/api/extract/text', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text })
        });
        const data = await res.json();
        out.innerText = JSON.stringify(data, null, 2);
        if (data.success) {
          desc.innerText = `Parsed ${data.count} unique email address(es).`;
        }
      } catch (err) {
        out.innerText = `Error: ${err.message}`;
      } finally {
        btn.disabled = false;
        btn.innerHTML = '<span>🔍 Extract Emails from Text</span>';
      }
    }

    async function handleRawSearch(e) {
      e.preventDefault();
      const btn = document.getElementById('search-submit-btn');
      const out = document.getElementById('search-output');
      const desc = document.getElementById('search-result-desc');

      const query = document.getElementById('search-query').value;
      const num_results = parseInt(document.getElementById('search-num').value);
      const method = document.getElementById('search-method').value;

      btn.disabled = true;
      btn.innerHTML = '<span class="spinner"></span> <span>Searching...</span>';

      try {
        const res = await fetch('/api/search', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query, num_results, method })
        });
        const data = await res.json();
        out.innerText = JSON.stringify(data, null, 2);
        if (data.success) {
          desc.innerText = `Retrieved ${data.count} search results.`;
        }
      } catch (err) {
        out.innerText = `Error: ${err.message}`;
      } finally {
        btn.disabled = false;
        btn.innerHTML = '<span>🌐 Query Search Engine</span>';
      }
    }

    async function loadDatabaseLeads() {
      const q = document.getElementById('db-search-input').value;
      const tbody = document.getElementById('leads-table-body');
      tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: var(--text-muted);">Loading database leads...</td></tr>';

      try {
        const res = await fetch(`/api/leads?limit=500&q=${encodeURIComponent(q)}`);
        const data = await res.json();
        if (data.success && data.leads.length > 0) {
          tbody.innerHTML = '';
          data.leads.forEach((email, idx) => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
              <td style="color: var(--text-dim); font-family: var(--font-mono);">${idx + 1}</td>
              <td style="font-weight: 600; font-family: var(--font-mono);">${email}</td>
              <td><span class="badge badge-new">Verified Lead</span></td>
              <td style="text-align: right;">
                <button class="btn btn-secondary btn-sm" style="color: var(--accent-rose);" onclick="deleteLead('${email}')">Delete</button>
              </td>
            `;
            tbody.appendChild(tr);
          });
        } else {
          tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: var(--text-muted); padding: 2rem;">No leads found in database.</td></tr>';
        }
      } catch (err) {
        tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--accent-rose);">Error loading database: ${err.message}</td></tr>`;
      }
    }

    async function deleteLead(email) {
      if (!confirm(`Delete lead "${email}" from database?`)) return;
      try {
        const res = await fetch('/api/leads', {
          method: 'DELETE',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email })
        });
        const data = await res.json();
        if (data.success) {
          fetchHealth();
          loadDatabaseLeads();
        }
      } catch (err) {
        alert(`Error deleting lead: ${err.message}`);
      }
    }

    async function clearDatabase() {
      if (!confirm('Are you sure you want to permanently clear ALL leads from the database?')) return;
      try {
        const res = await fetch('/api/leads', {
          method: 'DELETE',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ clear_all: true })
        });
        const data = await res.json();
        if (data.success) {
          fetchHealth();
          loadDatabaseLeads();
        }
      } catch (err) {
        alert(`Error clearing database: ${err.message}`);
      }
    }

    function copyOutput(id) {
      const text = document.getElementById(id).innerText;
      navigator.clipboard.writeText(text).then(() => {
        alert('Copied output to clipboard!');
      });
    }

    // Initialize on load
    window.addEventListener('DOMContentLoaded', () => {
      initPlatforms();
      fetchHealth();
    });
  </script>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def dashboard_view():
    """Renders the interactive web application and direct inferencing test dashboard."""
    return render_template_string(
        INDEX_HTML_TEMPLATE,
        platforms_json=json.dumps(PLATFORMS)
    )


# ==========================================
# CLI / Main Entry Point
# ==========================================

def main():
    parser = argparse.ArgumentParser(description="Start the Mail Lead Gen Flask Inferencing API Server")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host address to bind to (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5000, help="Port number to listen on (default: 5000)")
    parser.add_argument("--debug", action="store_true", help="Run server in Flask debug mode")
    args = parser.parse_args()

    print(f"\n========================================================")
    print(f"  ✉ Mail Lead Gen - Flask Direct Inferencing API")
    print(f"========================================================")
    print(f"[*] API Server running on: http://{args.host}:{args.port}/")
    print(f"[*] Interactive Studio:   http://{args.host}:{args.port}/")
    print(f"[*] OpenAPI Documentation: http://{args.host}:{args.port}/api/docs")
    print(f"[*] Stored Database:      {DEFAULT_CSV_PATH}")
    print(f"========================================================\n")

    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
