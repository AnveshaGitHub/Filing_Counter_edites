from __future__ import annotations

RELATION_OPTIONS: list[dict[str, str]] = [
    {"code": "S/o", "label": "S/o"},
    {"code": "D/o", "label": "D/o"},
    {"code": "W/o", "label": "W/o"},
    {"code": "C/o", "label": "C/o"},
]

GENDER_OPTIONS: list[dict[str, str]] = [
    {"code": "Male", "label": "Male"},
    {"code": "Female", "label": "Female"},
    {"code": "Other", "label": "Other"},
]

IDENTITY_PROOF_OPTIONS: list[dict[str, str]] = [
    {"code": "AADHAAR", "label": "Aadhaar"},
    {"code": "PAN", "label": "PAN"},
    {"code": "VOTER_ID", "label": "Voter ID"},
    {"code": "DRIVING_LICENSE", "label": "Driving License"},
    {"code": "PASSPORT", "label": "Passport"},
]

CASTE_OPTIONS: list[dict[str, str]] = [
    {"code": "GENERAL", "label": "General"},
    {"code": "OBC", "label": "OBC"},
    {"code": "OBC-NCL", "label": "OBC-NCL"},
    {"code": "SC", "label": "SC"},
    {"code": "ST", "label": "ST"},
]

STATE_OPTIONS: list[dict[str, str]] = [
    {"code": "MP", "label": "Madhya Pradesh"},
    {"code": "UP", "label": "Uttar Pradesh"},
    {"code": "RJ", "label": "Rajasthan"},
    {"code": "MH", "label": "Maharashtra"},
    {"code": "DL", "label": "Delhi"},
    {"code": "HR", "label": "Haryana"},
    {"code": "PB", "label": "Punjab"},
    {"code": "CH", "label": "Chandigarh"},
]

DISTRICT_OPTIONS: list[dict[str, str]] = [
    {"code": "BHOPAL", "label": "Bhopal", "state_code": "MP"},
    {"code": "JABALPUR", "label": "Jabalpur", "state_code": "MP"},
    {"code": "INDORE", "label": "Indore", "state_code": "MP"},
    {"code": "GWALIOR", "label": "Gwalior", "state_code": "MP"},
    {"code": "SAGAR", "label": "Sagar", "state_code": "MP"},
    {"code": "RAISEN", "label": "Raisen", "state_code": "MP"},
    {"code": "SATNA", "label": "Satna", "state_code": "MP"},
    {"code": "REWA", "label": "Rewa", "state_code": "MP"},
    {"code": "CHHATARPUR", "label": "Chhatarpur", "state_code": "MP"},
    {"code": "MANDLA", "label": "Mandla", "state_code": "MP"},
]

TEHSIL_OPTIONS: list[dict[str, str]] = [
    {"code": "HUZUR", "label": "Huzur", "district_code": "BHOPAL"},
    {"code": "RAGHURAJNAGAR", "label": "Raghurajnagar", "district_code": "SATNA"},
    {"code": "UDAYPURA", "label": "Udaypura", "district_code": "RAISEN"},
    {"code": "JABALPUR", "label": "Jabalpur", "district_code": "JABALPUR"},
    {"code": "INDORE", "label": "Indore", "district_code": "INDORE"},
    {"code": "NAINPUR", "label": "Nainpur", "district_code": "MANDLA"},
]

VILLAGE_OPTIONS: list[dict[str, str]] = [
    {"code": "UMARI", "label": "Umari", "tehsil_code": "UDAYPURA"},
    {"code": "KOLHUA", "label": "Kolhua", "tehsil_code": "RAGHURAJNAGAR"},
]
