"""GET /api/v1/verify — quick fact verification via Wikipedia."""
from fastapi import APIRouter, Depends, Query

from backend.models.schemas import VerifyResponse
from backend.services.fact_checker import FactChecker, get_fact_checker

router = APIRouter(prefix="/api/v1", tags=["verification"])


@router.get("/verify", response_model=VerifyResponse)
def verify_fact(
    q: str = Query(..., min_length=2, max_length=300, description="Topic to fact-check"),
    checker: FactChecker = Depends(get_fact_checker),
) -> VerifyResponse:
    return checker.verify(q)
