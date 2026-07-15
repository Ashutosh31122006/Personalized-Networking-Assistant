"""POST /api/v1/generate -- the orchestration & request handler.

Pipeline: validate input -> DistilBERT theme analysis -> GPT-2 starter
generation -> VALIDATE each starter is on-topic -> log -> return themes + starters.
"""
from fastapi import APIRouter, Depends, HTTPException

from backend.models.schemas import GenerateRequest, GenerateResponse
from backend.services.theme_extractor import ThemeExtractor, get_theme_extractor
from backend.services.starter_generator import StarterGenerator, get_starter_generator
from backend.services.history_store import HistoryStore, get_history_store
from backend.services.validator import StarterValidator

router = APIRouter(prefix="/api/v1", tags=["generation"])


@router.post("/generate", response_model=GenerateResponse)
def generate_starters(
    payload: GenerateRequest,
    extractor: ThemeExtractor = Depends(get_theme_extractor),
    generator: StarterGenerator = Depends(get_starter_generator),
    store: HistoryStore = Depends(get_history_store),
) -> GenerateResponse:
    if not payload.event_description.strip():
        raise HTTPException(status_code=422, detail="event_description cannot be blank")

    # 1) Analyze the event into themes (DistilBERT zero-shot).
    themes = extractor.extract(payload.event_description, extra_labels=payload.interests)

    # 2) Over-generate candidates so validation has room to drop weak ones.
    #    Kept small and capped: generation time scales with this count, and
    #    the validator now checks the surplus in a single batched pass.
    candidates = generator.generate(
        event_description=payload.event_description,
        user_bio=payload.user_bio or "",
        themes=themes,
        num_starters=min(payload.num_starters + 1, 6),
    )

    # 3) Validate: keep only starters that are genuinely on-topic.
    validator = StarterValidator(extractor)
    kept, rejected = validator.validate(candidates, themes, payload.event_description)
    starters = kept[: payload.num_starters]

    # 4) Log the validated starters to history.
    store.log_starters(payload.event_description, payload.interests, starters)

    return GenerateResponse(
        themes=themes,
        starters=starters,
        engine=generator.engine,
        rejected=rejected,
    )
