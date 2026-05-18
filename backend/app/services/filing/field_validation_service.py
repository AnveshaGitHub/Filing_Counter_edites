from __future__ import annotations

import re
from datetime import datetime

from app.schemas.filing_fields import FilingFieldDefinition


class FieldValidationService:
    def normalize_value(self, field_def: FilingFieldDefinition, raw_value: str | None) -> str | None:
        if raw_value is None:
            return None

        value = raw_value.strip()
        if not value:
            return None

        lower_value = value.lower()
        if field_def.aliases and lower_value in field_def.aliases:
            return field_def.aliases[lower_value]

        if field_def.field_type == "mobile":
            digits = re.sub(r"\D", "", value)
            if len(digits) == 12 and digits.startswith("91"):
                digits = digits[2:]
            return digits

        return value

    def validate(self, field_def: FilingFieldDefinition, value: str | None) -> tuple[bool, str | None]:
        if field_def.required and not value:
            return False, "required_field_missing"

        if not value:
            return True, None

        if field_def.allowed_values and value not in field_def.allowed_values:
            return False, f"value_not_in_allowed_values:{value}"

        if field_def.key == "advocate_enrol_year":
            try:
                year = int(value)
            except ValueError:
                return False, "invalid_year_format"

            current = datetime.utcnow().year
            if not (1950 <= year <= current):
                return False, "year_out_of_range"

        if field_def.key == "advocate_mobile":
            if not re.fullmatch(r"[6-9]\d{9}", value):
                return False, "invalid_mobile_format"

        if field_def.key == "advocate_enrol_no":
            if len(value) < 3:
                return False, "enrol_no_too_short"

        return True, None
