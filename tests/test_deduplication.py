from src.memory.database import Database
from src.memory.deduplication import (
    DeduplicationService,
)
from src.utils.hashing import (
    generate_content_hash,
)


class FakeEmbeddingService:
    """
    Fake embedding service used for deterministic tests.

    It returns a high similarity score when both texts
    refer to the same enterprise AI platform event,
    and a low score otherwise.
    """

    def similarity(
        self,
        text_a: str,
        text_b: str,
    ) -> float:

        text_a = text_a.lower()
        text_b = text_b.lower()

        same_enterprise_event = (
            "enterprise ai" in text_a
            and
            "enterprise ai" in text_b
        )

        if same_enterprise_event:
            return 0.94

        return 0.20


def test_semantic_duplicate(
    tmp_path,
):
    """
    Two differently worded articles about the same
    business event should be detected as duplicates.
    """

    database_path = (
        tmp_path
        / "dedup_test.db"
    )

    db = Database(
        database_path=database_path
    )

    # -----------------------------------------
    # Existing article already stored
    # -----------------------------------------

    existing_content = (
        "Mistral AI announced an enterprise AI "
        "platform for business customers."
    )

    existing_hash = (
        generate_content_hash(
            company="Mistral AI",
            title=(
                "Mistral launches "
                "enterprise AI platform"
            ),
            content=existing_content,
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
            "original"
        ),
        source="example.com",
        content=existing_content,
        content_hash=existing_hash,
    )

    assert article_id is not None

    # -----------------------------------------
    # Deduplication service
    # -----------------------------------------

    service = DeduplicationService(
        database=db,
        embedding_service=(
            FakeEmbeddingService()
        ),
        threshold=0.88,
    )

    # -----------------------------------------
    # New article with different wording,
    # but same underlying event
    # -----------------------------------------

    (
        is_duplicate,
        similarity,
        matching_article,
    ) = service.is_semantic_duplicate(
        company="Mistral AI",
        title=(
            "Mistral unveils new "
            "enterprise AI solution"
        ),
        content=(
            "The company introduced a new "
            "enterprise AI platform "
            "for companies."
        ),
    )

    # -----------------------------------------
    # Assertions
    # -----------------------------------------

    assert is_duplicate is True

    assert similarity == 0.94

    assert matching_article is not None

    assert (
        matching_article["company"]
        == "Mistral AI"
    )


def test_not_semantic_duplicate(
    tmp_path,
):
    """
    A genuinely different business event should
    not be considered a semantic duplicate.
    """

    database_path = (
        tmp_path
        / "not_duplicate.db"
    )

    db = Database(
        database_path=database_path
    )

    # -----------------------------------------
    # Existing article
    # -----------------------------------------

    existing_content = (
        "Mistral AI announced an "
        "enterprise AI platform."
    )

    existing_hash = (
        generate_content_hash(
            company="Mistral AI",
            title=(
                "Enterprise AI Platform"
            ),
            content=existing_content,
        )
    )

    article_id = db.save_article(
        company="Mistral AI",
        title="Enterprise AI Platform",
        url="https://example.com/a",
        source="example.com",
        content=existing_content,
        content_hash=existing_hash,
    )

    assert article_id is not None

    # -----------------------------------------
    # Deduplication service
    # -----------------------------------------

    service = DeduplicationService(
        database=db,
        embedding_service=(
            FakeEmbeddingService()
        ),
        threshold=0.88,
    )

    # -----------------------------------------
    # Different event
    # -----------------------------------------

    (
        is_duplicate,
        similarity,
        matching_article,
    ) = service.is_semantic_duplicate(
        company="Mistral AI",
        title=(
            "Mistral opens new office "
            "in Berlin"
        ),
        content=(
            "The company expanded its "
            "operations into Germany."
        ),
    )

    # -----------------------------------------
    # Assertions
    # -----------------------------------------

    assert is_duplicate is False

    assert similarity == 0.20

    assert matching_article is not None


def test_empty_memory_is_not_duplicate(
    tmp_path,
):
    """
    If the database contains no previous article
    for the company, the content cannot be a duplicate.
    """

    database_path = (
        tmp_path
        / "empty_memory.db"
    )

    db = Database(
        database_path=database_path
    )

    service = DeduplicationService(
        database=db,
        embedding_service=(
            FakeEmbeddingService()
        ),
        threshold=0.88,
    )

    (
        is_duplicate,
        similarity,
        matching_article,
    ) = service.is_semantic_duplicate(
        company="ElevenLabs",
        title=(
            "ElevenLabs launches "
            "new voice platform"
        ),
        content=(
            "ElevenLabs announced a "
            "new voice AI platform."
        ),
    )

    assert is_duplicate is False

    assert similarity == 0.0

    assert matching_article is None