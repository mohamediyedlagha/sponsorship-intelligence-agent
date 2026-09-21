from typing import Protocol

from src.config import SEMANTIC_DUPLICATE_THRESHOLD
from src.memory.database import Database


class EmbeddingProvider(Protocol):
    """
    Interface expected by the deduplication service.

    This avoids loading sentence-transformers during
    unit tests when a fake embedding service is used.
    """

    def similarity(
        self,
        text_a: str,
        text_b: str,
    ) -> float:
        ...


class DeduplicationService:
    """
    Detect semantic duplicates among previously
    stored articles for the same company.
    """

    def __init__(
        self,
        database: Database,
        embedding_service: EmbeddingProvider,
        threshold: float = SEMANTIC_DUPLICATE_THRESHOLD,
    ) -> None:

        self.database = database
        self.embedding_service = embedding_service
        self.threshold = threshold

    def is_semantic_duplicate(
        self,
        company: str,
        title: str,
        content: str,
    ) -> tuple[bool, float, dict | None]:

        previous_articles = (
            self.database.get_articles_by_company(
                company
            )
        )

        if not previous_articles:
            return False, 0.0, None

        new_text = self._build_comparison_text(
            title=title,
            content=content,
        )

        highest_similarity = 0.0
        matching_article = None

        for article in previous_articles:

            previous_text = (
                self._build_comparison_text(
                    title=article["title"],
                    content=article["content"],
                )
            )

            similarity = (
                self.embedding_service.similarity(
                    new_text,
                    previous_text,
                )
            )

            if similarity > highest_similarity:

                highest_similarity = similarity
                matching_article = article

        is_duplicate = (
            highest_similarity
            >= self.threshold
        )

        return (
            is_duplicate,
            highest_similarity,
            matching_article,
        )

    @staticmethod
    def _build_comparison_text(
        title: str,
        content: str,
    ) -> str:

        return (
            f"Title: {title}\n\n"
            f"Content: {content}"
        )