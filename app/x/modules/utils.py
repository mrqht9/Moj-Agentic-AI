import mimetypes
import os
import re
import uuid
from pathlib import Path
from typing import Optional

import requests


def is_url(s: str) -> bool:
    return bool(re.match(r"^https?://", (s or "").strip(), re.I))


def guess_ext_from_url_or_ct(url: str, content_type: Optional[str]) -> str:
    if content_type:
        ext = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if ext:
            return ext
    path = Path(url.split("?")[0])
    if path.suffix:
        return path.suffix
    return ".bin"


def download_to_temp(url: str, folder: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, stream=True, timeout=120, headers=headers, allow_redirects=True)
    r.raise_for_status()
    ext = guess_ext_from_url_or_ct(url, r.headers.get("Content-Type"))
    out_path = os.path.join(folder, f"dl_{uuid.uuid4().hex}{ext}")
    with open(out_path, "wb") as f:
        for chunk in r.iter_content(1024 * 1024):
            if chunk:
                f.write(chunk)
    return out_path


def safe_label(label: str) -> str:
    label = (label or '').strip()
    label = re.sub(r'[^a-zA-Z0-9_\-\.]+', '_', label)
    return label[:80] if label else 'account'


def normalize_cookies(data: dict) -> dict:
    """
    تحويل أي صيغة كوكيز إلى الصيغة الرسمية المعتمدة.
    
    الصيغة الرسمية:
    {
        "cookies": [
            {
                "name": "...",
                "value": "...",
                "domain": ".x.com",
                "path": "/",
                "expires": 1234567890.123,
                "httpOnly": true/false,
                "secure": true/false,
                "sameSite": "None"/"Lax"/"Strict"
            },
            ...
        ],
        "origins": []
    }
    
    الصيغ المدعومة للتحويل:
    1. قائمة مباشرة من الكوكيز: [{"name": "...", "value": "..."}]
    2. صيغة Playwright: {"cookies": [...], "origins": [...]}
    3. صيغة EditThisCookie: [{"name": "...", "value": "...", "expirationDate": ...}]
    4. صيغة Netscape/curl: نص بصيغة معينة
    """
    if not data:
        return {"cookies": [], "origins": []}
    
    cookies_list = []
    
    # إذا كانت البيانات قائمة مباشرة
    if isinstance(data, list):
        cookies_list = data
    # إذا كانت البيانات dict تحتوي على cookies
    elif isinstance(data, dict):
        if "cookies" in data:
            cookies_list = data.get("cookies", [])
        else:
            # ربما كوكيز واحد فقط
            if "name" in data and "value" in data:
                cookies_list = [data]
    
    # تحويل كل كوكيز للصيغة الرسمية
    normalized_cookies = []
    for cookie in cookies_list:
        if not isinstance(cookie, dict):
            continue
        
        # استخراج الاسم والقيمة (مطلوبان)
        name = cookie.get("name", "")
        value = cookie.get("value", "")
        
        if not name:
            continue
        
        # تحويل domain
        domain = cookie.get("domain", ".x.com")
        if not domain:
            domain = ".x.com"
        # تأكد أن domain يبدأ بنقطة للـ x.com
        if "x.com" in domain or "twitter.com" in domain:
            if not domain.startswith("."):
                domain = "." + domain
            # توحيد إلى x.com
            domain = domain.replace("twitter.com", "x.com")
        
        # تحويل expires/expirationDate
        expires = cookie.get("expires") or cookie.get("expirationDate") or cookie.get("expiry")
        if expires is None:
            # تعيين انتهاء افتراضي (سنة من الآن)
            import time
            expires = time.time() + (365 * 24 * 60 * 60)
        elif isinstance(expires, int):
            # إذا كان timestamp بالثواني الكاملة، حوله لـ float
            expires = float(expires)
        
        # تحويل httpOnly
        http_only = cookie.get("httpOnly") or cookie.get("httponly") or cookie.get("HttpOnly")
        if http_only is None:
            http_only = False
        elif isinstance(http_only, str):
            http_only = http_only.lower() in ("true", "1", "yes")
        
        # تحويل secure
        secure = cookie.get("secure") or cookie.get("Secure")
        if secure is None:
            secure = True
        elif isinstance(secure, str):
            secure = secure.lower() in ("true", "1", "yes")
        
        # تحويل sameSite
        same_site = cookie.get("sameSite") or cookie.get("samesite") or cookie.get("SameSite")
        if same_site is None:
            same_site = "None"
        elif isinstance(same_site, str):
            # توحيد الصيغة
            same_site_lower = same_site.lower()
            if same_site_lower == "lax":
                same_site = "Lax"
            elif same_site_lower == "strict":
                same_site = "Strict"
            elif same_site_lower in ("none", "no_restriction", "unspecified"):
                same_site = "None"
            else:
                same_site = "None"
        
        # path
        path = cookie.get("path", "/")
        if not path:
            path = "/"
        
        # إنشاء الكوكيز بالصيغة الرسمية
        normalized_cookie = {
            "name": name,
            "value": value,
            "domain": domain,
            "path": path,
            "expires": expires,
            "httpOnly": bool(http_only),
            "secure": bool(secure),
            "sameSite": same_site
        }
        
        normalized_cookies.append(normalized_cookie)
    
    return {
        "cookies": normalized_cookies,
        "origins": []
    }
