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
