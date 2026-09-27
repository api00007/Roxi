import cloudscraper
import re
import json
import random
import time
import os
import shutil
from datetime import datetime
import pytz
from collections import OrderedDict
from urllib.parse import urljoin

BASE_URL = os.getenv("BASE_URL")
OUTPUT_FILE = "Roxi.json"

CATEGORIES = {
    "Soccer": "/soccer",
    "NBA": "/nba",
    "MLB": "/mlb",
    "NHL": "/nhl",
    "NFL": "/nfl",
    "Fighting": "/fighting",
    "Motorsports": "/motorsports",
    "F1": "/f1",
    "UFC": "/ufc",
    "AEW": "/aew"
}

def get_ist_time():
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist).strftime('%d/%m/%y %H:%M:%S IST')

def push_to_github():
    GITHUB_TOKEN = os.getenv("GH_TOKEN")
    GITHUB_USER = os.getenv("TGITHUB_USER")
    GITHUB_REPO = os.getenv("TGITHUB_REPO")
    GITHUB_EMAIL = os.getenv("TGITHUB_EMAIL")
    
    if not GITHUB_TOKEN or not GITHUB_USER or not GITHUB_REPO:
        print("[ERROR] GitHub secrets are missing. Skipping push.")
        return

    temp_dir = "temp_external_repo"
    remote_url = f"https://{GITHUB_TOKEN}@github.com/{GITHUB_USER}/{GITHUB_REPO}.git"

    try:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            
        clone_status = os.system(f"git clone {remote_url} {temp_dir}")
        if clone_status != 0:
            raise Exception("Git Clone failed. Please check credentials.")
        
        shutil.copy(OUTPUT_FILE, os.path.join(temp_dir, OUTPUT_FILE))
        
        current_dir = os.getcwd()
        os.chdir(temp_dir)
        
        os.system(f'git config user.email "{GITHUB_EMAIL if GITHUB_EMAIL else "action@github.com"}"')
        os.system(f'git config user.name "{GITHUB_USER}"')
        os.system(f"git add {OUTPUT_FILE}")
        os.system(f'git commit -m "Auto Update: {get_ist_time()}" || echo "No changes"')
        push_status = os.system("git push origin main")
        
        os.chdir(current_dir)
        shutil.rmtree(temp_dir)
        
        if push_status == 0:
            print(f"[SUCCESS] {OUTPUT_FILE} successfully updated in {GITHUB_USER}/{GITHUB_REPO}.")
        else:
            print("[ERROR] Git push command failed.")
            
    except Exception as e:
        print(f"[ERROR] Push failed: {e}")

def run_scraper():
    if not BASE_URL:
        print("[ERROR] BASE_URL environment variable is missing.")
        return

    clean_base = BASE_URL.rstrip('/')
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'android', 'desktop': False})
    all_live_matches = []
    domains_list = []

    domain_file_candidates = ["domainsz77.txt", "domainsz65.txt"]
    for d_file in domain_file_candidates:
        try:
            dom_res = scraper.get(f"{clean_base}/{d_file}", timeout=10)
            if dom_res.status_code == 200 and dom_res.text.strip():
                domains_list = [d.strip() for d in dom_res.text.split('\n') if d.strip()]
                if domains_list:
                    break
        except Exception:
            continue

    if not domains_list:
        domains_list = ["shadow-ran.online", "formaturamaxi.com.br", "sman1asjap.my.id"]

    collected_events = []
    seen_urls = set()

    try:
        home_res = scraper.get(clean_base, timeout=15)
        table_matches = re.findall(r'<tr>\s*<td><a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a></td>', home_res.text, re.S | re.I)
        for m_url, m_text in table_matches:
            full_url = m_url if m_url.startswith("http") else urljoin(clean_base, m_url)
            if full_url not in seen_urls:
                seen_urls.add(full_url)
                clean_rivals = re.sub('<[^<]+?>', '', m_text).strip()
                collected_events.append(("Event", clean_rivals, full_url))
    except Exception:
        pass

    for cat_name, cat_path in CATEGORIES.items():
        try:
            target_url = urljoin(clean_base, cat_path)
            res = scraper.get(target_url, timeout=15)
            matches = re.findall(r'href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', res.text, re.S | re.I)
            
            for m_url, m_text in matches:
                if len(m_url) < 3 or any(x in m_url.lower() for x in ['multiview', 'discord', 'contact', 'instagram']):
                    continue
                full_url = m_url if m_url.startswith("http") else urljoin(clean_base, m_url)
                if full_url not in seen_urls and full_url != clean_base and full_url != target_url:
                    seen_urls.add(full_url)
                    clean_rivals = re.sub('<[^<]+?>', '', m_text).strip()
                    if clean_rivals:
                        collected_events.append((cat_name, clean_rivals, full_url))
        except Exception:
            continue

    for cat_name, rivals, m_url in collected_events:
        try:
            time.sleep(random.uniform(0.4, 0.8))
            m_res = scraper.get(m_url, timeout=12)
            m_html = m_res.text

            subdomain_search = re.search(r"var\s+subdomain\s*=\s*['\"]([^'\"]+)['\"]", m_html, re.I)
            page_subdomain = subdomain_search.group(1) if subdomain_search else "tedesco"

            streams = re.findall(r"getRandomStream\s*\(\s*['\"]([^'\"]+)['\"](?:\s*,\s*['\"]([^'\"]+)['\"])?\s*\)", m_html)
            
            if streams:
                for idx, (path, custom_sub) in enumerate(streams, 1):
                    sub = custom_sub if custom_sub else page_subdomain
                    if path.startswith("http"):
                        final_link = path
                    else:
                        r_dom = random.choice(domains_list)
                        final_link = f"https://{sub}.{r_dom}/{path.lstrip('/')}"
                    
                    all_live_matches.append(OrderedDict([
                        ("Id", str(len(all_live_matches) + 1)),
                        ("Rivels", rivals),
                        ("Title", f"{cat_name} (S-{idx})"),
                        ("Link", final_link)
                    ]))
            else:
                path_match = re.search(r"['\"]([^'\"]+\.m3u8[^'\"]*)['\"]", m_html)
                if path_match:
                    p = path_match.group(1)
                    if p.startswith("http"):
                        final_link = p
                    else:
                        r_dom = random.choice(domains_list)
                        final_link = f"https://{page_subdomain}.{r_dom}/{p.lstrip('/')}"
                    
                    all_live_matches.append(OrderedDict([
                        ("Id", str(len(all_live_matches) + 1)),
                        ("Rivels", rivals),
                        ("Title", f"{cat_name} (S-1)"),
                        ("Link", final_link)
                    ]))
        except Exception:
            continue

    if all_live_matches:
        final_package = OrderedDict([
            ("Owner", "Ivan-FluX"),
            ("Telegram", "https://t.me/iVan_flux"),
            ("App name", "fawna-auto-scrape-api"),
            ("Last update", get_ist_time()),
            ("Total_Matches", len(all_live_matches)),
            ("Live_Data", all_live_matches)
        ])
        
        with open(OUTPUT_FILE, "w") as f:
            json.dump(final_package, f, indent=4)
            
        push_to_github()
        print(json.dumps(final_package, indent=4))

if __name__ == "__main__":
    run_scraper()
