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

# --- সেটিংস ---
BASE_URL = os.getenv("BASE_URL")
OUTPUT_FILE = "Roxi.json"

CATEGORIES = {
    "Soccer": "/soccer", "NBA": "/nba", "MLB": "/mlb",
    "NHL": "/nhl", "NFL": "/nfl", "Fighting": "/fighting"
}

def get_ist_time():
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist).strftime('%d/%m/%y %H:%M:%S IST')

def push_to_github():
    print(f"[-] অন্য GitHub রিপোজিটরিতে {OUTPUT_FILE} আপডেট করা হচ্ছে...")
    GITHUB_TOKEN = os.getenv("GH_TOKEN")
    GITHUB_USER = os.getenv("TGITHUB_USER")
    GITHUB_REPO = os.getenv("TGITHUB_REPO")
    GITHUB_EMAIL = os.getenv("TGITHUB_EMAIL")
    
    # একটি আলাদা অস্থায়ী ডিরেক্টরি নাম
    temp_dir = "temp_external_repo"
    remote_url = f"https://{GITHUB_TOKEN}@github.com/{GITHUB_USER}/{GITHUB_REPO}.git"

    try:
        # ১. আগের কোনো টেম্পোরারি ফোল্ডার থাকলে তা মুছে ফেলা
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            
        # ২. অন্য রিপোজিটরিটি একদম নতুনভাবে ক্লোন করা
        clone_status = os.system(f"git clone {remote_url} {temp_dir}")
        if clone_status != 0:
            raise Exception("Git Clone ব্যর্থ হয়েছে। দয়া করে টোকেন ও রিপোজিটরি নাম চেক করুন।")
        
        # ৩. সদ্য স্ক্র্যাপ করা Roxi.json ফাইলটি ক্লোন করা ফোল্ডারে কপি করা
        shutil.copy(OUTPUT_FILE, os.path.join(temp_dir, OUTPUT_FILE))
        
        # ৪. ক্লোন ফোল্ডারের ভেতর প্রবেশ করে কনফিগার, কমিট ও পুশ করা
        current_dir = os.getcwd()
        os.chdir(temp_dir)
        
        os.system(f'git config user.email "{GITHUB_EMAIL}"')
        os.system(f'git config user.name "{GITHUB_USER}"')
        os.system(f"git add {OUTPUT_FILE}")
        os.system(f'git commit -m "Auto Update: {get_ist_time()}" || echo "No changes"')
        push_status = os.system("git push origin main")
        
        # ৫. কাজ শেষে আবার আগের প্রধান ডিরেক্টরিতে ফিরে আসা
        os.chdir(current_dir)
        
        # অস্থায়ী ফোল্ডারটি মুছে ফেলা
        shutil.rmtree(temp_dir)
        
        if push_status == 0:
            print(f"[SUCCESS] অন্য রিপোজিটরিতে {OUTPUT_FILE} সফলভাবে আপডেট সম্পন্ন।")
        else:
            print("[ERROR] পুশ কমান্ড সফল হয়নি।")
            
    except Exception as e:
        print(f"[ERROR] পুশ ফেইল: {e}")

def run_scraper():
    if not BASE_URL:
        print("[ERROR] BASE_URL পাওয়া যায়নি! দয়া করে গিটহাব সিক্রেট চেক করুন।")
        return

    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'android', 'desktop': False})
    all_live_matches = []
    
    try:
        dom_res = scraper.get(f"{BASE_URL}/domainsz35.txt", timeout=15)
        domains_list = [d.strip() for d in dom_res.text.split('\n') if d.strip()]
    except:
        domains_list = ["formaturamaxi.com.br", "sman1asjap.my.id"]

    for cat_name, cat_path in CATEGORIES.items():
        print(f"[*] স্ক্র্যানিং ক্যাটাগরি: {cat_name}")
        try:
            res = scraper.get(BASE_URL + cat_path, timeout=20)
            matches = re.findall(r'href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', res.text, re.S | re.I)
            
            for m_url, m_text in matches:
                if len(m_url) < 10 or any(x in m_url for x in ['multiview', 'discord', 'contact']): continue
                clean_rivals = re.sub('<[^<]+?>', '', m_text).strip()
                full_m_url = m_url if m_url.startswith("http") else f"{BASE_URL}/{m_url.lstrip('/')}"
                
                try:
                    time.sleep(random.uniform(0.5, 1.0))
                    m_res = scraper.get(full_m_url, timeout=15)
                    m_html = m_res.text
                    
                    # সব সার্ভার লিঙ্ক বের করা
                    streams = re.findall(r"getRandomStream\s*\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]", m_html)
                    
                    if streams:
                        for idx, (path, sub) in enumerate(streams, 1):
                            if path.startswith("http"):
                                final_link = path
                            else:
                                r_dom = random.choice(domains_list)
                                final_link = f"https://{sub}.{r_dom}/{path.lstrip('/')}"
                            
                            all_live_matches.append(OrderedDict([
                                ("Id", str(len(all_live_matches) + 1)),
                                ("Rivels", clean_rivals),
                                ("Title", f"{cat_name} (S-{idx})"),
                                ("Link", final_link)
                            ]))
                    else:
                        path_match = re.search(r"['\"]([^'\"]+\.m3u8[^'\"]*)['\"]", m_html)
                        sub_match = re.search(r"subdomain\s*=\s*['\"]([^'\"]+)['\"]", m_html)
                        if path_match:
                            p = path_match.group(1)
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

if __name__ == "__main__":
    run_scraper()
