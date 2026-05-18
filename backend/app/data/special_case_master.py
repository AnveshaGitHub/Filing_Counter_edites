from __future__ import annotations

SPECIAL_CASE_OPTIONS: list[dict[str, str]] = [
    {"code": "Senior Citizen Case", "label": "Senior Citizen Case"},
    {"code": "Crime Against Children", "label": "Crime Against Children"},
    {"code": "Crime Against Women", "label": "Crime Against Women"},
    {"code": "Scheduled Caste Case", "label": "Scheduled Caste Case"},
    {"code": "Scheduled Tribe Case", "label": "Scheduled Tribe Case"},
    {"code": "OBC-NCL Case", "label": "OBC-NCL Case"},
    {"code": "Yellow Card Holder Case", "label": "Yellow Card Holder Case"},
    {"code": "HIV Person Case", "label": "HIV Person Case"},
    {"code": "Whether this Hon'ble Court is a Party", "label": "Whether this Hon'ble Court is a Party"},
    {"code": "Whether ex or Sitting MP/MLA is a party", "label": "Whether ex or Sitting MP/MLA is a party"},
]

PARTY_NAME_SUFFIX_OPTIONS: list[dict[str, str]] = [
    {"code": "", "label": "SELECT"},
    {"code": "AND ANOTHER", "label": "AND ANOTHER"},
    {"code": "AND OTHERS", "label": "AND OTHERS"},
    {"code": "AND OTHERS ETC.", "label": "AND OTHERS ETC."},
]
