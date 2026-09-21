from sentence_transformers import SentenceTransformer


class EmbeddingService:
    """
    Local embedding service used for semantic
    similarity and duplicate detection.
    """

    def __init__(
        self,
        model_name: str = (
            "sentence-transformers/"
            "all-MiniLM-L6-v2"
        ),
    ) -> None:

        self.model = SentenceTransformer(
            model_name
        )

    def encode(
        self,
        text: str,
    ):
        """
        Generate a normalized embedding.
        """

        return self.model.encode(
            text,
            normalize_embeddings=True,
        )

    def similarity(
        self,
        text_a: str,
        text_b: str,
    ) -> float:
        """
        Calculate cosine similarity.

        Since embeddings are normalized,
        dot product = cosine similarity.
        """

        embedding_a = self.encode(
            text_a
        )

        embedding_b = self.encode(
            text_b
        )

        similarity_score = (
            embedding_a @ embedding_b
        )

        return float(
            similarity_score
        )