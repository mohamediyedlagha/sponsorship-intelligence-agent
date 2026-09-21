from pydantic import (
    BaseModel,
    Field,
)


class Recommendation(BaseModel):

    company: str

    signal_type: str

    # Canonical description of the underlying
    # business event.
    event_summary: str

    # ========================================================
    # EVENT MATCHING
    # ========================================================

    recommended_event: str

    event_fit_reason: str

    # ========================================================
    # SCORING
    # ========================================================

    business_trigger_score: int = Field(
        ge=0,
        le=25,
    )

    event_fit_score: int = Field(
        ge=0,
        le=25,
    )

    evidence_quality_score: int = Field(
        ge=0,
        le=20,
    )

    commercial_intent_score: int = Field(
        ge=0,
        le=15,
    )

    recency_score: int = Field(
        ge=0,
        le=15,
    )

    total_score: int = Field(
        ge=0,
        le=100,
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    should_recommend: bool

    reason: str

    next_step: str

    sources: list[str]