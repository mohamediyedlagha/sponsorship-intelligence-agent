from src.agents.recommendation_agent import (
    RecommendationAgent,
)
from src.memory.database import Database
from src.models.evidence import (
    EvidenceAssessment,
    EvidenceQuality,
)
from src.models.opportunity import (
    OpportunityAnalysis,
)
from src.models.signal import (
    BusinessSignal,
    SignalType,
)
from src.utils.hashing import (
    generate_content_hash,
)


# ============================================================
# FAKE LLMS
# ============================================================


class FakeOpportunityLLM:
    """
    Deterministic fake LLM for a strong sponsorship
    opportunity with a clear RAISE event fit.
    """

    def structured_chat(
        self,
        prompt: str,
        schema,
        system_prompt: str | None = None,
    ):

        return OpportunityAnalysis(
            company="Mistral AI",

            recommended_event="RAISE",

            event_fit_reason=(
                "The enterprise AI product launch "
                "fits RAISE because the event focuses "
                "on enterprise AI, AI adoption and "
                "technology decision-makers."
            ),

            business_trigger_score=24,

            event_fit_score=22,

            evidence_quality_score=18,

            commercial_intent_score=13,

            recency_score=14,

            total_score=92,

            confidence=0.92,

            reason=(
                "The new enterprise product creates "
                "a credible reason for increased "
                "visibility among business "
                "decision-makers."
            ),

            next_step=(
                "Identify the marketing or "
                "partnerships lead and prepare "
                "a targeted RAISE sponsorship "
                "introduction."
            ),
        )


class FakeNoEventFitLLM:
    """
    Fake LLM returning a high numerical score but
    no credible fit with RAISE, MACHINA or SIGNAL WEEK.

    Application code must prevent a recommendation
    when recommended_event is NONE.
    """

    def structured_chat(
        self,
        prompt: str,
        schema,
        system_prompt: str | None = None,
    ):

        return OpportunityAnalysis(
            company="Mistral AI",

            recommended_event="NONE",

            event_fit_reason=(
                "The current business event does not "
                "have a sufficiently clear connection "
                "with the available sponsorship events."
            ),

            business_trigger_score=25,

            event_fit_score=20,

            evidence_quality_score=18,

            commercial_intent_score=15,

            recency_score=15,

            total_score=93,

            confidence=0.95,

            reason=(
                "The business event is important, "
                "but no sufficiently clear sponsorship "
                "event fit was identified."
            ),

            next_step=(
                "Continue monitoring for a business "
                "event with a clearer event fit."
            ),
        )


# ============================================================
# TEST DATA HELPERS
# ============================================================


def create_test_article(
    db: Database,
) -> int:

    content = (
        "Mistral AI officially announced "
        "a new enterprise AI platform "
        "for business customers."
    )

    content_hash = (
        generate_content_hash(
            company="Mistral AI",
            title=(
                "Mistral launches enterprise "
                "AI platform"
            ),
            content=content,
        )
    )

    article_id = db.save_article(
        company="Mistral AI",
        title=(
            "Mistral launches enterprise "
            "AI platform"
        ),
        url=(
            "https://mistral.ai/"
            "news/example"
        ),
        source="mistral.ai",
        published_at="2026-09-19",
        content=content,
        content_hash=content_hash,
    )

    assert article_id is not None

    return article_id


def create_signal() -> BusinessSignal:

    return BusinessSignal(
        company="Mistral AI",

        signal_type=(
            SignalType.PRODUCT_LAUNCH
        ),

        summary=(
            "Mistral launched a new "
            "enterprise AI platform."
        ),

        evidence=(
            "The official announcement "
            "directly describes the launch."
        ),

        business_relevance=92,

        confidence=0.95,

        is_relevant=True,
    )


def create_evidence() -> EvidenceAssessment:

    return EvidenceAssessment(
        company="Mistral AI",

        source_quality=(
            EvidenceQuality.HIGH
        ),

        evidence_quality_score=18,

        claim_supported=True,

        evidence_clear=True,

        reason=(
            "The official article directly "
            "supports the product launch."
        ),

        confidence=0.94,
    )


# ============================================================
# STRONG OPPORTUNITY
# ============================================================


def test_strong_opportunity_recommended(
    tmp_path,
):

    db = Database(
        database_path=(
            tmp_path
            / "recommendation.db"
        )
    )

    article_id = create_test_article(
        db
    )

    agent = RecommendationAgent(
        database=db,
        llm=FakeOpportunityLLM(),
    )

    result = agent.evaluate(
        article_id=article_id,
        signal=create_signal(),
        evidence=create_evidence(),
    )

    assert result is not None

    # --------------------------------------------------------
    # FINAL DECISION
    # --------------------------------------------------------

    assert (
        result.should_recommend
        is True
    )

    # --------------------------------------------------------
    # EVENT MATCH
    # --------------------------------------------------------

    assert (
        result.recommended_event
        == "RAISE"
    )

    assert (
        result.event_fit_reason
        != ""
    )

    assert (
        "RAISE"
        in result.event_fit_reason
    )

    # --------------------------------------------------------
    # DETERMINISTIC SCORING
    # --------------------------------------------------------

    assert result.total_score == 92

    # Publication date is recent,
    # so Python recalculates recency as 15.

    assert result.recency_score == 15

    # Conservative confidence:
    #
    # LLM       = 0.92
    # evidence  = 0.94
    # signal    = 0.95
    #
    # final = minimum = 0.92

    assert result.confidence == 0.92

    # --------------------------------------------------------
    # SOURCE
    # --------------------------------------------------------

    assert result.sources == [
        "https://mistral.ai/news/example"
    ]

    # --------------------------------------------------------
    # DATABASE
    # --------------------------------------------------------

    recommendations = (
        db.get_recommendations_by_company(
            "Mistral AI"
        )
    )

    assert len(recommendations) == 1

    stored = recommendations[0]

    assert (
        stored["recommended_event"]
        == "RAISE"
    )

    assert (
        stored["event_fit_reason"]
        != ""
    )


# ============================================================
# DUPLICATE RECOMMENDATION
# ============================================================


def test_duplicate_recommendation_not_saved_twice(
    tmp_path,
):

    db = Database(
        database_path=(
            tmp_path
            / "duplicate_recommendation.db"
        )
    )

    article_id = create_test_article(
        db
    )

    agent = RecommendationAgent(
        database=db,
        llm=FakeOpportunityLLM(),
    )

    first_result = agent.evaluate(
        article_id=article_id,
        signal=create_signal(),
        evidence=create_evidence(),
    )

    second_result = agent.evaluate(
        article_id=article_id,
        signal=create_signal(),
        evidence=create_evidence(),
    )

    assert (
        first_result.should_recommend
        is True
    )

    assert (
        second_result.should_recommend
        is True
    )

    assert (
        first_result.recommended_event
        == "RAISE"
    )

    assert (
        second_result.recommended_event
        == "RAISE"
    )

    recommendations = (
        db.get_recommendations_by_company(
            "Mistral AI"
        )
    )

    # Only one persistent alert.

    assert len(recommendations) == 1


# ============================================================
# UNSUPPORTED EVIDENCE
# ============================================================


def test_unsupported_evidence_not_recommended(
    tmp_path,
):

    db = Database(
        database_path=(
            tmp_path
            / "unsupported.db"
        )
    )

    article_id = create_test_article(
        db
    )

    weak_evidence = EvidenceAssessment(
        company="Mistral AI",

        source_quality=(
            EvidenceQuality.LOW
        ),

        evidence_quality_score=4,

        claim_supported=False,

        evidence_clear=False,

        reason=(
            "The source does not clearly "
            "support the claimed event."
        ),

        confidence=0.35,
    )

    agent = RecommendationAgent(
        database=db,
        llm=FakeOpportunityLLM(),
    )

    result = agent.evaluate(
        article_id=article_id,
        signal=create_signal(),
        evidence=weak_evidence,
    )

    assert result is not None

    assert (
        result.should_recommend
        is False
    )

    # Without verified evidence, no event
    # sponsorship recommendation is made.

    assert (
        result.recommended_event
        == "NONE"
    )

    assert (
        result.event_fit_score
        == 0
    )

    recommendations = (
        db.get_recommendations_by_company(
            "Mistral AI"
        )
    )

    assert len(recommendations) == 0


# ============================================================
# NO EVENT FIT
# ============================================================


def test_none_event_blocks_recommendation(
    tmp_path,
):

    db = Database(
        database_path=(
            tmp_path
            / "no_event_fit.db"
        )
    )

    article_id = create_test_article(
        db
    )

    agent = RecommendationAgent(
        database=db,
        llm=FakeNoEventFitLLM(),
    )

    result = agent.evaluate(
        article_id=article_id,
        signal=create_signal(),
        evidence=create_evidence(),
    )

    assert result is not None

    # The numerical score can be high,
    # but NONE must prevent the alert.

    assert (
        result.total_score
        >= 75
    )

    assert (
        result.recommended_event
        == "NONE"
    )

    assert (
        result.should_recommend
        is False
    )

    recommendations = (
        db.get_recommendations_by_company(
            "Mistral AI"
        )
    )

    assert len(recommendations) == 0


# ============================================================
# LOW-QUALITY SOURCE
# ============================================================


def test_low_quality_source_blocks_recommendation(
    tmp_path,
):
    """
    Even when the claim is supported and the evidence
    appears clear, a LOW-quality source must never
    trigger a sponsorship recommendation.
    """

    db = Database(
        database_path=(
            tmp_path
            / "low_quality_source.db"
        )
    )

    article_id = create_test_article(
        db
    )

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # The evidence looks strong numerically:
    #
    # claim_supported = True
    # evidence_clear  = True
    # evidence score  = 18/20
    #
    # But source quality is LOW.
    #
    # The deterministic rule must therefore block
    # the sponsorship alert.
    # --------------------------------------------------------

    low_quality_evidence = (
        EvidenceAssessment(
            company="Mistral AI",

            source_quality=(
                EvidenceQuality.LOW
            ),

            evidence_quality_score=18,

            claim_supported=True,

            evidence_clear=True,

            reason=(
                "The article contains a clear claim, "
                "but the source itself is considered "
                "low quality."
            ),

            confidence=0.80,
        )
    )

    agent = RecommendationAgent(
        database=db,
        llm=FakeOpportunityLLM(),
    )

    result = agent.evaluate(
        article_id=article_id,
        signal=create_signal(),
        evidence=low_quality_evidence,
    )

    assert result is not None

    # --------------------------------------------------------
    # NO SPONSORSHIP ALERT
    # --------------------------------------------------------

    assert (
        result.should_recommend
        is False
    )

    # --------------------------------------------------------
    # NO EVENT SHOULD BE RECOMMENDED
    # --------------------------------------------------------

    assert (
        result.recommended_event
        == "NONE"
    )

    assert (
        result.event_fit_score
        == 0
    )

    # --------------------------------------------------------
    # ORIGINAL EVIDENCE SCORE IS PRESERVED
    # --------------------------------------------------------

    assert (
        result.evidence_quality_score
        == 18
    )

    # --------------------------------------------------------
    # EXPLANATION SHOULD MENTION LOW SOURCE QUALITY
    # --------------------------------------------------------

    assert (
        "LOW"
        in result.reason
    )

    # --------------------------------------------------------
    # NO RECOMMENDATION MUST BE SAVED
    # --------------------------------------------------------

    recommendations = (
        db.get_recommendations_by_company(
            "Mistral AI"
        )
    )

    assert len(recommendations) == 0