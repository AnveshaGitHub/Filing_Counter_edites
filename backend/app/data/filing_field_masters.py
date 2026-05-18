from __future__ import annotations

from app.data.case_type_master import CASE_TYPE_OPTIONS

CASE_TYPE_MASTER = {
    item["code"]: {"label": item["label"], "code": item["code"]}
    for item in CASE_TYPE_OPTIONS
}

CASE_TYPE_ALIASES = {}

LIST_TYPE_MASTER = {
    "INDIVIDUAL": {"label": "INDIVIDUAL", "code": "INDIVIDUAL"},
    "REGULAR": {"label": "REGULAR", "code": "REGULAR"},
    "URGENT": {"label": "URGENT", "code": "URGENT"},
}

LIST_TYPE_ALIASES = {
    "individual": "INDIVIDUAL",
    "regular": "REGULAR",
    "urgent": "URGENT",
}

PARTY_TYPE_MASTER = {
    "Individual": {"label": "Individual", "code": "INDIVIDUAL"},
    "State Department": {"label": "State Department", "code": "STATE_DEPARTMENT"},
    "Central Department": {"label": "Central Department", "code": "CENTRAL_DEPARTMENT"},
    "Other Organization": {"label": "Other Organization", "code": "OTHER_ORGANIZATION"},
}

PARTY_TYPE_ALIASES = {
    "individual": "Individual",
    "state department": "State Department",
    "central department": "Central Department",
    "other organization": "Other Organization",
}

BOOLEAN_TRUE_VALUES = {"true", "1", "yes", "checked", "on"}
BOOLEAN_FALSE_VALUES = {"false", "0", "no", "unchecked", "off", ""}
