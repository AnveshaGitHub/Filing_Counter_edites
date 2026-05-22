from fastapi import APIRouter

from app.api.v1.filing_extraction import router as filing_extraction_router
from app.api.v1.efiling_fetch import router as efiling_fetch_router
from app.api.v1.master_data import router as master_data_router
from app.api.v1.party_autofill import router as party_autofill_router
from app.api.v1.filing_review import router as filing_review_router
from app.api.v1.filing_payload import router as filing_payload_router
from app.api.v1.filing_full_metadata import router as filing_full_metadata_router
from app.api.v1.filing_submission import router as filing_submission_router
from app.api.v1.ecourt_payload import router as ecourt_payload_router
from app.api.v1.layout_debug import router as layout_debug_router
from app.api.v1.test_documents import router as test_documents_router
from app.api.v1.page_classification import router as page_classification_router
from app.api.v1.benchmark import router as benchmark_router
from app.api.v1.field_router_debug import router as field_router_debug_router
from app.api.v1.region_debug import router as region_debug_router
from app.api.v1.filing_candidates import router as filing_candidates_router

api_router = APIRouter()
api_router.include_router(efiling_fetch_router)
api_router.include_router(master_data_router)
api_router.include_router(party_autofill_router)
api_router.include_router(filing_extraction_router)
api_router.include_router(filing_review_router)
api_router.include_router(filing_payload_router)
api_router.include_router(filing_full_metadata_router)
api_router.include_router(filing_submission_router)
api_router.include_router(ecourt_payload_router)
api_router.include_router(layout_debug_router)
api_router.include_router(test_documents_router)
api_router.include_router(page_classification_router)
api_router.include_router(benchmark_router)
api_router.include_router(field_router_debug_router)
api_router.include_router(region_debug_router)
api_router.include_router(filing_candidates_router)
