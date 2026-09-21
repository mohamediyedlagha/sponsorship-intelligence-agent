from pathlib import Path
from urllib.parse import urlparse

from src.config import (
    PROMPTS_DIR,
    SIGNAL_CONFIDENCE_THRESHOLD,
    SIGNAL_RELEVANCE_THRESHOLD,
)
from src.memory.database import Database
from src.models.signal import BusinessSignal
from src.services.ollama_service import (
    OllamaService,
)


class SignalAgent:
    """
    Detect meaningful business signals
    from newly discovered articles.
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
                / "signal_extraction.txt"
            )

        else:

            self.prompt_path = Path(
                prompt_path
            )

        self.prompt_template = (
            self._load_prompt()
        )

    # ========================================================
    # PROMPT
    # ========================================================

    def _load_prompt(
        self,
    ) -> str:

        if not self.prompt_path.exists():

            raise FileNotFoundError(
                f"Prompt not found: "
                f"{self.prompt_path}"
            )

        return self.prompt_path.read_text(
            encoding="utf-8"
        )

    # ========================================================
    # ANALYSIS
    # ========================================================

    def analyze_article(
        self,
        article_id: int,
    ) -> BusinessSignal | None:

        article = (
            self.database
            .get_article_by_id(
                article_id
            )
        )

        if article is None:

            print(
                f"[SignalAgent] "
                f"Article {article_id} "
                f"does not exist."
            )

            return None

        prompt = (
            self._build_prompt(
                article
            )
        )

        print(
            f"\n[SignalAgent] "
            f"Analyzing article "
            f"#{article_id}"
        )

        print(
            f"[SignalAgent] "
            f"{article['title'][:80]}"
        )

        signal = (
            self.llm.structured_chat(
                prompt=prompt,
                schema=BusinessSignal,
                system_prompt=(
                    "You are a conservative "
                    "business intelligence analyst. "
                    "Use only supplied evidence. "
                    "Never invent facts. "
                    "Confidence MUST be between "
                    "0.0 and 1.0."
                ),
            )
        )

        # ====================================================
        # GENERIC PAGE FILTER
        # ====================================================

        generic_profile = (
            self._looks_like_generic_profile(
                title=article["title"],
                url=article["url"],
            )
        )

        # ====================================================
        # DETERMINISTIC RELEVANCE GATE
        # ====================================================

        final_is_relevant = (
            signal.is_relevant
            and signal.business_relevance
            >= SIGNAL_RELEVANCE_THRESHOLD
            and signal.confidence
            >= SIGNAL_CONFIDENCE_THRESHOLD
            and not generic_profile
        )

        signal = signal.model_copy(
            update={
                "company": (
                    article["company"]
                ),
                "is_relevant": (
                    final_is_relevant
                ),
            }
        )

        if generic_profile:

            print(
                "[SignalAgent] "
                "Generic company/profile page detected."
            )

        self._print_signal(
            signal
        )

        # ====================================================
        # SAVE ONLY RELEVANT SIGNALS
        # ====================================================

        if signal.is_relevant:

            self.database.save_signal(
                article_id=article_id,
                company=signal.company,
                signal_type=(
                    signal.signal_type.value
                ),
                summary=signal.summary,
                business_relevance=(
                    signal.business_relevance
                ),
                confidence=(
                    signal.confidence
                ),
            )

        return signal

    # ========================================================
    # GENERIC PAGE DETECTION
    # ========================================================

    @staticmethod
    def _looks_like_generic_profile(
        title: str,
        url: str = "",
    ) -> bool:
        """
        Detect pages that describe a company in general
        rather than reporting a specific new business event.

        The deterministic filter checks both:

        1. generic patterns in the page title;
        2. root/homepage URLs.

        This prevents a homepage containing historical
        funding, product or partnership information from
        being interpreted as a new business event.
        """

        normalized_title = (
            title
            .lower()
            .strip()
        )

        generic_patterns = (
            "wikipedia",
            "wiki",
            "company profile",
            "company information",
            "funding & investors",
            "funding and investors",
            "funding & key investors",
            "funding and key investors",
            "team & investors",
            "team and investors",
            "funding rounds",
            "list of investors",
            "statistics",
            "revenue, valuation & funding",
            "revenue valuation funding",
            "latest news",
            "newsroom",
            "news and analysis",
            "press releases",
            "all news",
            "news archive",
            "what is ",
            "what's new",
            "what’s new",
            "everything to know",
            "explained",
            "company overview",
        )

        # ----------------------------------------------------
        # ROOT / HOMEPAGE URL
        # ----------------------------------------------------

        if url:

            try:

                parsed_url = (
                    urlparse(
                        url
                    )
                )

                path = (
                    parsed_url.path
                    .strip()
                )

                # Examples:
                #
                # https://mistral.ai
                # https://mistral.ai/
                # https://elevenlabs.io
                #
                # These are company homepages rather than
                # specific business-event articles.

                if path in (
                    "",
                    "/",
                ):

                    return True

            except Exception:

                # URL parsing should never break
                # the signal-analysis pipeline.
                pass

        # ----------------------------------------------------
        # SPECIFIC GENERIC COMPANY-PROFILE PAGES
        # ----------------------------------------------------

        if normalized_title.endswith(
            " - forbes"
        ):

            return True

        # ----------------------------------------------------
        # GENERAL GENERIC TITLE PATTERNS
        # ----------------------------------------------------

        return any(
            pattern in normalized_title
            for pattern
            in generic_patterns
        )

    # ========================================================
    # PROMPT BUILDING
    # ========================================================

    def _build_prompt(
        self,
        article: dict,
    ) -> str:

        return self.prompt_template.format(
            company=(
                article["company"]
            ),
            title=(
                article["title"]
            ),
            source=(
                article["source"]
                or "Unknown source"
            ),
            url=(
                article["url"]
            ),
            content=(
                article["content"]
            ),
        )

    # ========================================================
    # OUTPUT
    # ========================================================

    @staticmethod
    def _print_signal(
        signal: BusinessSignal,
    ) -> None:

        status = (
            "RELEVANT"
            if signal.is_relevant
            else "NOT RELEVANT"
        )

        print(
            f"[SignalAgent] "
            f"Signal: "
            f"{signal.signal_type.value}"
        )

        print(
            f"[SignalAgent] "
            f"Relevance: "
            f"{signal.business_relevance}/100"
        )

        print(
            f"[SignalAgent] "
            f"Confidence: "
            f"{signal.confidence:.2f}"
        )

        print(
            f"[SignalAgent] "
            f"Decision: {status}"
        )