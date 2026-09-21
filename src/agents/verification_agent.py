from pathlib import Path

from src.config import PROMPTS_DIR
from src.memory.database import Database
from src.models.evidence import EvidenceAssessment
from src.models.signal import BusinessSignal
from src.services.ollama_service import OllamaService


class VerificationAgent:
    """
    Verifies whether a business signal extracted from
    an article is sufficiently supported by evidence.
    """

    def __init__(
        self,
        database: Database,
        llm: OllamaService,
        prompt_path: str | Path | None = None,
    ) -> None:

        self.database = database
        self.llm = llm

        if prompt_path is None:
            self.prompt_path = (
                PROMPTS_DIR
                / "evidence_verification.txt"
            )
        else:
            self.prompt_path = Path(
                prompt_path
            )

        self.prompt_template = (
            self._load_prompt()
        )

    # =========================================================
    # PROMPT LOADING
    # =========================================================

    def _load_prompt(self) -> str:
        """
        Load the evidence-verification prompt.
        """

        if not self.prompt_path.exists():

            raise FileNotFoundError(
                f"Prompt not found: "
                f"{self.prompt_path}"
            )

        return self.prompt_path.read_text(
            encoding="utf-8"
        )

    # =========================================================
    # EVIDENCE VERIFICATION
    # =========================================================

    def verify(
        self,
        article_id: int,
        signal: BusinessSignal,
    ) -> EvidenceAssessment | None:
        """
        Verify the evidence supporting a detected
        business signal.

        Returns:
            EvidenceAssessment if the article exists.

            None if the article cannot be found.
        """

        article = (
            self.database.get_article_by_id(
                article_id
            )
        )

        if article is None:

            print(
                f"[VerificationAgent] "
                f"Article #{article_id} "
                f"not found."
            )

            return None

        prompt = self._build_prompt(
            article=article,
            signal=signal,
        )

        print(
            f"\n[VerificationAgent] "
            f"Checking evidence for "
            f"article #{article_id}"
        )

        print(
            f"[VerificationAgent] "
            f"{article['title'][:80]}"
        )

        assessment = (
            self.llm.structured_chat(
                prompt=prompt,
                schema=EvidenceAssessment,
                system_prompt=(
                    "You are a conservative "
                    "evidence verification analyst. "
                    "Use only the provided article. "
                    "Do not invent facts. "
                    "Reduce confidence when evidence "
                    "is incomplete or unclear."
                ),
            )
        )

        # We trust the company name stored in
        # our database rather than the LLM output.
        assessment = assessment.model_copy(
            update={
                "company": article["company"]
            }
        )

        self._print_result(
            assessment
        )

        return assessment

    # =========================================================
    # PROMPT CONSTRUCTION
    # =========================================================

    def _build_prompt(
        self,
        article: dict,
        signal: BusinessSignal,
    ) -> str:
        """
        Build the verification prompt from
        the article and extracted signal.
        """

        return self.prompt_template.format(
            company=article["company"],
            source=(
                article["source"]
                or "Unknown source"
            ),
            title=article["title"],
            url=article["url"],
            content=article["content"],
            signal_type=(
                signal.signal_type.value
            ),
            summary=signal.summary,
            evidence=signal.evidence,
        )

    # =========================================================
    # TERMINAL OUTPUT
    # =========================================================

    @staticmethod
    def _print_result(
        assessment: EvidenceAssessment,
    ) -> None:
        """
        Print a concise verification summary.
        """

        print(
            f"[VerificationAgent] "
            f"Source quality: "
            f"{assessment.source_quality.value}"
        )

        print(
            f"[VerificationAgent] "
            f"Evidence score: "
            f"{assessment.evidence_quality_score}/20"
        )

        print(
            f"[VerificationAgent] "
            f"Claim supported: "
            f"{assessment.claim_supported}"
        )

        print(
            f"[VerificationAgent] "
            f"Evidence clear: "
            f"{assessment.evidence_clear}"
        )

        print(
            f"[VerificationAgent] "
            f"Confidence: "
            f"{assessment.confidence:.2f}"
        )