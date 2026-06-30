#!/usr/bin/env python3
"""
Google and Alternative Search Utility

This script provides multiple ways to perform programmatic web searches:
1. 'api'   : Google Custom Search JSON API (Official and reliable, requires API credentials).
2. 'ddg'   : DuckDuckGo Search (Free, no API key required, reliable alternative using 'duckduckgo-search').
3. 'scrape': Direct Google Scraping (Free, but highly prone to CAPTCHA blocks and JavaScript redirects).

Installation of dependencies:
    pip install requests beautifulsoup4 duckduckgo-search
"""

import sys
import json
import argparse
import time
import urllib.parse
from typing import List, Dict, Any

# Force UTF-8 stdout/stderr on Windows to avoid UnicodeEncodeError (e.g. from emoji content)
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass

# Standard headers to mimic a browser
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.google.com/",
    "Connection": "keep-alive"
}


def search_api(query: str, api_key: str, cx: str, num_results: int = 10) -> List[Dict[str, Any]]:
    """
    Search Google using the official Google Custom Search JSON API.
    This is the recommended, robust, and stable way to fetch Google results.
    """
    try:
        import requests
    except ImportError:
        print("[!] Error: 'requests' library is required for the official API method.", file=sys.stderr)
        print("    Install it using: pip install requests", file=sys.stderr)
        sys.exit(1)

    url = "https://www.googleapis.com/customsearch/v1"
    results = []
    
    # Custom Search API paginates in pages of max 10 results
    pages = (num_results + 9) // 10
    
    for page in range(pages):
        start_index = (page * 10) + 1
        count = min(10, num_results - len(results))
        if count <= 0:
            break
            
        params = {
            "q": query,
            "key": api_key,
            "cx": cx,
            "start": start_index,
            "num": count
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code != 200:
                print(f"[!] Google API Error ({response.status_code}): {response.text}", file=sys.stderr)
                break
                
            data = response.json()
            items = data.get("items", [])
            
            for item in items:
                results.append({
                    "position": len(results) + 1,
                    "title": item.get("title"),
                    "link": item.get("link"),
                    "snippet": item.get("snippet")
                })
        except Exception as e:
            print(f"[!] API request exception: {e}", file=sys.stderr)
            break
            
        # Add a minor delay if paginating multiple requests
        if page < pages - 1:
            time.sleep(0.5)

    return results


def search_ddg(query: str, num_results: int = 10) -> List[Dict[str, Any]]:
    """
    Search using DuckDuckGo via the 'ddgs' package (or 'duckduckgo_search').
    Highly reliable, completely free, and does not require API keys.
    """
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS
    except ImportError:
        print("[!] Error: 'ddgs' or 'duckduckgo-search' library is required for the ddg method.", file=sys.stderr)
        print("    Install it using: pip install ddgs", file=sys.stderr)
        sys.exit(1)

    results = []
    seen_links = set()
    page = 1
    
    try:
        with DDGS() as ddgs:
            while len(results) < num_results:
                # Query page-by-page to collect enough results
                # We request max_results=None to prevent ddgs from enforcing its default 10-result limit
                ddg_results = ddgs.text(query, page=page, max_results=None)
                if not ddg_results:
                    break
                    
                added_in_page = 0
                for r in ddg_results:
                    link = r.get("href")
                    if link and link not in seen_links:
                        seen_links.add(link)
                        results.append({
                            "position": len(results) + 1,
                            "title": r.get("title"),
                            "link": link,
                            "snippet": r.get("body")
                        })
                        added_in_page += 1
                        if len(results) >= num_results:
                            break
                            
                if added_in_page == 0:
                    break
                    
                page += 1
                time.sleep(1.0)  # Rate limiting prevention delay
                
    except Exception as e:
        print(f"[!] Error during DuckDuckGo search: {e}", file=sys.stderr)
        
    return results


def search_scrape(query: str, num_results: int = 10) -> List[Dict[str, Any]]:
    """
    Search Google by scraping search results page directly.
    Warning: Google employs strict bot-detection (CAPTCHAs and Javascript requirements)
    which frequently blocks this method.
    """
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        print("[!] Error: 'requests' and 'beautifulsoup4' libraries are required for scraping.", file=sys.stderr)
        print("    Install them using: pip install requests beautifulsoup4", file=sys.stderr)
        sys.exit(1)

    url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}&num={num_results}&hl=en"
    
    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=10)
        
        if "detected unusual traffic" in response.text or "captcha" in response.url.lower():
            print("[!] Block Warning: Google blocked this request with a CAPTCHA challenge.", file=sys.stderr)
            print("    Recommendation: Use the official API '--method api' or the free '--method ddg' alternative.", file=sys.stderr)
            return []
            
        if "please enable javascript" in response.text.lower() or "/httpservice/retry/enablejs" in response.text:
            print("[!] Redirection Warning: Google requires JavaScript execution to load search results.", file=sys.stderr)
            print("    Recommendation: Use the official API '--method api' or the free '--method ddg' alternative.", file=sys.stderr)
            return []

        if response.status_code != 200:
            print(f"[!] Received HTTP status code {response.status_code}", file=sys.stderr)
            return []
            
        soup = BeautifulSoup(response.text, "html.parser")
        results = []
        h3s = soup.find_all("h3")
        
        for h3 in h3s:
            a_tag = h3.find_parent("a")
            if not a_tag:
                continue
                
            href = a_tag.get("href", "")
            if not href.startswith("http"):
                continue
                
            title = h3.get_text(strip=True)
            snippet = "N/A"
            
            parent = h3.find_parent(class_="g") or h3.find_parent(class_="MjjYud")
            if parent:
                snippet_elem = (
                    parent.find(class_="VwiC3b") or 
                    parent.find(class_="yDqZ7") or 
                    parent.find(class_="KBbdbe")
                )
                if snippet_elem:
                    snippet = snippet_elem.get_text(strip=True)
                    
            results.append({
                "position": len(results) + 1,
                "title": title,
                "link": href,
                "snippet": snippet
            })
            
            if len(results) >= num_results:
                break
                
        return results

    except Exception as e:
        print(f"[!] Error during scrape search: {e}", file=sys.stderr)
        return []


def main():
    parser = argparse.ArgumentParser(
        description="Search Utility supporting Google API, DuckDuckGo (Free), or Google Scraping."
    )
    parser.add_argument("query", type=str, help="Search query string")
    parser.add_argument("-n", "--num", type=int, default=10, help="Number of results to retrieve (default: 10)")
    parser.add_argument("--method", choices=["api", "ddg", "scrape"], default="ddg",
                        help="Search method: 'api' (Official Google API), 'ddg' (DuckDuckGo, default, free), or 'scrape' (Google Scraping)")
    parser.add_argument("--key", type=str, help="Google Custom Search API Key (required for 'api' method)")
    parser.add_argument("--cx", type=str, help="Google Custom Search Engine ID (required for 'api' method)")
    parser.add_argument("--json", action="store_true", help="Output results as raw JSON")

    args = parser.parse_args()

    if args.method == "api":
        if not args.key or not args.cx:
            parser.error("The 'api' method requires both --key and --cx credentials. See documentation.")
        results = search_api(args.query, args.key, args.cx, num_results=args.num)
    elif args.method == "scrape":
        results = search_scrape(args.query, num_results=args.num)
    else:
        results = search_ddg(args.query, num_results=args.num)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        if not results:
            print("[!] No search results retrieved.")
            sys.exit(1)
            
        print(f"\nSearch Results for: \"{args.query}\" using '{args.method}' method")
        print("=" * 60)
        for res in results:
            print(f"[{res['position']}] {res['title']}")
            print(f"    Link: {res['link']}")
            if res.get('snippet') and res['snippet'] != "N/A":
                print(f"    Description: {res['snippet']}")
            print("-" * 60)


if __name__ == "__main__":
    main()
