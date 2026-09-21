from src.agents.signal_agent import SignalAgent
from src.memory.database import Database
from src.models.signal import (
    BusinessSignal,
    SignalType,
)
from src.utils.hashing import (
    generate_content_hash,
)


class FakeLLM:
    """
    Fake deterministic LLM used for testing.
    """

    def structured_chat(
        self,
        prompt: str,
        schema,
        system_prompt: str | None = None,
    ):
        return BusinessSignal(
            company="Mistral AI",
            signal_type=(
                SignalType.PRODUCT_LAUNCH
            ),
            summary=(
                "Mistral AI launched a new "
                "enterprise AI product."
            ),
            evidence=(
                "The company announced a new "
                "enterprise platform for "
                "business customers."
            ),
            business_relevance=90,
            confidence=0.95,
            is_relevant=True,
        )


class FakeGenericLLM:
    """
    Fake LLM that intentionally marks generic
    company information as relevant.

    The deterministic SignalAgent filter should
    override this decision.
    """

    def structured_chat(
        self,
        prompt: str,
        schema,
        system_prompt: str | None = None,
    ):
        return BusinessSignal(
            company="Mistral AI",
            signal_type=(
                SignalType.FUNDING
            ),
            summary=(
                "Historical funding information."
            ),
            evidence=(
                "Funding information is listed."
            ),
            business_relevance=100,
            confidence=1.0,
            is_relevant=True,
        )


# ============================================================
# REAL BUSINESS EVENT
# ============================================================


def test_signal_agent(
    tmp_path,
):
    """
    A specific business-event article should
    remain relevant and should be persisted.
    """

    # --------------------------------------------------------
    # TEMPORARY DATABASE
    # --------------------------------------------------------

    database_path = (
        tmp_path
        / "signal_test.db"
    )

    db = Database(
        database_path=database_path
    )

    # --------------------------------------------------------
    # SPECIFIC BUSINESS ARTICLE
    # --------------------------------------------------------

    content = (
        "Mistral AI announced a new "
        "enterprise AI platform designed "
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
            "https://example.com/"
            "mistral-enterprise"
        ),
        source="example.com",
        content=content,
        content_hash=content_hash,
    )

    assert article_id is not None

    # --------------------------------------------------------
    # SIGNAL ANALYSIS
    # --------------------------------------------------------

    agent = SignalAgent(
        database=db,
        llm=FakeLLM(),
    )

    result = agent.analyze_article(
        article_id=article_id
    )

    # --------------------------------------------------------
    # ASSERTIONS
    # --------------------------------------------------------

    assert result is not None

    assert (
        result.signal_type
        == SignalType.PRODUCT_LAUNCH
    )

    assert (
        result.is_relevant
        is True
    )

    assert (
        result.business_relevance
        == 90
    )

    assert (
        result.confidence
        == 0.95
    )

    # --------------------------------------------------------
    # PERSISTENT MEMORY
    # --------------------------------------------------------

    signals = (
        db.get_signals_by_company(
            "Mistral AI"
        )
    )

    assert len(signals) == 1

    assert (
        signals[0]["signal_type"]
        == "PRODUCT_LAUNCH"
    )


# ============================================================
# GENERIC TITLE
# ============================================================


def test_generic_profile_is_not_relevant(
    tmp_path,
):
    """
    A generic company-profile page must be rejected
    even if the LLM considers it highly relevant.
    """

    database_path = (
        tmp_path
        / "generic_profile.db"
    )

    db = Database(
        database_path=database_path
    )

    content = (
        "General company funding information "
        "and historical investor information."
    )

    content_hash = (
        generate_content_hash(
            company="Mistral AI",
            title=(
                "Mistral AI company information, "
                "funding & investors"
            ),
            content=content,
        )
    )

    article_id = db.save_article(
        company="Mistral AI",
        title=(
            "Mistral AI company information, "
            "funding & investors"
        ),
        url=(
            "https://example.com/profile"
        ),
        source="example.com",
        content=content,
        content_hash=content_hash,
    )

    assert article_id is not None

    agent = SignalAgent(
        database=db,
        llm=FakeGenericLLM(),
    )

    result = agent.analyze_article(
        article_id=article_id
    )

    # --------------------------------------------------------
    # DETERMINISTIC GENERIC-TITLE FILTER
    # --------------------------------------------------------

    assert result is not None

    assert (
        result.is_relevant
        is False
    )

    # --------------------------------------------------------
    # GENERIC SIGNAL MUST NOT BE PERSISTED
    # --------------------------------------------------------

    signals = (
        db.get_signals_by_company(
            "Mistral AI"
        )
    )

    assert len(signals) == 0


# ============================================================
# COMPANY HOMEPAGE
# ============================================================


def test_company_homepage_is_not_relevant(
    tmp_path,
):
    """
    A company homepage must not generate a new
    business signal merely because it contains
    historical funding or product information.

    The title intentionally does not contain one
    of the generic title patterns. The URL itself
    must trigger the deterministic homepage filter.
    """

    database_path = (
        tmp_path
        / "homepage_filter.db"
    )

    db = Database(
        database_path=database_path
    )

    content = (
        "Mistral AI develops frontier AI models, "
        "enterprise solutions and AI infrastructure. "
        "The page also mentions previous funding."
    )

    title = (
        "Mistral: Frontier AI LLMs, "
        "assistants, agents, services"
    )

    content_hash = (
        generate_content_hash(
            company="Mistral AI",
            title=title,
            content=content,
        )
    )

    article_id = db.save_article(
        company="Mistral AI",
        title=title,

        # Root URL: this is the important part
        # of this test.
        url="https://mistral.ai/",

        source="mistral.ai",
        content=content,
        content_hash=content_hash,
    )

    assert article_id is not None

    # FakeGenericLLM intentionally returns:
    #
    # relevance = 100
    # confidence = 1.0
    # is_relevant = True
    #
    # Python must override it because this is
    # a company homepage.

    agent = SignalAgent(
        database=db,
        llm=FakeGenericLLM(),
    )

    result = agent.analyze_article(
        article_id=article_id
    )

    assert result is not None

    assert (
        result.signal_type
        == SignalType.FUNDING
    )

    assert (
        result.business_relevance
        == 100
    )

    # --------------------------------------------------------
    # IMPORTANT ASSERTION
    # --------------------------------------------------------

    assert (
        result.is_relevant
        is False
    )

    # --------------------------------------------------------
    # HOMEPAGE SIGNAL MUST NOT BE SAVED
    # --------------------------------------------------------

    signals = (
        db.get_signals_by_company(
            "Mistral AI"
        )
    )

    assert len(signals) == 0