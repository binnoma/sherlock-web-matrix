import hashlib
import socket
import urllib.parse
import urllib.request
import json
import re

DISPOSABLE_DOMAINS = {
    "mailinator.com", "tempmail.com", "10minutemail.com", "guerrillamail.com",
    "sharklasers.com", "throwawaymail.com", "yopmail.com", "getairmail.com",
    "trashmail.com", "fakemailgenerator.com", "dispostable.com"
}

COUNTRY_MAP = {
    "+971": {"name": "الإمارات العربية المتحدة", "iso": "AE", "flag": "🇦🇪", "digits": 9},
    "+966": {"name": "المملكة العربية السعودية", "iso": "SA", "flag": "🇸🇦", "digits": 9},
    "+20":  {"name": "جمهورية مصر العربية", "iso": "EG", "flag": "🇪🇬", "digits": 10},
    "+965": {"name": "دولة الكويت", "iso": "KW", "flag": "🇰🇼", "digits": 8},
    "+974": {"name": "دولة قطر", "iso": "QA", "flag": "🇶🇦", "digits": 8},
    "+973": {"name": "مملكة البحرين", "iso": "BH", "flag": "🇧🇭", "digits": 8},
    "+968": {"name": "سلطنة عُمان", "iso": "OM", "flag": "🇴🇲", "digits": 8},
    "+962": {"name": "المملكة الأردنية الهاشمية", "iso": "JO", "flag": "🇯🇴", "digits": 9},
    "+964": {"name": "جمهورية العراق", "iso": "IQ", "flag": "🇮🇶", "digits": 10},
    "+961": {"name": "الجمهورية اللبنانية", "iso": "LB", "flag": "🇱🇧", "digits": 8},
    "+212": {"name": "المملكة المغربية", "iso": "MA", "flag": "🇲🇦", "digits": 9},
    "+213": {"name": "الجمهورية الجزائرية", "iso": "DZ", "flag": "🇩🇿", "digits": 9},
    "+216": {"name": "الجمهورية التونسية", "iso": "TN", "flag": "🇹🇳", "digits": 8},
    "+1":   {"name": "الولايات المتحدة / كندا", "iso": "US", "flag": "🇺🇸", "digits": 10},
    "+44":  {"name": "المملكة المتحدة", "iso": "GB", "flag": "🇬🇧", "digits": 10},
    "+49":  {"name": "ألمانيا", "iso": "DE", "flag": "🇩🇪", "digits": 10},
    "+33":  {"name": "فرنسا", "iso": "FR", "flag": "🇫🇷", "digits": 9},
    "+90":  {"name": "تركيا", "iso": "TR", "flag": "🇹🇷", "digits": 10},
}

def recon_username(username: str) -> dict:
    username = username.strip()
    data = {
        "username": username,
        "real_name": None,
        "avatar_url": f"https://ui-avatars.com/api/?name={urllib.parse.quote(username)}&background=00ff66&color=000&size=128&bold=true",
        "bio": None,
        "location": None,
        "company": None,
        "source": None
    }

    # 1. Query GitHub User API
    try:
        gh_url = f"https://api.github.com/users/{username}"
        req = urllib.request.Request(gh_url, headers={"User-Agent": "SherlockOSINT/1.0"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            if resp.status == 200:
                gh_data = json.loads(resp.read().decode("utf-8"))
                if gh_data.get("name"):
                    data["real_name"] = gh_data.get("name")
                if gh_data.get("avatar_url"):
                    data["avatar_url"] = gh_data.get("avatar_url")
                if gh_data.get("bio"):
                    data["bio"] = gh_data.get("bio")
                if gh_data.get("location"):
                    data["location"] = gh_data.get("location")
                if gh_data.get("company"):
                    data["company"] = gh_data.get("company")
                data["source"] = "GitHub Profile"
                return data
    except Exception:
        pass

    # 2. Query Gravatar Profile by username
    try:
        gravatar_url = f"https://en.gravatar.com/{username}.json"
        req = urllib.request.Request(gravatar_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                gdata = json.loads(resp.read().decode("utf-8"))
                entries = gdata.get("entry", [])
                if entries:
                    e = entries[0]
                    name = e.get("displayName") or e.get("name", {}).get("formatted")
                    if name:
                        data["real_name"] = name
                    if e.get("thumbnailUrl"):
                        data["avatar_url"] = e.get("thumbnailUrl")
                    if e.get("aboutMe"):
                        data["bio"] = e.get("aboutMe")
                    if e.get("currentLocation"):
                        data["location"] = e.get("currentLocation")
                    data["source"] = "Gravatar Profile"
                    return data
    except Exception:
        pass

    return data

def recon_email(email: str) -> dict:
    email = email.strip().lower()
    if "@" not in email:
        return {"error": "Invalid email format"}

    username, domain = email.split("@", 1)
    email_hash = hashlib.md5(email.encode("utf-8")).hexdigest()

    gravatar_profile_url = f"https://en.gravatar.com/{email_hash}.json"
    has_gravatar = False
    gravatar_name = None
    gravatar_avatar = None
    gravatar_bio = None

    try:
        req = urllib.request.Request(gravatar_profile_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                gdata = json.loads(resp.read().decode("utf-8"))
                entries = gdata.get("entry", [])
                if entries:
                    e = entries[0]
                    has_gravatar = True
                    gravatar_avatar = e.get("thumbnailUrl")
                    gravatar_name = e.get("displayName") or e.get("name", {}).get("formatted")
                    gravatar_bio = e.get("aboutMe")
    except Exception:
        pass

    is_disposable = domain in DISPOSABLE_DOMAINS
    domain_valid = False

    try:
        socket.gethostbyname(domain)
        domain_valid = True
    except Exception:
        domain_valid = False

    default_avatar = f"https://www.gravatar.com/avatar/{email_hash}?d=identicon&s=128"

    return {
        "email": email,
        "username": username,
        "domain": domain,
        "domain_valid": domain_valid,
        "is_disposable": is_disposable,
        "has_gravatar": has_gravatar,
        "gravatar_avatar": gravatar_avatar or default_avatar,
        "gravatar_name": gravatar_name,
        "gravatar_bio": gravatar_bio,
        "gravatar_profile": f"https://gravatar.com/{email_hash}" if has_gravatar else None,
        "google_search": f"https://www.google.com/search?q=%22{urllib.parse.quote(email)}%22",
        "hibp_link": f"https://haveibeenpwned.com/account/{urllib.parse.quote(email)}"
    }

def recon_phone(phone_input: str, default_prefix: str = "+971") -> dict:
    cleaned = re.sub(r"[^\d+]", "", phone_input.strip())
    if not cleaned.startswith("+"):
        if cleaned.startswith("00"):
            cleaned = "+" + cleaned[2:]
        else:
            cleaned = default_prefix + cleaned.lstrip("0")

    matched_country = None
    matched_prefix = None
    for prefix, info in sorted(COUNTRY_MAP.items(), key=lambda x: len(x[0]), reverse=True):
        if cleaned.startswith(prefix):
            matched_prefix = prefix
            matched_country = info
            break

    pure_digits = re.sub(r"\D", "", cleaned)
    whatsapp_url = f"https://wa.me/{pure_digits}"
    telegram_url = f"https://t.me/+{pure_digits}"
    truecaller_url = f"https://www.truecaller.com/search/{matched_country['iso'].lower() if matched_country else 'ae'}/{pure_digits}"

    return {
        "full_number": cleaned,
        "pure_digits": pure_digits,
        "country": matched_country["name"] if matched_country else "دولة غير محددة",
        "iso": matched_country["iso"] if matched_country else "XX",
        "flag": matched_country["flag"] if matched_country else "🌐",
        "dial_code": matched_prefix if matched_prefix else "+",
        "whatsapp_url": whatsapp_url,
        "telegram_url": telegram_url,
        "truecaller_url": truecaller_url,
        "google_search": f"https://www.google.com/search?q=%22{urllib.parse.quote(cleaned)}%22"
    }

def get_site_favicon(url_main: str) -> str:
    try:
        parsed = urllib.parse.urlparse(url_main)
        domain = parsed.netloc or parsed.path
        return f"https://www.google.com/s2/favicons?domain={domain}&sz=64"
    except Exception:
        return ""
