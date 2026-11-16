import os
import sys
import json
import urllib.request
import urllib.parse
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
OUTPUT_FILE = DATA_DIR / "database_expanded.json"

def fetch_json(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))

def update_database():
    print("=" * 60)
    print("[*] Sherlock OSINT - GitHub Multi-Source Database Updater")
    print("=" * 60)

    # 1. Base Sherlock official
    print("[+] Fetching official Sherlock repository data.json...")
    sherlock_url = "https://raw.githubusercontent.com/sherlock-project/sherlock/master/sherlock_project/resources/data.json"
    try:
        combined = fetch_json(sherlock_url)
        print(f"    -> Official Sherlock sites: {len(combined) - 1}")
    except Exception as e:
        print(f"    [-] Failed to fetch official Sherlock: {e}. Using local fallback.")
        import sherlock_project.resources
        local_p = Path(sherlock_project.__file__).parent / "resources" / "data.json"
        with open(local_p, "r", encoding="utf-8") as f:
            combined = json.load(f)

    existing_keys = {k.lower() for k in combined.keys()}

    # 2. WhatsMyName OSINT project
    print("[+] Fetching WhatsMyName project database (WebBreacher/WhatsMyName)...")
    wmn_url = "https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json"
    wmn_added = 0
    try:
        wmn = fetch_json(wmn_url)
        for s in wmn.get("sites", []):
            name = s.get("name", "").strip()
            if not name or name.lower() in existing_keys:
                continue

            uri_check = s.get("uri_check", "")
            if not uri_check or "{account}" not in uri_check:
                continue

            url = uri_check.replace("{account}", "{}")
            parsed = urllib.parse.urlparse(url)
            url_main = f"{parsed.scheme}://{parsed.netloc}/"

            known = s.get("known", [])
            claimed = known[0] if known else "admin"

            entry = {
                "url": url,
                "urlMain": url_main,
                "username_claimed": claimed
            }

            if s.get("cat") == "nsfw":
                entry["isNSFW"] = True

            m_string = s.get("m_string", "").strip()
            m_code = s.get("m_code")

            if m_string:
                entry["errorType"] = "message"
                entry["errorMsg"] = [m_string]
            elif m_code and m_code != 200:
                entry["errorType"] = "status_code"
                entry["errorCode"] = m_code
            else:
                entry["errorType"] = "status_code"

            combined[name] = entry
            existing_keys.add(name.lower())
            wmn_added += 1
        print(f"    -> Added {wmn_added} new verified sites from WhatsMyName!")
    except Exception as e:
        print(f"    [-] Error fetching WhatsMyName: {e}")

    # 3. Maigret OSINT project
    print("[+] Fetching Maigret OSINT database (soxoj/maigret)...")
    maigret_url = "https://raw.githubusercontent.com/soxoj/maigret/main/maigret/resources/data.json"
    maigret_added = 0
    try:
        m = fetch_json(maigret_url)
        for name, s in m.get("sites", {}).items():
            if not isinstance(s, dict):
                continue
            if name.lower() in existing_keys:
                continue

            url = s.get("url", "")
            url_main = s.get("urlMain", "")
            if not url or "{username}" not in url or not url_main:
                continue

            url_sherlock = url.replace("{username}", "{}")
            absence = s.get("absenceStrs", [])
            claimed = s.get("usernameClaimed", "admin")
            check_type = s.get("checkType", "")

            entry = {
                "url": url_sherlock,
                "urlMain": url_main,
                "username_claimed": claimed
            }

            if "nsfw" in s.get("tags", []):
                entry["isNSFW"] = True

            if absence and isinstance(absence, list):
                entry["errorType"] = "message"
                entry["errorMsg"] = absence
            elif check_type == "status_code":
                entry["errorType"] = "status_code"
            else:
                continue

            combined[name] = entry
            existing_keys.add(name.lower())
            maigret_added += 1
        print(f"    -> Added {maigret_added} new verified sites from Maigret!")
    except Exception as e:
        print(f"    [-] Error fetching Maigret: {e}")

    total_sites = len(combined) - 1
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2)

    print("=" * 60)
    print(f"[✓] Database successfully updated & saved to: {OUTPUT_FILE}")
    print(f"[✓] TOTAL SITES IN DATABASE: {total_sites:,} websites!")
    print("=" * 60)
    return total_sites

if __name__ == "__main__":
    update_database()
