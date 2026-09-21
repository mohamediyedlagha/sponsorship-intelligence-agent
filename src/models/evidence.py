from enum import Enum

from pydantic import BaseModel, Field


class EvidenceQuality(str, Enum):
    """
    Overall quality of the evidence supporting
    a detected business signal.
    """

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class EvidenceAssessment(BaseModel):
    """
    Structured result returned by the
    VerificationAgent.
    """

    company: str

    source_quality: EvidenceQuality

    evidence_quality_score: int = Field(
        ge=0,
        le=20,
    )

    claim_supported: bool

    evidence_clear: bool

    reason: str

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )