import re
from typing import Protocol

from src.config import (
    EVENT_DUPLICATE_THRESHOLD,
)
from src.memory.database import (
    Database,
)


class EmbeddingProvider(
    Protocol
):

    def similarity(
        self,
        text_a: str,
        text_b: str,
    ) -> float:
        ...


class EventDeduplicationService:
    """
    Detect whether an underlying business event
    has already produced a sponsorship alert.

    The decision combines:

    1. Signal type
    2. Semantic similarity
    3. Deterministic event facts

    Funding events receive additional deterministic
    checks using funding amount and funding round.

    Example:

    "$180M Series C"
    and
    "$500M Series D"

    are NOT the same funding event.

    But:

    "$500M Series D at $11B valuation"
    and
    "$500M from Sequoia at an $11B valuation"

    can be recognized as the same funding event
    even when their wording is different.
    """

    # A shared funding amount is a strong signal,
    # so we can use a lower semantic threshold than
    # the general event threshold.
    FUNDING_AMOUNT_DUPLICATE_THRESHOLD = 0.60

    # A shared explicit funding round is useful,
    # but less specific than a shared amount.
    FUNDING_ROUND_DUPLICATE_THRESHOLD = 0.72

    def __init__(
        self,
        database: Database,
        embedding_service: EmbeddingProvider,
        threshold: float = (
            EVENT_DUPLICATE_THRESHOLD
        ),
    ) -> None:

        self.database = database

        self.embedding_service = (
            embedding_service
        )

        self.threshold = threshold

    # ========================================================
    # PUBLIC API
    # ========================================================

    def is_duplicate_event(
        self,
        company: str,
        signal_type: str,
        event_summary: str,
    ) -> tuple[
        bool,
        float,
        dict | None,
    ]:

        recommendations = (
            self.database
            .get_recommendations_by_company(
                company
            )
        )

        # Only compare recommendations for:
        #
        # - the same company
        # - the same business signal type

        candidates = [
            recommendation
            for recommendation
            in recommendations
            if (
                recommendation[
                    "signal_type"
                ]
                == signal_type

                and recommendation.get(
                    "event_summary"
                )
            )
        ]

        if not candidates:

            return (
                False,
                0.0,
                None,
            )

        best_similarity = 0.0
        best_match = None

        for recommendation in candidates:

            previous_summary = (
                recommendation[
                    "event_summary"
                ]
            )

            similarity = (
                self.embedding_service
                .similarity(
                    event_summary,
                    previous_summary,
                )
            )

            # =================================================
            # FUNDING CHECK
            # =================================================

            if signal_type == "FUNDING":

                # ---------------------------------------------
                # DIFFERENT FUNDING EVENTS?
                # ---------------------------------------------

                if self._funding_events_conflict(
                    event_summary,
                    previous_summary,
                ):

                    # Clear deterministic evidence says
                    # these are different funding rounds.

                    continue

                # ---------------------------------------------
                # SAME FUNDING EVENT?
                # ---------------------------------------------

                if self._funding_events_match(
                    text_a=event_summary,
                    text_b=previous_summary,
                    similarity=similarity,
                ):

                    return (
                        True,
                        similarity,
                        recommendation,
                    )

            # =================================================
            # PRODUCT LAUNCH CHECK
            # =================================================

            if signal_type == "PRODUCT_LAUNCH":

                product_overlap = (
                    self._important_token_overlap(
                        event_summary,
                        previous_summary,
                        company,
                    )
                )

                # Product articles often use different
                # wording for the same launch.

                product_duplicate = (
                    similarity >= 0.78
                    and product_overlap >= 0.20
                )

                if product_duplicate:

                    return (
                        True,
                        similarity,
                        recommendation,
                    )

            # =================================================
            # NORMAL SEMANTIC COMPARISON
            # =================================================

            if (
                similarity
                > best_similarity
            ):

                best_similarity = (
                    similarity
                )

                best_match = (
                    recommendation
                )

        is_duplicate = (
            best_similarity
            >= self.threshold
        )

        return (
            is_duplicate,
            best_similarity,
            best_match,
        )

    # ========================================================
    # FUNDING EVENT MATCH
    # ========================================================

    @classmethod
    def _funding_events_match(
        cls,
        text_a: str,
        text_b: str,
        similarity: float,
    ) -> bool:
        """
        Return True when two funding summaries have
        strong evidence that they describe the same
        underlying funding event.

        Strong indicators:

        1. Same funding amount + same funding round.
        2. Same funding amount + reasonable semantic
           similarity.
        3. Same explicit funding round + stronger
           semantic similarity.

        Examples:

        "$500M Series D at $11B valuation"

        and

        "$500M from Sequoia at an $11B valuation"

        should normally be treated as the same event.

        However:

        "$180M Series C"

        and

        "$500M Series D"

        remain different events.
        """

        amounts_a = (
            cls._extract_funding_amounts(
                text_a
            )
        )

        amounts_b = (
            cls._extract_funding_amounts(
                text_b
            )
        )

        rounds_a = (
            cls._extract_funding_rounds(
                text_a
            )
        )

        rounds_b = (
            cls._extract_funding_rounds(
                text_b
            )
        )

        shared_amounts = (
            amounts_a
            & amounts_b
        )

        shared_rounds = (
            rounds_a
            & rounds_b
        )

        # ----------------------------------------------------
        # SAME AMOUNT + SAME ROUND
        # ----------------------------------------------------
        #
        # Example:
        #
        # $500M Series D
        # vs
        # Series D financing of $500 million
        #
        # This is strong enough to consider the
        # events duplicates without requiring a
        # high embedding similarity.
        # ----------------------------------------------------

        if (
            shared_amounts
            and shared_rounds
        ):

            return True

        # ----------------------------------------------------
        # SAME FUNDING AMOUNT
        # ----------------------------------------------------
        #
        # Sometimes one article mentions "Series D"
        # while another article only says "$500M funding".
        #
        # In that situation the common amount is strong
        # evidence, but we still require some semantic
        # similarity for safety.
        # ----------------------------------------------------

        if (
            shared_amounts
            and similarity
            >= cls.FUNDING_AMOUNT_DUPLICATE_THRESHOLD
        ):

            return True

        # ----------------------------------------------------
        # SAME FUNDING ROUND
        # ----------------------------------------------------
        #
        # A round name alone is weaker evidence because
        # descriptions can omit the amount.
        #
        # Therefore use a slightly stronger semantic
        # threshold.
        # ----------------------------------------------------

        if (
            shared_rounds
            and similarity
            >= cls.FUNDING_ROUND_DUPLICATE_THRESHOLD
        ):

            return True

        return False

    # ========================================================
    # FUNDING EVENT CONFLICT
    # ========================================================

    @classmethod
    def _funding_events_conflict(
        cls,
        text_a: str,
        text_b: str,
    ) -> bool:
        """
        Return True when two funding summaries contain
        clear evidence that they are different events.

        Example:

        $180M Series C

        vs

        $500M Series D

        -> conflict -> NOT duplicate
        """

        amounts_a = (
            cls._extract_funding_amounts(
                text_a
            )
        )

        amounts_b = (
            cls._extract_funding_amounts(
                text_b
            )
        )

        rounds_a = (
            cls._extract_funding_rounds(
                text_a
            )
        )

        rounds_b = (
            cls._extract_funding_rounds(
                text_b
            )
        )

        # ----------------------------------------------------
        # DIFFERENT FUNDING AMOUNTS
        # ----------------------------------------------------

        if amounts_a and amounts_b:

            if amounts_a.isdisjoint(
                amounts_b
            ):

                return True

        # ----------------------------------------------------
        # DIFFERENT FUNDING ROUNDS
        # ----------------------------------------------------

        if rounds_a and rounds_b:

            if rounds_a.isdisjoint(
                rounds_b
            ):

                return True

        return False

    # ========================================================
    # FUNDING AMOUNT EXTRACTION
    # ========================================================

    @classmethod
    def _extract_funding_amounts(
        cls,
        text: str,
    ) -> set[str]:
        """
        Extract likely funding amounts while excluding
        amounts that are clearly used only as company
        valuations.

        Example:

        "raised $500M Series D at an $11B valuation"

        All monetary amounts:
            {$500m, $11b}

        Funding amounts:
            {$500m}

        This prevents the valuation itself from becoming
        the main deterministic funding identifier.
        """

        all_amounts = (
            cls._extract_money_amounts(
                text
            )
        )

        valuation_amounts = (
            cls._extract_valuation_amounts(
                text
            )
        )

        funding_amounts = (
            all_amounts
            - valuation_amounts
        )

        # If everything was classified as a valuation,
        # return an empty set rather than using a
        # valuation as the funding amount.

        return funding_amounts

    # ========================================================
    # MONEY EXTRACTION
    # ========================================================

    @staticmethod
    def _extract_money_amounts(
        text: str,
    ) -> set[str]:
        """
        Extract normalized monetary amounts.

        Examples:

        $500M
        $500 million
        €3B
        3 billion euros
        """

        text = text.lower()

        results: set[str] = set()

        # ----------------------------------------------------
        # SYMBOL FORM
        # ----------------------------------------------------
        #
        # Examples:
        #
        # $500M
        # €3B
        # £180m
        # ----------------------------------------------------

        symbol_pattern = (
            r"([$€£])\s*"
            r"(\d+(?:\.\d+)?)\s*"
            r"(billion|million|bn|m|b)"
        )

        for match in re.finditer(
            symbol_pattern,
            text,
        ):

            currency = (
                match.group(1)
            )

            number = (
                match.group(2)
            )

            unit = (
                EventDeduplicationService
                ._normalize_money_unit(
                    match.group(3)
                )
            )

            results.add(
                f"{currency}{number}{unit}"
            )

        # ----------------------------------------------------
        # WORD FORM
        # ----------------------------------------------------
        #
        # Examples:
        #
        # 3 billion euros
        # 500 million dollars
        # ----------------------------------------------------

        word_pattern = (
            r"(\d+(?:\.\d+)?)\s*"
            r"(billion|million|bn|m|b)"
            r"\s*"
            r"(euros?|dollars?|pounds?)"
        )

        for match in re.finditer(
            word_pattern,
            text,
        ):

            number = (
                match.group(1)
            )

            unit = (
                EventDeduplicationService
                ._normalize_money_unit(
                    match.group(2)
                )
            )

            currency_word = (
                match.group(3)
            )

            if "euro" in currency_word:

                currency = "€"

            elif "dollar" in currency_word:

                currency = "$"

            else:

                currency = "£"

            results.add(
                f"{currency}{number}{unit}"
            )

        return results

    # ========================================================
    # VALUATION AMOUNT EXTRACTION
    # ========================================================

    @classmethod
    def _extract_valuation_amounts(
        cls,
        text: str,
    ) -> set[str]:
        """
        Extract monetary values that are explicitly
        associated with company valuation.

        Examples:

        "$11B valuation"
        "valuation of $11 billion"
        "post-money valuation of €21B"
        """

        text = text.lower()

        results: set[str] = set()

        money_expression = (
            r"([$€£])\s*"
            r"(\d+(?:\.\d+)?)\s*"
            r"(billion|million|bn|m|b)"
        )

        # ----------------------------------------------------
        # MONEY BEFORE "VALUATION"
        # ----------------------------------------------------
        #
        # Examples:
        #
        # $11B valuation
        # $11 billion post-money valuation
        # ----------------------------------------------------

        before_pattern = (
            money_expression
            + r"\s*"
            r"(?:post[-\s]?money\s+)?"
            r"valuation"
        )

        for match in re.finditer(
            before_pattern,
            text,
        ):

            currency = (
                match.group(1)
            )

            number = (
                match.group(2)
            )

            unit = (
                cls._normalize_money_unit(
                    match.group(3)
                )
            )

            results.add(
                f"{currency}{number}{unit}"
            )

        # ----------------------------------------------------
        # "VALUATION" BEFORE MONEY
        # ----------------------------------------------------
        #
        # Examples:
        #
        # valuation of $11B
        # valuation at $11 billion
        # valuation: €21B
        # ----------------------------------------------------

        after_pattern = (
            r"(?:post[-\s]?money\s+)?"
            r"valuation"
            r"(?:\s+of|\s+at|\s*:)?"
            r"\s*"
            r"(?:over\s+|about\s+|around\s+|"
            r"approximately\s+)?"
            + money_expression
        )

        for match in re.finditer(
            after_pattern,
            text,
        ):

            currency = (
                match.group(1)
            )

            number = (
                match.group(2)
            )

            unit = (
                cls._normalize_money_unit(
                    match.group(3)
                )
            )

            results.add(
                f"{currency}{number}{unit}"
            )

        return results

    # ========================================================
    # MONEY UNIT NORMALIZATION
    # ========================================================

    @staticmethod
    def _normalize_money_unit(
        unit: str,
    ) -> str:

        unit = unit.lower()

        if unit in {
            "billion",
            "bn",
            "b",
        }:

            return "b"

        return "m"

    # ========================================================
    # FUNDING ROUND EXTRACTION
    # ========================================================

    @staticmethod
    def _extract_funding_rounds(
        text: str,
    ) -> set[str]:
        """
        Extract funding round names.

        Examples:

        Series A
        Series B
        Series C
        Series D
        Seed
        Pre-Seed
        """

        text = text.lower()

        rounds: set[str] = set()

        series_matches = re.findall(
            r"\bseries\s+([a-h])\b",
            text,
        )

        for series in series_matches:

            rounds.add(
                f"series {series}"
            )

        if re.search(
            r"\bpre[-\s]?seed\b",
            text,
        ):

            rounds.add(
                "pre-seed"
            )

        elif re.search(
            r"\bseed\b",
            text,
        ):

            rounds.add(
                "seed"
            )

        return rounds

    # ========================================================
    # PRODUCT TOKEN OVERLAP
    # ========================================================

    @classmethod
    def _important_token_overlap(
        cls,
        text_a: str,
        text_b: str,
        company: str,
    ) -> float:
        """
        Compare meaningful tokens from two event
        summaries.

        Useful for detecting the same product launch
        described with different wording.
        """

        tokens_a = (
            cls._important_tokens(
                text_a,
                company,
            )
        )

        tokens_b = (
            cls._important_tokens(
                text_b,
                company,
            )
        )

        if (
            not tokens_a
            or not tokens_b
        ):

            return 0.0

        intersection = (
            tokens_a
            & tokens_b
        )

        union = (
            tokens_a
            | tokens_b
        )

        return (
            len(intersection)
            / len(union)
        )

    @staticmethod
    def _important_tokens(
        text: str,
        company: str,
    ) -> set[str]:

        stop_words = {
            "the",
            "and",
            "for",
            "with",
            "from",
            "into",
            "that",
            "this",
            "new",
            "launch",
            "launches",
            "launched",
            "product",
            "products",
            "model",
            "models",
            "company",
            "platform",
            "announces",
            "announced",
            "introduces",
            "introduced",
            "release",
            "releases",
            "released",
            "ai",
        }

        company_tokens = set(
            re.findall(
                r"[a-z0-9]+",
                company.lower(),
            )
        )

        tokens = set(
            re.findall(
                r"[a-z0-9]+",
                text.lower(),
            )
        )

        return {
            token
            for token in tokens
            if (
                len(token) >= 2
                and token
                not in stop_words
                and token
                not in company_tokens
            )
        }