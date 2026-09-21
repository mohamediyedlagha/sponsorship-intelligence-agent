from src.agents.verification_agent import (
    VerificationAgent,
)
from src.memory.database import Database
from src.models.evidence import (
    EvidenceAssessment,
    EvidenceQuality,
)
from src.models.signal import (
    BusinessSignal,
    SignalType,
)
from src.utils.hashing import (
    generate_content_hash,
)


class FakeVerificationLLM:
    """
    Fake deterministic LLM used for testing
    the VerificationAgent.
    """

    def structured_chat(
        self,
        prompt: str,
        schema,
        system_prompt: str | None = None,
    ):

        return EvidenceAssessment(
            company="Mistral AI",
            source_quality=(
                EvidenceQuality.HIGH
            ),
            evidence_quality_score=18,
            claim_supported=True,
            evidence_clear=True,
            reason=(
                "The article directly states "
                "that the company launched "
                "a new enterprise AI platform."
            ),
            confidence=0.94,
        )


def test_verification_agent(
    tmp_path,
):
    """
    Verify that a strong business signal
    receives a high-quality evidence assessment.
    """

    # --------------------------------------------------
    # Temporary database
    # --------------------------------------------------

    database_path = (
        tmp_path
        / "verification.db"
    )

    db = Database(
        database_path=database_path
    )

    # --------------------------------------------------
    # Create article
    # --------------------------------------------------

    content = (
        "Mistral AI officially announced "
        "a new enterprise AI platform "
        "for business customers."
    )

    content_hash = (
        generate_content_hash(
            company="Mistral AI",
            title=(
                "Mistral launches "
                "enterprise AI platform"
            ),
            content=content,
        )
    )

    article_id = db.save_article(
        company="Mistral AI",
        title=(
            "Mistral launches "
            "enterprise AI platform"
        ),
        url=(
            "https://mistral.ai/"
            "news/example"
        ),
        source="mistral.ai",
        content=content,
        content_hash=content_hash,
    )

    assert article_id is not None

    # --------------------------------------------------
    # Create business signal
    # --------------------------------------------------

    signal = BusinessSignal(
        company="Mistral AI",
        signal_type=(
            SignalType.PRODUCT_LAUNCH
        ),
        summary=(
            "Mistral AI launched "
            "a new enterprise platform."
        ),
        evidence=(
            "The article explicitly states "
            "that the company announced "
            "a new enterprise AI platform."
        ),
        business_relevance=90,
        confidence=0.95,
        is_relevant=True,
    )

    # --------------------------------------------------
    # Create agent
    # --------------------------------------------------

    agent = VerificationAgent(
        database=db,
        llm=FakeVerificationLLM(),
    )

    # --------------------------------------------------
    # Verify evidence
    # --------------------------------------------------

    result = agent.verify(
        article_id=article_id,
        signal=signal,
    )

    # --------------------------------------------------
    # Assertions
    # --------------------------------------------------

    assert result is not None

    assert result.company == "Mistral AI"

    assert (
        result.source_quality
        == EvidenceQuality.HIGH
    )

    assert (
        result.evidence_quality_score
        == 18
    )

    assert (
        result.claim_supported
        is True
    )

    assert (
        result.evidence_clear
        is True
    )

    assert (
        result.confidence
        == 0.94
    )


def test_verification_missing_article(
    tmp_path,
):
    """
    Verification should safely return None
    when the requested article does not exist.
    """

    database_path = (
        tmp_path
        / "missing_article.db"
    )

    db = Database(
        database_path=database_path
    )

    signal = BusinessSignal(
        company="Mistral AI",
        signal_type=(
            SignalType.PRODUCT_LAUNCH
        ),
        summary="Example signal.",
        evidence="Example evidence.",
        business_relevance=80,
        confidence=0.90,
        is_relevant=True,
    )

    agent = VerificationAgent(
        database=db,
        llm=FakeVerificationLLM(),
    )

    result = agent.verify(
        article_id=999,
        signal=signal,
    )

    assert result is None