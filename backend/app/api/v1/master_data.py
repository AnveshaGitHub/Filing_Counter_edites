from __future__ import annotations

from fastapi import APIRouter, Query

from app.schemas.master_data import MasterListResponse, LinkedMasterListResponse
from app.services.master_data_service import MasterDataService

router = APIRouter(prefix="/masters", tags=["masters"])


@router.get("/case-types", response_model=MasterListResponse)
def get_case_types():
    return MasterDataService().get_case_types()


@router.get("/special-cases", response_model=MasterListResponse)
def get_special_cases():
    return MasterDataService().get_special_cases()


@router.get("/party-name-suffixes", response_model=MasterListResponse)
def get_party_name_suffixes():
    return MasterDataService().get_party_name_suffixes()


@router.get("/list-types", response_model=MasterListResponse)
def get_list_types():
    return MasterDataService().get_list_types()


@router.get("/relations", response_model=MasterListResponse)
def get_relations():
    return MasterDataService().get_relations()


@router.get("/genders", response_model=MasterListResponse)
def get_genders():
    return MasterDataService().get_genders()


@router.get("/states", response_model=MasterListResponse)
def get_states():
    return MasterDataService().get_states()


@router.get("/districts", response_model=LinkedMasterListResponse)
def get_districts(state_code: str | None = Query(default=None)):
    return MasterDataService().get_districts(state_code=state_code)


@router.get("/tehsils", response_model=LinkedMasterListResponse)
def get_tehsils(district_code: str | None = Query(default=None)):
    return MasterDataService().get_tehsils(district_code=district_code)


@router.get("/villages", response_model=LinkedMasterListResponse)
def get_villages(tehsil_code: str | None = Query(default=None)):
    return MasterDataService().get_villages(tehsil_code=tehsil_code)


@router.get("/castes", response_model=MasterListResponse)
def get_castes():
    return MasterDataService().get_castes()


@router.get("/identity-proofs", response_model=MasterListResponse)
def get_identity_proofs():
    return MasterDataService().get_identity_proofs()
