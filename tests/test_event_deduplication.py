from src.memory.database import (
    Database,
)
from src.memory.event_deduplication import (
    EventDeduplicationService,
)


class FakeEmbeddingService:
    """
    Deterministic fake embedding service.

    It intentionally gives high similarity to
    funding articles, even when the funding rounds
    are different.

    This allows us to verify that deterministic
    event facts can override semantic similarity.
    """

    def similarity(
        self,
        text_a: str,
        text_b: str,
    ) -> float:

        text_a = text_a.lower()
        text_b = text_b.lower()

        # ----------------------------------------------------
        # PRODUCT LAUNCH
        # ----------------------------------------------------

        if (
            "mistral 3" in text_a
            and "mistral 3" in text_b
        ):

            return 0.90

        # ----------------------------------------------------
        # FUNDING
        # ----------------------------------------------------

        funding_terms = (
            "$",
            "€",
            "£",
            "funding",
            "raised",
            "raises",
            "financing",
            "series",
            "valuation",
        )

        funding_a = any(
            term in text_a
            for term in funding_terms
        )

        funding_b = any(
            term in text_b
            for term in funding_terms
        )

        if (
            funding_a
            and funding_b
        ):

            return 0.94

        return 0.20


# ============================================================
# TEST 1
# SAME FUNDING EVENT
# SAME AMOUNT + SAME ROUND
# ============================================================


def test_duplicate_business_event(
    tmp_path,
):
    """
    Two descriptions of the same $500M Series D
    event should be considered duplicates.
    """

    db = Database(
        database_path=(
            tmp_path
            / "events.db"
        )
    )

    db.save_recommendation(
        company="ElevenLabs",
        signal_type="FUNDING",
        event_summary=(
            "ElevenLabs raised $500M "
            "Series D at an $11B valuation."
        ),
        total_score=95,
        confidence=0.95,
        reason="Funding event.",
        next_step="Contact partnerships.",
        recommendation_hash="hash-one",
    )

    service = EventDeduplicationService(
        database=db,
        embedding_service=(
            FakeEmbeddingService()
        ),
        threshold=0.84,
    )

    (
        is_duplicate,
        similarity,
        match,
    ) = service.is_duplicate_event(
        company="ElevenLabs",
        signal_type="FUNDING",
        event_summary=(
            "ElevenLabs closes "
            "$500M Series D financing "
            "at an $11B valuation."
        ),
    )

    assert (
        is_duplicate
        is True
    )

    assert similarity == 0.94

    assert match is not None


# ============================================================
# TEST 2
# DIFFERENT FUNDING EVENTS
# $180M SERIES C VS $500M SERIES D
# ============================================================


def test_different_funding_rounds_are_not_duplicates(
    tmp_path,
):
    """
    $180M Series C and $500M Series D are
    different business events.

    Even if embeddings give them a high semantic
    similarity, deterministic event facts must
    prevent a false duplicate.
    """

    db = Database(
        database_path=(
            tmp_path
            / "different_rounds.db"
        )
    )

    db.save_recommendation(
        company="ElevenLabs",
        signal_type="FUNDING",
        event_summary=(
            "ElevenLabs raised $180M "
            "Series C at a $3.3B valuation."
        ),
        total_score=80,
        confidence=0.95,
        reason="Series C funding event.",
        next_step="Contact partnerships.",
        recommendation_hash="series-c",
    )

    service = EventDeduplicationService(
        database=db,
        embedding_service=(
            FakeEmbeddingService()
        ),
        threshold=0.84,
    )

    (
        is_duplicate,
        similarity,
        match,
    ) = service.is_duplicate_event(
        company="ElevenLabs",
        signal_type="FUNDING",
        event_summary=(
            "ElevenLabs raised $500M "
            "Series D at an $11B valuation."
        ),
    )

    # Fake embeddings deliberately return 0.94.
    #
    # The funding facts must override
    # semantic similarity.

    assert (
        is_duplicate
        is False
    )

    assert match is None


# ============================================================
# TEST 3
# COMPLETELY DIFFERENT BUSINESS EVENT
# ============================================================


def test_different_business_event(
    tmp_path,
):
    """
    A geographically focused expansion event
    should not be considered the same as a
    funding event.
    """

    db = Database(
        database_path=(
            tmp_path
            / "events2.db"
        )
    )

    db.save_recommendation(
        company="ElevenLabs",
        signal_type="FUNDING",
        event_summary=(
            "ElevenLabs raised $500M "
            "Series D at an $11B valuation."
        ),
        total_score=95,
        confidence=0.95,
        reason="Funding event.",
        next_step="Contact partnerships.",
        recommendation_hash="hash-one",
    )

    service = EventDeduplicationService(
        database=db,
        embedding_service=(
            FakeEmbeddingService()
        ),
        threshold=0.84,
    )

    (
        is_duplicate,
        similarity,
        _,
    ) = service.is_duplicate_event(
        company="ElevenLabs",
        signal_type="FUNDING",
        event_summary=(
            "ElevenLabs opens a "
            "new office in Germany."
        ),
    )

    assert (
        is_duplicate
        is False
    )

    assert similarity == 0.20


# ============================================================
# TEST 4
# SAME PRODUCT LAUNCH
# ============================================================


def test_duplicate_product_launch(
    tmp_path,
):
    """
    Two differently worded summaries describing
    the same Mistral 3 product launch should be
    treated as the same underlying event.
    """

    db = Database(
        database_path=(
            tmp_path
            / "product_events.db"
        )
    )

    db.save_recommendation(
        company="Mistral AI",
        signal_type="PRODUCT_LAUNCH",
        event_summary=(
            "Mistral AI launches Mistral 3 "
            "open-source model family."
        ),
        total_score=82,
        confidence=0.95,
        reason="New AI model launch.",
        next_step="Contact partnerships.",
        recommendation_hash=(
            "mistral-3-launch"
        ),
    )

    service = EventDeduplicationService(
        database=db,
        embedding_service=(
            FakeEmbeddingService()
        ),
        threshold=0.84,
    )

    (
        is_duplicate,
        similarity,
        match,
    ) = service.is_duplicate_event(
        company="Mistral AI",
        signal_type="PRODUCT_LAUNCH",
        event_summary=(
            "Mistral introduces Mistral 3, "
            "a family of open-source models."
        ),
    )

    assert (
        is_duplicate
        is True
    )

    assert similarity == 0.90

    assert match is not None


# ============================================================
# TEST 5
# SAME $500M FUNDING EVENT
# ONE DESCRIPTION OMITS SERIES D
# ============================================================


def test_same_funding_amount_without_round_is_duplicate(
    tmp_path,
):
    """
    This reproduces the real ElevenLabs case.

    Previous alert:

        $500M Series D at $11B valuation

    New article:

        $500M from Sequoia at $11B valuation

    The second description does not explicitly
    mention Series D, but the shared $500M funding
    amount plus semantic similarity should identify
    the same underlying event.
    """

    db = Database(
        database_path=(
            tmp_path
            / "same_amount_missing_round.db"
        )
    )

    db.save_recommendation(
        company="ElevenLabs",
        signal_type="FUNDING",
        event_summary=(
            "ElevenLabs completed a "
            "$500M Series D funding round "
            "at an $11B valuation."
        ),
        total_score=83,
        confidence=0.95,
        reason=(
            "Major funding event."
        ),
        next_step=(
            "Contact partnerships."
        ),
        recommendation_hash=(
            "elevenlabs-500m-series-d"
        ),
    )

    service = EventDeduplicationService(
        database=db,
        embedding_service=(
            FakeEmbeddingService()
        ),
        threshold=0.84,
    )

    (
        is_duplicate,
        similarity,
        match,
    ) = service.is_duplicate_event(
        company="ElevenLabs",
        signal_type="FUNDING",
        event_summary=(
            "ElevenLabs raised $500M "
            "from Sequoia at an "
            "$11B valuation."
        ),
    )

    # --------------------------------------------------------
    # IMPORTANT
    # --------------------------------------------------------
    #
    # Same funding amount:
    #
    # $500M == $500M
    #
    # Semantic similarity:
    #
    # 0.94 >= funding-specific threshold
    #
    # Therefore this must be the same alert.
    # --------------------------------------------------------

    assert (
        is_duplicate
        is True
    )

    assert similarity == 0.94

    assert match is not None

    assert (
        "$500M"
        in match["event_summary"]
    )


# ============================================================
# TEST 6
# SAME VALUATION BUT DIFFERENT FUNDING AMOUNTS
# ============================================================


def test_same_valuation_different_funding_not_duplicate(
    tmp_path,
):
    """
    Company valuation must NOT be treated as the
    funding amount.

    Example:

        $180M funding at $11B valuation

    and

        $500M funding at $11B valuation

    share the same valuation but represent
    different funding events.
    """

    db = Database(
        database_path=(
            tmp_path
            / "valuation_not_funding.db"
        )
    )

    db.save_recommendation(
        company="ElevenLabs",
        signal_type="FUNDING",
        event_summary=(
            "ElevenLabs raised $180M "
            "Series C at an $11B valuation."
        ),
        total_score=80,
        confidence=0.95,
        reason=(
            "Series C funding."
        ),
        next_step=(
            "Contact partnerships."
        ),
        recommendation_hash=(
            "180m-round"
        ),
    )

    service = EventDeduplicationService(
        database=db,
        embedding_service=(
            FakeEmbeddingService()
        ),
        threshold=0.84,
    )

    (
        is_duplicate,
        similarity,
        match,
    ) = service.is_duplicate_event(
        company="ElevenLabs",
        signal_type="FUNDING",
        event_summary=(
            "ElevenLabs raised $500M "
            "Series D at an $11B valuation."
        ),
    )

    # --------------------------------------------------------
    # The $11B value is only the valuation.
    #
    # Funding amounts are:
    #
    # $180M vs $500M
    #
    # Therefore these must remain distinct.
    # --------------------------------------------------------

    assert (
        is_duplicate
        is False
    )

    assert match is None