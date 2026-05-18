from __future__ import annotations

from app.services.filing.extractors.case_type_extractor import CaseTypeExtractor
from app.services.filing.extractors.list_type_extractor import ListTypeExtractor
from app.services.filing.extractors.petitioner_name_extractor import PetitionerNameExtractor
from app.services.filing.extractors.respondent_name_extractor import RespondentNameExtractor
from app.services.filing.extractors.party_type_extractor import PartyTypeExtractor
from app.services.filing.extractors.advocate_name_extractor import AdvocateNameExtractor
from app.services.filing.extractors.advocate_enrol_no_extractor import AdvocateEnrolNoExtractor
from app.services.filing.extractors.advocate_enrol_year_extractor import AdvocateEnrolYearExtractor
from app.services.filing.extractors.advocate_mobile_extractor import AdvocateMobileExtractor
from app.services.filing.extractors.checkbox_extractor import CheckboxExtractor
from app.services.filing.extractors.multi_advocate_extractor import MultiAdvocateExtractor
from app.services.filing.extractors.multi_party_extractor import MultiPartyExtractor
from app.services.filing.extractors.petitioner_more_details_extractor import (
    PetitionerMoreDetailsExtractor,
)
from app.services.filing.extractors.respondent_more_details_extractor import (
    RespondentMoreDetailsExtractor,
)


class CandidateExtractionService:
    def __init__(self) -> None:
        self._extractors = {
            "case_type": CaseTypeExtractor(),
            "list_type": ListTypeExtractor(),
            "petitioner_name": PetitionerNameExtractor(),
            "respondent_name": RespondentNameExtractor(),
            "petitioner_party_type": PartyTypeExtractor(
                field_key="petitioner_party_type",
                linked_name_field="petitioner_name",
            ),
            "respondent_party_type": PartyTypeExtractor(
                field_key="respondent_party_type",
                linked_name_field="respondent_name",
            ),
            "advocate_name": AdvocateNameExtractor(),
            "advocate_enrol_no": AdvocateEnrolNoExtractor(),
            "advocate_enrol_year": AdvocateEnrolYearExtractor(),
            "advocate_mobile": AdvocateMobileExtractor(),
            "with_application": CheckboxExtractor("with_application"),
            "hide_party_petitioner": CheckboxExtractor("hide_party_petitioner"),
            "hide_party_respondent": CheckboxExtractor("hide_party_respondent"),
            "differently_abled_petitioner": CheckboxExtractor("differently_abled_petitioner"),
            "differently_abled_respondent": CheckboxExtractor("differently_abled_respondent"),
            "advocate_rows": MultiAdvocateExtractor(),
            "petitioner_party_candidates": MultiPartyExtractor(
                field_key="petitioner_party_candidates",
                side="petitioner",
            ),
            "respondent_party_candidates": MultiPartyExtractor(
                field_key="respondent_party_candidates",
                side="respondent",
            ),
            "petitioner_more_details": PetitionerMoreDetailsExtractor(),
            "respondent_more_details": RespondentMoreDetailsExtractor(),
        }

    def extract_candidates(self, field_key: str, context: dict) -> list[dict]:
        extractor = self._extractors.get(field_key)
        if not extractor:
            return []
        return extractor.extract(context)
