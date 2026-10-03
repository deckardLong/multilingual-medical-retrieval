from __future__ import annotations

import re
import unicodedata
from urllib.parse import urlsplit


_CONTROL_OR_ZERO_WIDTH = re.compile(
    "["
    "\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f-\u009f"
    "\u00ad\u180e\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff"
    "]"
)
_NEWLINES = re.compile(r"\n{3,}")
_SPACES = re.compile(r"[^\S\n]+")


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFC", value).replace("\r\n", "\n").replace("\r", "\n")
    value = _CONTROL_OR_ZERO_WIDTH.sub("", value)
    value = _SPACES.sub(" ", value)
    value = _NEWLINES.sub("\n\n", value)
    return value.strip()


def normalize_hostname(url: str) -> str | None:
    try:
        hostname = urlsplit(url).hostname
    except ValueError:
        return None
    if not hostname:
        return None
    hostname = hostname.lower().rstrip(".")
    if hostname.startswith("www."):
        hostname = hostname[4:]
    return hostname or None


def detect_supported_language(text: str) -> tuple[str, float] | None:
    from langdetect import DetectorFactory, detect_langs
    from langdetect.lang_detect_exception import LangDetectException

    DetectorFactory.seed = 0
    try:
        candidates = detect_langs(text)
    except LangDetectException:
        return None
    if not candidates:
        return None
    detected = candidates[0]
    code = detected.lang.lower()
    if code.startswith("zh"):
        code = "zh"
    if code not in {"vi", "zh", "en"}:
        return None
    return code, float(detected.prob)
