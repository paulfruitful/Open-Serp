#!/usr/bin/env python3
"""
Email Extractor Parser

This script parses search results (either from a JSON file or directly by executing search.py)
and extracts email addresses using regular expressions.
"""

import sys
import os
import json
import re
import argparse
from typing import List, Dict, Any, Set

# Force UTF-8 stdout/stderr on Windows to avoid UnicodeEncodeError (e.g. from emoji content)
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass

# Ensure the script's directory is in the import search path to resolve search.py from any CWD
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

# Standard regular expression for email validation/extraction
EMAIL_REGEX = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')

def extract_emails_from_text(text: str) -> Set[str]:
    """
    Extract all unique email addresses from a string.
    Also handles simple obfuscations like ' [at] ' or ' (at) '.
    """
    if not text:
        return set()
    # Normalize common obfuscations
    text = re.sub(r'\s*[\[\(]at[\]\)]\s*', '@', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*@\s*', '@', text)  # remove spaces around @ if any
    
    return {email.lower() for email in EMAIL_REGEX.findall(text)}

def parse_results(results: List[Dict[str, Any]]) -> Dict[str, Set[str]]:
    """
    Parse a list of search results and map email addresses to the URLs/sources where they were found.
    """
    email_to_sources = {}
    
    for item in results:
        link = item.get("link", "")
        title = item.get("title", "")
        snippet = item.get("snippet", "")
        
        # Combine fields to search for emails
        combined_text = f"{title} {snippet} {link}"
        emails = extract_emails_from_text(combined_text)
        
        for email in emails:
            if email not in email_to_sources:
                email_to_sources[email] = set()
            if link:
                email_to_sources[email].add(link)
            else:
                email_to_sources[email].add("Unknown Source")
                
    return email_to_sources

def main():
    parser = argparse.ArgumentParser(
        description="Extract and parse email addresses from search results."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", type=str, help="Path to a JSON file containing search results")
    group.add_argument("--query", type=str, help="Search query to run directly and extract emails from")
    
    parser.add_argument("-n", "--num", type=int, default=50, help="Number of search results to fetch (default: 50, only with --query)")
    parser.add_argument("--method", choices=["api", "ddg", "scrape"], default="ddg",
                        help="Search method: 'api', 'ddg' (default), or 'scrape' (only with --query)")
    parser.add_argument("--key", type=str, help="Google API Key (only with --query and --method api)")
    parser.add_argument("--cx", type=str, help="Google Search Engine ID (only with --query and --method api)")
    parser.add_argument("--output", type=str, default="emails.csv", help="Path to output CSV file (default: emails.csv)")

    args = parser.parse_args()

    results = []
    
    if args.file:
        if not os.path.exists(args.file):
            print(f"[!] Error: File '{args.file}' not found.", file=sys.stderr)
            sys.exit(1)
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                results = json.load(f)
        except Exception as e:
            print(f"[!] Error reading or parsing JSON file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Import search functions from search.py
        try:
            import search
        except ImportError:
            print("[!] Error: Could not find search.py in the current directory.", file=sys.stderr)
            sys.exit(1)
            
        print(f"[*] Running search query: '{args.query}'...", file=sys.stderr)
        if args.method == "api":
            if not args.key or not args.cx:
                parser.error("The 'api' method requires both --key and --cx credentials.")
            results = search.search_api(args.query, args.key, args.cx, num_results=args.num)
        elif args.method == "scrape":
            results = search.search_scrape(args.query, num_results=args.num)
        else:
            results = search.search_ddg(args.query, num_results=args.num)

    if not results:
        print("[!] No search results found or processed.", file=sys.stderr)
        sys.exit(1)

    # Parse and extract
    email_map = parse_results(results)
    
    if not email_map:
        print("\n[-] No email addresses found in the search results.")
        return

    print(f"\n[+] Extracted {len(email_map)} unique email address(es):")
    for email in sorted(email_map.keys()):
        print(f"  - {email}")

    # Deduplicate against existing CSV and append new emails
    import csv
    existing_emails = set()
    if os.path.exists(args.output):
        try:
            with open(args.output, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                for row in reader:
                    if row:
                        existing_emails.add(row[0].strip().lower())
        except Exception as e:
            print(f"[!] Error reading existing CSV: {e}", file=sys.stderr)
            
    new_emails = [e for e in email_map.keys() if e not in existing_emails]
    
    if not new_emails:
        print(f"\n[-] All {len(email_map)} extracted emails are already in '{args.output}'. No new emails added.")
        return

    try:
        with open(args.output, "a", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            for email in sorted(new_emails):
                writer.writerow([email])
        print(f"\n[+] Successfully appended {len(new_emails)} new unique email(s) to '{args.output}'")
    except Exception as e:
        print(f"[!] Error saving CSV file: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
