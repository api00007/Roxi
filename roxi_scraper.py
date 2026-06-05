import cloudscraper
import re
import json
import random
import time
import os
from datetime import datetime
import pytz
from collections import OrderedDict

# --- সেটিংস ---
BASE_URL = "https://roxiestreams.info"
OUTPUT_FILE = "Roxi.json"

CATEGORIES = {
    "Soccer": "/soccer", "NBA": "/nba", "MLB": "/mlb",
    "NHL": "/nhl", "NFL": "/nfl", "Fighting": "/fighting"
}

def get_ist_time():
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist).strftime('%d/%m/%y %H:%M:%S IST')

def push_to_github():
    print(f"[-] GitHub এ {OUTPUT_FILE} আপডেট করা হচ্ছে...")
    # আপনার ALL-ROUNDER রিপোজিটরির ডিটেইলস
    GITHUB_TOKEN = "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"
    GITHUB_USER = "sptvhelpdesk-ship-it"
    GITHUB_REPO = "ALL-ROUNDER"
    GITHUB_EMAIL = "sptvhelpdesk@gmail.com"
    
    remote_url = f"https://{GITHUB_TOKEN}@github.com/{GITHUB_USER}/{GITHUB_REPO}.git"

    try:
        os.system(f'git config --global user.email "{GITHUB_EMAIL}"')
        os.system(f'git config --global user.name "{GITHUB_USER}"')
        os.system(f"git remote set-url origin {remote_url}")
        
        os.system("git fetch origin main")
        os.system(f"git add {OUTPUT_FILE}")
        os.system(f'git commit -m "Roxi Auto Update: {get_ist_time()}" || echo "No changes"')
        os.system("git pull origin main --rebase -X ours")
        os.system("git push origin main")
        print(f"[SUCCESS] {OUTPUT_FILE} সফলভাবে আপডেট হয়েছে।")
    except Exception as e:
        print(f"[ERROR] পুশ ফেইল: {e}")

def run_scraper():
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'android', 'desktop': False})
    all_live_matches = []
    
    try:
        dom_res = scraper.get(f"{BASE_URL}/domainsz29.txt", timeout=15)
        domains_list = [d.strip() for d in dom_res.text.split('\n') if d.strip()]
    except:
        domains_list = ["formaturamaxi.com.br", "shadow-ran.online"]

    for cat_name, cat_path in CATEGORIES.items():
        print(f"[*] স্ক্র্যানিং ক্যাটাগরি: {cat_name}")
        try:
            res = scraper.get(BASE_URL + cat_path, timeout=20)
            # সব টেবিল রো রিড করা যাতে কোনো ম্যাচ বাদ না পড়ে
            rows = re.findall(r'<tr.*?>(.*?)</tr>', res.text, re.S | re.I)
            
            for row in rows:
                if "ENDED" in row.upper() or "EVENT" in row.upper(): continue
                
                match_info = re.search(r'href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', row, re.S | re.I)
                if match_info:
                    m_url = match_info.group(1).strip()
                    clean_rivals = re.sub('<[^<]+?>', '', match_info.group(2)).strip()
                    full_m_url = m_url if m_url.startswith("http") else f"{BASE_URL}/{m_url.lstrip('/')}"
                    
                    try:
                        # ব্যান এড়াতে মানুষের মতো ছোট বিরতি
                        time.sleep(random.uniform(0.5, 1.0))
                        m_res = scraper.get(full_m_url, timeout=15)
                        m_html = m_res.text
                        
                        # ১. সব getRandomStream সার্ভার খুঁজে বের করা
                        streams = re.findall(r"getRandomStream\s*\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]", m_html)
                        
                        if streams:
                            for idx, (path, sub) in enumerate(streams, 1):
                                # Double URL Fix: যদি পাথে অলরেডি http থাকে
                                if path.startswith("http"):
                                    final_link = path
                                else:
                                    r_dom = random.choice(domains_list)
                                    final_link = f"https://{sub}.{r_dom}/{path.lstrip('/')}"
                                
                                # রিফারার থাকলে ক্লিন করা
                                final_link = final_link.split('|')[0]
                                
                                all_live_matches.append(OrderedDict([
                                    ("Id", str(len(all_live_matches) + 1)),
                                    ("Rivels", clean_rivals),
                                    ("Title", f"{cat_name} (S-{idx})"),
                                    ("Link", final_link)
                                ]))
                        else:
                            # ২. যদি বাটন না থাকে তবে ডাইরেক্ট m3u8 চেক
                            path_match = re.search(r"['\"]([^'\"]+\.m3u8[^'\"]*)['\"]", m_html)
                            sub_match = re.search(r"subdomain\s*=\s*['\"]([^'\"]+)['\"]", m_html)
                            if path_match:
                                p = path_match.group(1).split('|')[0]
                                if p.startswith("http"):
                                    final_link = p
                                else:
                                    sub = sub_match.group(1) if sub_match else "601"
                                    r_dom = random.choice(domains_list)
                                    final_link = f"https://{sub}.{r_dom}/{p.lstrip('/')}"
                                
                                all_live_matches.append(OrderedDict([
                                    ("Id", str(len(all_live_matches) + 1)),
                                    ("Rivels", clean_rivals),
                                    ("Title", f"{cat_name} (S-1)"),
                                    ("Link", final_link)
                                ]))
                    except: continue
        except: continue

    # আপনার দেওয়া ফরম্যাটে ডাটা সাজানো
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
        print(f"[OK] মোট {len(all_live_matches)}টি ম্যাচ সংগ্রহ করা হয়েছে।")
        push_to_github()
    else:
        print("[!] কোনো ডাটা পাওয়া যায়নি। সাইট ব্লক বা ম্যাচ নেই।")

if __name__ == "__main__":
    run_scraper()
