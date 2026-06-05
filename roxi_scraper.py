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
OUTPUT_FILE = "data.json"

CATEGORIES = {
    "Soccer": "/soccer", "NBA": "/nba", "MLB": "/mlb",
    "NHL": "/nhl", "NFL": "/nfl", "Fighting": "/fighting"
}

def get_ist_time():
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist).strftime('%d/%m/%y %H:%M:%S IST')

def push_to_github():
    print(f"[-] GitHub এ {OUTPUT_FILE} আপডেট করা হচ্ছে...")
    # আপনার দেওয়া নতুন টোকেন এবং রিপোজিটরি ডিটেইলস
    GITHUB_TOKEN = "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"
    GITHUB_USER = "api00007"
    GITHUB_REPO = "Roxi"
    GITHUB_EMAIL = "api00007@gmail.com"
    
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
        print(f"[SUCCESS] {OUTPUT_FILE} আপডেট সম্পন্ন।")
    except Exception as e:
        print(f"[ERROR] পুশ ফেইল: {e}")

def run_scraper():
    # Cloudscraper তৈরি করা যা বট প্রোটেকশন কাটবে
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'android', 'desktop': False})
    all_live_matches = []
    
    # ডোমেইন লিস্ট সংগ্রহ
    try:
        dom_res = scraper.get(f"{BASE_URL}/domainsz29.txt", timeout=15)
        domains_list = [d.strip() for d in dom_res.text.split('\n') if d.strip()]
    except:
        domains_list = ["formaturamaxi.com.br", "shadow-ran.online"]

    # সব ক্যাটাগরি স্ক্র্যাপ করা
    for cat_name, cat_path in CATEGORIES.items():
        print(f"[*] স্ক্র্যানিং ক্যাটাগরি: {cat_name}")
        try:
            res = scraper.get(BASE_URL + cat_path, timeout=20)
            matches = re.findall(r'href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', res.text, re.S | re.I)
            
            for m_url, m_text in matches:
                # অপ্রয়োজনীয় লিঙ্ক ফিল্টার করা
                if len(m_url) < 10 or any(x in m_url for x in ['multiview', 'discord', 'contact']): continue
                clean_name = re.sub('<[^<]+?>', '', m_text).strip()
                full_m_url = m_url if m_url.startswith("http") else f"{BASE_URL}/{m_url.lstrip('/')}"
                
                try:
                    m_res = scraper.get(full_m_url, timeout=15)
                    # সব সার্ভার লিঙ্ক বের করা
                    streams = re.findall(r"getRandomStream\s*\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]", m_res.text)
                    
                    if streams:
                        for idx, (path, sub) in enumerate(streams, 1):
                            r_dom = random.choice(domains_list)
                            final_link = f"https://{sub}.{r_dom}/{path.lstrip('/')}"
                            all_live_matches.append({
                                "Id": str(len(all_live_matches) + 1),
                                "Category": cat_name,
                                "Match": f"{clean_name} (S-{idx})",
                                "Link": f"{final_link}|referer={BASE_URL}/"
                            })
                    else:
                        # যদি বাটন না থাকে তবে ডাইরেক্ট m3u8 খোঁজা
                        path_match = re.search(r"['\"]([^'\"]+\.m3u8[^'\"]*)['\"]", m_res.text)
                        sub_match = re.search(r"subdomain\s*=\s*['\"]([^'\"]+)['\"]", m_res.text)
                        if path_match:
                            sub = sub_match.group(1) if sub_match else "601"
                            r_dom = random.choice(domains_list)
                            final_link = f"https://{sub}.{r_dom}/{path_match.group(1).lstrip('/')}"
                            all_live_matches.append({
                                "Id": str(len(all_live_matches) + 1),
                                "Category": cat_name,
                                "Match": clean_name,
                                "Link": f"{final_link}|referer={BASE_URL}/"
                            })
                except: continue
        except: continue

    # ডাটা সেভ এবং পুশ করা
    if all_live_matches:
        final_package = OrderedDict([
            ("Status", "Success"),
            ("Owner", "api00007"),
            ("Total", len(all_live_matches)),
            ("Last_Update", get_ist_time()),
            ("Live_Data", all_live_matches)
        ])
        with open(OUTPUT_FILE, "w") as f:
            json.dump(final_package, f, indent=4)
        push_to_github()

if __name__ == "__main__":
    run_scraper()
