from __future__ import annotations

import re

MULTISPACE_RE = re.compile(r"\s+")
OCR_NOISE_RE = re.compile(r"[|]{2,}|[_]{2,}|[~`]{2,}")
NON_PRINTABLE_RE = re.compile(r"[\x00-\x1f\x7f-\x9f]")
URL_RE = re.compile(r"(https?://\S+|www\.\S+|\b\d{1,3}(?:\.\d{1,3}){3}\S*)", re.I)
TIME_RE = re.compile(r"\b\d{1,2}:\d{2}\s*(?:am|pm)?\b", re.I)
DATE_RE = re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b")
PAGE_COUNTER_RE = re.compile(r"\b\d+\s+of\s+\d+\b", re.I)
OCR_TABLE_NOISE_RE = re.compile(r"(?:\b[a-z]{1,4}\b[\s|]){8,}", re.I)

JUNK_LINE_PATTERNS = [
    re.compile(r"\bfirefox\b", re.I),
    re.compile(r"\bchrome\b", re.I),
    re.compile(r"\bmenu\.php\b", re.I),
    re.compile(r"\bcishcbom\b", re.I),
    re.compile(r"\bchecker\b", re.I),
    re.compile(r"\bfiling section\b", re.I),
    re.compile(r"\bscrutiny report\b", re.I),
    re.compile(r"\bscrutiny report of\b", re.I),
    re.compile(r"\bgrand total\b", re.I),
    re.compile(r"\bcourt fee\b", re.I),
    re.compile(r"\bprocess fee\b", re.I),
    re.compile(r"\bmemo fee\b", re.I),
    re.compile(r"\blimitation\b", re.I),
    re.compile(r"\bdefaults?\b", re.I),
    re.compile(r"\bchecked by\b", re.I),
]

ADMIN_TOKENS = {
    "firefox",
    "checker",
    "scrutiny",
    "report",
    "court",
    "fee",
    "grand",
    "total",
    "limitation",
    "default",
    "menu.php",
    "filing",
}


def clean_ocr_text(text: str | None) -> str:
    if not text:
        return ""

    value = NON_PRINTABLE_RE.sub(" ", text)
    value = OCR_NOISE_RE.sub(" ", value)
    value = OCR_TABLE_NOISE_RE.sub(" ", value)
    value = value.replace("\u2013", "-").replace("\u2014", "-")
    value = MULTISPACE_RE.sub(" ", value)
    return value.strip()


def normalize_for_matching(text: str | None) -> str:
    if not text:
        return ""
    value = clean_ocr_text(text).lower()
    value = URL_RE.sub(" ", value)
    value = re.sub(r"[^a-z0-9\s:/&().,\-]", " ", value)
    value = MULTISPACE_RE.sub(" ", value)
    return value.strip()


def strip_inline_junk(text: str) -> str:
    value = clean_ocr_text(text)
    value = URL_RE.sub(" ", value)
    value = TIME_RE.sub(" ", value)
    value = DATE_RE.sub(" ", value)
    value = PAGE_COUNTER_RE.sub(" ", value)
    value = MULTISPACE_RE.sub(" ", value)
    return value.strip()


def is_junk_line(text: str | None) -> bool:
    if not text:
        return True

    value = clean_ocr_text(text)

    if URL_RE.search(value):
        return True

    for pattern in JUNK_LINE_PATTERNS:
        if pattern.search(value):
            return True

    if len(value) < 2:
        return True

    if PAGE_COUNTER_RE.search(value):
        return True

    if TIME_RE.search(value) and DATE_RE.search(value):
        return True

    if len(re.findall(r"\d", value)) > 20 and len(value) < 200:
        return True
    if OCR_TABLE_NOISE_RE.search(value):
        return True

    return False


def split_lines(text: str | None) -> list[str]:
    if not text:
        return []
    raw_lines = text.splitlines()
    lines: list[str] = []
    for line in raw_lines:
        cleaned = clean_ocr_text(line)
        cleaned = strip_inline_junk(cleaned)
        if cleaned and not is_junk_line(cleaned):
            lines.append(cleaned)
    return lines


def clean_page_text(text: str | None) -> str:
    if not text:
        return ""

    lines = split_lines(text)
    return "\n".join(lines)


def admin_token_count(text: str | None) -> int:
    if not text:
        return 0
    low = normalize_for_matching(text)
    tokens = set(low.split())
    return sum(1 for token in ADMIN_TOKENS if token in tokens)
