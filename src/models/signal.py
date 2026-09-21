from enum import Enum

from pydantic import BaseModel, Field


class SignalType(str, Enum):
    PRODUCT_LAUNCH = "PRODUCT_LAUNCH"
    MARKET_EXPANSION = "MARKET_EXPANSION"
    FUNDING = "FUNDING"
    PARTNERSHIP = "PARTNERSHIP"
    ACQUISITION = "ACQUISITION"
    HIRING_GROWTH = "HIRING_GROWTH"
    BRAND_CAMPAIGN = "BRAND_CAMPAIGN"
    LEADERSHIP_CHANGE = "LEADERSHIP_CHANGE"
    OTHER = "OTHER"


class BusinessSignal(BaseModel):
    company: str

    signal_type: SignalType

    summary: str

    evidence: str

    business_relevance: int = Field(
        ge=0,
        le=100,
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    is_relevant: bool