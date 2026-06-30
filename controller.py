#!/usr/bin/env python3
"""
Mail Lead Gen Controller

An interactive Terminal User Interface (TUI) to run mail dorks on various
social media platforms and extract new emails. It intelligently avoids 
saving duplicates by checking the existing CSV file.
"""

import sys
import os
import csv

# Enable ANSI colors on Windows
if os.name == 'nt':
    os.system('')

class Style:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    MAGENTA = '\033[95m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

# Import our custom modules
import search
import extract_emails

def load_seen_emails(csv_path: str) -> set:
    """Load already discovered emails from the CSV file."""
    seen = set()
    if os.path.exists(csv_path):
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                for row in reader:
                    if row:
                        seen.add(row[0].lower().strip())
        except Exception as e:
            print(f"{Style.RED}[!] Error reading {csv_path}: {e}{Style.RESET}")
    return seen

def save_new_emails(csv_path: str, new_emails: set):
    """Append new emails to the CSV file."""
    try:
        with open(csv_path, "a", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            for email in sorted(new_emails):
                writer.writerow([email])
    except Exception as e:
        print(f"{Style.RED}[!] Error writing to {csv_path}: {e}{Style.RESET}")

def main():
    # Force UTF-8 stdout on Windows
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

    csv_file = "emails.csv"

    platforms = {
        "1": ("Instagram", "instagram.com"),
        "2": ("LinkedIn", "linkedin.com"),
        "3": ("Twitter/X", "twitter.com"),
        "4": ("Facebook", "facebook.com"),
        "5": ("TikTok", "tiktok.com"),
        "6": ("YouTube", "youtube.com"),
        "7": ("OnlyFans (Creator)", "onlyfans.com"),
        "8": ("Patreon (Creator)", "patreon.com"),
        "9": ("Linktree (Creator)", "linktr.ee"),
        "10": ("Custom Query (Enter your own dork)", None)
    }

    while True:
        print(f"\n{Style.MAGENTA}{Style.BOLD}" + "="*50)
        print("    MAIL LEAD GEN CONTROLLER")
        print("="*50 + f"{Style.RESET}")
        
        seen_emails = load_seen_emails(csv_file)
        print(f"{Style.CYAN}[*] Database Status:{Style.RESET} {len(seen_emails)} unique emails in {csv_file}\n")
        
        print(f"{Style.BOLD}Available Platforms:{Style.RESET}")
        for key, (name, _) in platforms.items():
            print(f"  {Style.YELLOW}[{key}]{Style.RESET} {name}")
        print(f"  {Style.YELLOW}[0]{Style.RESET} Exit")
        
        choice = input(f"\n{Style.BOLD}Select a platform (0-10): {Style.RESET}").strip()
        
        if choice == '0':
            print(f"{Style.YELLOW}Exiting...{Style.RESET}")
            break
            
        if choice not in platforms:
            print(f"{Style.RED}[-] Invalid choice. Please try again.{Style.RESET}")
            continue
            
        platform_name, domain = platforms[choice]
        
        if domain:
            niche = input(f"\n{Style.BOLD}Enter your target niche/keyword for {platform_name} (e.g. 'plumber', 'developer'): {Style.RESET}").strip()
            if not niche:
                print(f"{Style.RED}[-] Niche cannot be empty.{Style.RESET}")
                continue
            # Typical email providers for generic search
            email_providers = '"@gmail.com" OR "@yahoo.com" OR "@hotmail.com" OR "@outlook.com"'
            query = f'site:{domain} "{niche}" {email_providers}'
        else:
            query = input(f"\n{Style.BOLD}Enter your full custom search query (dork): {Style.RESET}").strip()
            if not query:
                print(f"{Style.RED}[-] Query cannot be empty.{Style.RESET}")
                continue
                
        num_str = input(f"{Style.BOLD}How many search results to fetch? (default: 50): {Style.RESET}").strip()
        num_results = int(num_str) if num_str.isdigit() else 50
        
        print(f"\n{Style.CYAN}[*] Running search: {query}{Style.RESET}")
        print(f"{Style.CYAN}[*] Fetching up to {num_results} results via DuckDuckGo...{Style.RESET}")
        
        # Run the search via DuckDuckGo by default as it's the free/stable method
        results = search.search_ddg(query, num_results=num_results)
        
        if not results:
            print(f"{Style.YELLOW}[-] No results found.{Style.RESET}")
            input(f"\n{Style.BOLD}Press Enter to continue...{Style.RESET}")
            continue
            
        print(f"{Style.GREEN}[+] Found {len(results)} search results. Extracting emails...{Style.RESET}")
        
        # Process with extract_emails parser
        email_map = extract_emails.parse_results(results)
        
        if not email_map:
            print(f"{Style.YELLOW}[-] No emails found in the search results.{Style.RESET}")
            input(f"\n{Style.BOLD}Press Enter to continue...{Style.RESET}")
            continue
            
        extracted_count = len(email_map)
        print(f"{Style.GREEN}[+] Extracted {extracted_count} total email(s) from this run.{Style.RESET}")
        
        # Deduplication intelligence
        new_emails = set(email_map.keys()) - seen_emails
        
        if not new_emails:
            print(f"{Style.YELLOW}[-] All extracted emails are duplicates. No new leads added.{Style.RESET}")
        else:
            print(f"{Style.GREEN}{Style.BOLD}[+] Found {len(new_emails)} NEW unique email(s)!{Style.RESET}")
            save_new_emails(csv_file, new_emails)
            for email in sorted(new_emails):
                print(f"  {Style.CYAN}-{Style.RESET} {email}")
            print(f"{Style.GREEN}[+] Saved to {csv_file}{Style.RESET}")
            
        input(f"\n{Style.BOLD}Press Enter to continue...{Style.RESET}")

if __name__ == "__main__":
    main()
