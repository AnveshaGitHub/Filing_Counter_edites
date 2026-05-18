from __future__ import annotations

import re

CASE_TYPE_PATTERNS: list[tuple[re.Pattern, str, float]] = [
    (re.compile(r"\bconc(?:\b|\.?\s*no\.?)", re.I), "CONC", 0.99),
    (re.compile(r"\bcontempt\s+petition\b", re.I), "CONC", 0.99),
    (re.compile(r"\bcivil\s+contempt\b", re.I), "CONC", 0.98),
    (re.compile(r"\bmcrc\b", re.I), "MCRC", 0.99),
    (re.compile(r"\bmcrc\s*(?:no\.?|number)?\s*[:\-]?\s*\d+", re.I), "MCRC", 0.99),
    (re.compile(r"\bclass\s+of\s+case\s*[:\-]?\s*mcrc\b", re.I), "MCRC", 0.99),
    (re.compile(r"\bmisc\.?\s*criminal\s+case\s+no\.?\b", re.I), "MCRC", 0.99),
    (re.compile(r"\bmisc(?:ellaneous)?\s+criminal\s+case\b", re.I), "MCRC", 0.98),
    (re.compile(r"\bcra\b", re.I), "CRA", 0.98),
    (re.compile(r"\bcriminal\s+appeal\b", re.I), "CRA", 0.98),
    (re.compile(r"\bcrr\b", re.I), "CRR", 0.98),
    (re.compile(r"\bcriminal\s+revision\b", re.I), "CRR", 0.98),
    (re.compile(r"\bcriminal\s+revision\s+petition\b", re.I), "CRR", 0.98),
    (re.compile(r"\bwp\b", re.I), "WP", 0.95),
    (re.compile(r"\bwrit\s+petition\b", re.I), "WP", 0.95),
]

LIST_TYPE_PATTERNS: list[tuple[re.Pattern, str, float]] = [
    (re.compile(r"\bindividual\b", re.I), "INDIVIDUAL", 0.90),
    (re.compile(r"\bregular\b", re.I), "REGULAR", 0.90),
    (re.compile(r"\burgent\b", re.I), "URGENT", 0.86),
]

VERSUS_PATTERNS = [
    re.compile(r"\bvs\.?\b", re.I),
    re.compile(r"\bversus\b", re.I),
    re.compile(r"\bv/s\b", re.I),
]

PETITIONER_HINTS = [
    "petitioner",
    "applicant",
    "revisionist",
    "appellant",
]

RESPONDENT_HINTS = [
    "respondent",
    "non-applicant",
    "opponent",
]

STATE_DEPT_PATTERNS = [
    re.compile(r"\bstate\s+of\b", re.I),
    re.compile(r"\bstate\s+government\b", re.I),
    re.compile(r"\bsecretary\b", re.I),
    re.compile(r"\bcollector\b", re.I),
    re.compile(r"\bdistrict magistrate\b", re.I),
    re.compile(r"\btehsildar\b", re.I),
    re.compile(r"\bpolice station\b", re.I),
    re.compile(r"\bdepartment\b", re.I),
]

CENTRAL_DEPT_PATTERNS = [
    re.compile(r"\bunion\s+of\s+india\b", re.I),
    re.compile(r"\bcentral government\b", re.I),
    re.compile(r"\bgovernment of india\b", re.I),
    re.compile(r"\bministry of\b", re.I),
    re.compile(r"\bcommissioner of income tax\b", re.I),
    re.compile(r"\brailway\b", re.I),
]

ORG_PATTERNS = [
    re.compile(r"\blimited\b", re.I),
    re.compile(r"\bltd\b", re.I),
    re.compile(r"\bpvt\b", re.I),
    re.compile(r"\bprivate limited\b", re.I),
    re.compile(r"\bcorporation\b", re.I),
    re.compile(r"\bcompany\b", re.I),
    re.compile(r"\bsociety\b", re.I),
    re.compile(r"\btrust\b", re.I),
    re.compile(r"\bboard\b", re.I),
    re.compile(r"\buniversity\b", re.I),
    re.compile(r"\bcommittee\b", re.I),
]

ADVOCATE_HINT_PATTERNS = [
    re.compile(r"\badvocate\b", re.I),
    re.compile(r"\bcounsel\b", re.I),
    re.compile(r"\blearned counsel\b", re.I),
    re.compile(r"\bfor the petitioner\b", re.I),
    re.compile(r"\bfor petitioner\b", re.I),
    re.compile(r"\bfor the applicant\b", re.I),
    re.compile(r"\bfor applicant\b", re.I),
    re.compile(r"\bfor the respondent\b", re.I),
    re.compile(r"\bfor respondent\b", re.I),
    re.compile(r"\bfor non-applicant\b", re.I),
    re.compile(r"\bappearance\b", re.I),
    re.compile(r"\bmemo of appearance\b", re.I),
    re.compile(r"\bvakalatnama\b", re.I),
    re.compile(r"\bvakalat\s+nama\b", re.I),
    re.compile(r"\bname of the main advocate\b", re.I),
]

ENROL_NO_PATTERNS = [
    re.compile(r"\benrol(?:l)?\.?\s*no\.?\s*[:\-]?\s*([A-Za-z0-9\/\-]+)", re.I),
    re.compile(r"\benrollment\s*no\.?\s*[:\-]?\s*([A-Za-z0-9\/\-]+)", re.I),
    re.compile(r"\bbar\s*reg(?:istration)?\s*no\.?\s*[:\-]?\s*([A-Za-z0-9\/\-]+)", re.I),
]

ENROL_YEAR_PATTERNS = [
    re.compile(r"\benrol(?:l)?\s*year\s*[:\-]?\s*(19\d{2}|20\d{2})", re.I),
    re.compile(r"\byear\s*of\s*enrol(?:ment)?\s*[:\-]?\s*(19\d{2}|20\d{2})", re.I),
]

MOBILE_PATTERNS = [
    re.compile(r"\b(?:\+91[-\s]?)?[6-9]\d{9}\b"),
]

NAME_LINE_CLEANUP_PATTERNS = [
    re.compile(r"\badvocate\b", re.I),
    re.compile(r"\bcounsel\b", re.I),
    re.compile(r"\bfor the petitioner\b", re.I),
    re.compile(r"\bfor petitioner\b", re.I),
    re.compile(r"\bfor the respondent\b", re.I),
    re.compile(r"\bfor respondent\b", re.I),
]
