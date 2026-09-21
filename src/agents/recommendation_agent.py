import hashlib
from pathlib import Path

import yaml

from src.config import (
    CONFIDENCE_THRESHOLD,
    EVENTS_PATH,
    PROMPTS_DIR,
    SPONSORSHIP_THRESHOLD,
)
from src.memory.database import (
    Database,
)
from src.memory.event_deduplication import (
    EventDeduplicationService,
)
from src.models.evidence import (
    EvidenceAssessment,
    EvidenceQuality,
)
from src.models.opportunity import (
    OpportunityAnalysis,
)
from src.models.recommendation import (
    Recommendation,
)
from src.models.signal import (
    BusinessSignal,
)
from src.services.ollama_service import (
    OllamaService,
)
from src.utils.hashing import (
    normalize_text,
)
from src.utils.recency import (
    calculate_recency_score,
)


class RecommendationAgent:
    """
    Evaluate verified business signals and decide whether
    they create a credible sponsorship opportunity.

    The agent also selects the most relevant event among:

    - RAISE
    - MACHINA
    - SIGNAL WEEK
    - NONE
    """

    VALID_EVENTS = {
        "RAISE",
        "MACHINA",
        "SIGNAL WEEK",
        "NONE",
    }

    def __init__(
        self,
        database: Database,
        llm: OllamaService,
        event_deduplication_service: (
            EventDeduplicationService | None
        ) = None,
        prompt_path: str | Path | None = None,
        events_path: str | Path | None = None,
    ) -> None:

        self.database = database
        self.llm = llm

        self.event_deduplication_service = (
            event_deduplication_service
        )

        # ====================================================
        # PROMPT PATH
        # ====================================================

        if prompt_path is None:

            self.prompt_path = (
                PROMPTS_DIR
                / "opportunity_analysis.txt"
            )

        else:

            self.prompt_path = Path(
                prompt_path
            )

        # ====================================================
        # EVENTS PATH
        # ====================================================

        if events_path is None:

            self.events_path = (
                EVENTS_PATH
            )

        else:

            self.events_path = Path(
                events_path
            )

        # ====================================================
        # LOAD CONFIGURATION
        # ====================================================

        self.prompt_template = (
            self._load_prompt()
        )

        self.events = (
            self._load_events()
        )

        self.event_profiles_text = (
            self._format_event_profiles(
                self.events
            )
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
    # EVENTS
    # ========================================================

    def _load_events(
        self,
    ) -> list[dict]:
        """
        Load sponsorship event profiles
        from events.yaml.
        """

        if not self.events_path.exists():

            raise FileNotFoundError(
                f"Events file not found: "
                f"{self.events_path}"
            )

        data = yaml.safe_load(
            self.events_path.read_text(
                encoding="utf-8"
            )
        )

        if not isinstance(
            data,
            dict,
        ):

            raise ValueError(
                "Invalid events.yaml format."
            )

        events = data.get(
            "events",
            [],
        )

        if not isinstance(
            events,
            list,
        ) or not events:

            raise ValueError(
                "events.yaml must contain "
                "a non-empty 'events' list."
            )

        return events

    # ========================================================
    # FORMAT EVENT PROFILES
    # ========================================================

    @staticmethod
    def _format_event_profiles(
        events: list[dict],
    ) -> str:
        """
        Convert events.yaml into readable text
        that can be inserted into the LLM prompt.
        """

        blocks: list[str] = []

        for event in events:

            name = str(
                event.get(
                    "name",
                    "",
                )
            ).strip()

            if not name:
                continue

            description = str(
                event.get(
                    "description",
                    "",
                )
            ).strip()

            audience = (
                event.get(
                    "audience",
                    [],
                )
                or []
            )

            themes = (
                event.get(
                    "themes",
                    [],
                )
                or []
            )

            audience_text = "\n".join(
                f"- {item}"
                for item in audience
            )

            themes_text = "\n".join(
                f"- {item}"
                for item in themes
            )

            block = (
                f"EVENT: {name}\n"
                f"DESCRIPTION:\n"
                f"{description}\n\n"
                f"AUDIENCE:\n"
                f"{audience_text}\n\n"
                f"THEMES:\n"
                f"{themes_text}"
            )

            blocks.append(
                block
            )

        if not blocks:

            raise ValueError(
                "No valid event profiles "
                "were found in events.yaml."
            )

        return "\n\n".join(
            blocks
        )

    # ========================================================
    # NORMALIZE EVENT CHOICE
    # ========================================================

    @classmethod
    def _normalize_event_choice(
        cls,
        event_name: str,
    ) -> str:
        """
        Make the event choice deterministic.

        Invalid or unexpected LLM outputs become NONE.
        """

        value = " ".join(
            str(
                event_name
                or ""
            )
            .strip()
            .upper()
            .split()
        )

        aliases = {
            "SIGNALWEEK": "SIGNAL WEEK",
            "SIGNAL_WEEK": "SIGNAL WEEK",
            "NO EVENT": "NONE",
            "NO MATCH": "NONE",
            "N/A": "NONE",
        }

        value = aliases.get(
            value,
            value,
        )

        if value not in cls.VALID_EVENTS:

            return "NONE"

        return value

    # ========================================================
    # EVALUATION
    # ========================================================

    def evaluate(
        self,
        article_id: int,
        signal: BusinessSignal,
        evidence: EvidenceAssessment,
    ) -> Recommendation | None:

        article = (
            self.database
            .get_article_by_id(
                article_id
            )
        )

        if article is None:

            print(
                "[RecommendationAgent] "
                f"Article #{article_id} "
                "not found."
            )

            return None

        # ====================================================
        # EVIDENCE SUPPORT GATE
        # ====================================================

        if not evidence.claim_supported:

            print(
                "[RecommendationAgent] "
                "Evidence does not support "
                "the claim. "
                "No recommendation."
            )

            return (
                self._build_rejected_recommendation(
                    article=article,
                    signal=signal,
                    evidence=evidence,
                )
            )

        # ====================================================
        # SOURCE QUALITY GATE
        # ====================================================
        #
        # A LOW-quality source may still contain information
        # that looks plausible, but it is not strong enough
        # to trigger a sponsorship outreach alert.
        #
        # The information remains available for monitoring,
        # but no recommendation is created.
        # ====================================================

        if (
            evidence.source_quality
            == EvidenceQuality.LOW
        ):

            print(
                "[RecommendationAgent] "
                "Source quality is LOW. "
                "Monitoring only — "
                "no sponsorship alert."
            )

            return (
                self._build_rejected_recommendation(
                    article=article,
                    signal=signal,
                    evidence=evidence,
                )
            )

        # ====================================================
        # BUILD PROMPT
        # ====================================================

        prompt = (
            self._build_prompt(
                article=article,
                signal=signal,
                evidence=evidence,
            )
        )

        print(
            "\n[RecommendationAgent] "
            "Evaluating sponsorship "
            "opportunity for "
            f"{article['company']}"
        )

        # ====================================================
        # LLM ANALYSIS
        # ====================================================

        analysis = (
            self.llm.structured_chat(
                prompt=prompt,
                schema=(
                    OpportunityAnalysis
                ),
                system_prompt=(
                    "You are a conservative "
                    "sponsorship opportunity "
                    "analyst. "
                    "Use only supplied evidence. "
                    "Never invent facts. "
                    "Do not force an event match. "
                    "Confidence MUST be between "
                    "0.0 and 1.0."
                ),
            )
        )

        # ====================================================
        # NORMALIZE EVENT
        # ====================================================

        recommended_event = (
            self._normalize_event_choice(
                analysis.recommended_event
            )
        )

        event_fit_reason = (
            analysis
            .event_fit_reason
            .strip()
        )

        if not event_fit_reason:

            if recommended_event == "NONE":

                event_fit_reason = (
                    "No sufficiently clear fit "
                    "was identified with the "
                    "available sponsorship events."
                )

            else:

                event_fit_reason = (
                    "The selected event was judged "
                    "to have the strongest fit with "
                    "the verified business signal."
                )

        # ====================================================
        # OVERRIDE FIELDS CONTROLLED BY APPLICATION
        # ====================================================

        analysis = (
            analysis.model_copy(
                update={
                    "company": (
                        article["company"]
                    ),
                    "recommended_event": (
                        recommended_event
                    ),
                    "event_fit_reason": (
                        event_fit_reason
                    ),
                    "evidence_quality_score": (
                        evidence
                        .evidence_quality_score
                    ),
                }
            )
        )

        # ====================================================
        # DETERMINISTIC RECENCY
        # ====================================================

        recency_score = (
            calculate_recency_score(
                article[
                    "published_at"
                ]
            )
        )

        # ====================================================
        # DETERMINISTIC TOTAL
        # ====================================================

        total_score = (
            analysis.business_trigger_score
            + analysis.event_fit_score
            + evidence.evidence_quality_score
            + analysis.commercial_intent_score
            + recency_score
        )

        # ====================================================
        # CONSERVATIVE CONFIDENCE
        # ====================================================

        final_confidence = min(
            analysis.confidence,
            evidence.confidence,
            signal.confidence,
        )

        # ====================================================
        # FINAL DECISION
        # ====================================================

        should_recommend = (
            total_score
            >= SPONSORSHIP_THRESHOLD

            and final_confidence
            >= CONFIDENCE_THRESHOLD

            and evidence.claim_supported

            and evidence.evidence_clear

            and evidence.source_quality
            != EvidenceQuality.LOW

            and analysis.recommended_event
            != "NONE"
        )

        # ====================================================
        # BUILD FINAL RECOMMENDATION
        # ====================================================

        recommendation = (
            Recommendation(
                company=(
                    article["company"]
                ),

                signal_type=(
                    signal.signal_type.value
                ),

                event_summary=(
                    signal.summary
                ),

                recommended_event=(
                    analysis.recommended_event
                ),

                event_fit_reason=(
                    analysis.event_fit_reason
                ),

                business_trigger_score=(
                    analysis
                    .business_trigger_score
                ),

                event_fit_score=(
                    analysis
                    .event_fit_score
                ),

                evidence_quality_score=(
                    evidence
                    .evidence_quality_score
                ),

                commercial_intent_score=(
                    analysis
                    .commercial_intent_score
                ),

                recency_score=(
                    recency_score
                ),

                total_score=(
                    total_score
                ),

                confidence=(
                    final_confidence
                ),

                should_recommend=(
                    should_recommend
                ),

                reason=(
                    analysis.reason
                ),

                next_step=(
                    analysis.next_step
                ),

                sources=[
                    article["url"]
                ],
            )
        )

        # ====================================================
        # PRINT RESULT
        # ====================================================

        self._print_result(
            recommendation
        )

        # ====================================================
        # NO ALERT
        # ====================================================

        if not (
            recommendation
            .should_recommend
        ):

            return recommendation

        # ====================================================
        # EVENT-LEVEL DEDUPLICATION
        # ====================================================

        if (
            self.event_deduplication_service
            is not None
        ):

            (
                duplicate_event,
                event_similarity,
                previous_event,
            ) = (
                self.event_deduplication_service
                .is_duplicate_event(
                    company=(
                        recommendation.company
                    ),
                    signal_type=(
                        recommendation
                        .signal_type
                    ),
                    event_summary=(
                        recommendation
                        .event_summary
                    ),
                )
            )

            if duplicate_event:

                print(
                    "[RecommendationAgent] "
                    "Underlying business event "
                    "already alerted "
                    f"(similarity="
                    f"{event_similarity:.2f}). "
                    "No duplicate alert."
                )

                if previous_event:

                    print(
                        "[RecommendationAgent] "
                        "Previous event: "
                        f"{previous_event['event_summary']}"
                    )

                return recommendation

        # ====================================================
        # EXACT RECOMMENDATION HASH
        # ====================================================

        recommendation_hash = (
            self._generate_recommendation_hash(
                recommendation
            )
        )

        # ====================================================
        # SAVE RECOMMENDATION
        # ====================================================

        recommendation_id = (
            self.database
            .save_recommendation(
                company=(
                    recommendation.company
                ),

                signal_type=(
                    recommendation.signal_type
                ),

                event_summary=(
                    recommendation.event_summary
                ),

                recommended_event=(
                    recommendation
                    .recommended_event
                ),

                event_fit_reason=(
                    recommendation
                    .event_fit_reason
                ),

                total_score=(
                    recommendation.total_score
                ),

                confidence=(
                    recommendation.confidence
                ),

                reason=(
                    recommendation.reason
                ),

                next_step=(
                    recommendation.next_step
                ),

                recommendation_hash=(
                    recommendation_hash
                ),
            )
        )

        if recommendation_id is None:

            print(
                "[RecommendationAgent] "
                "Recommendation already known. "
                "No duplicate alert."
            )

        else:

            print(
                "[RecommendationAgent] "
                "Recommendation saved as "
                f"#{recommendation_id}."
            )

        return recommendation

    # ========================================================
    # PROMPT BUILDING
    # ========================================================

    def _build_prompt(
        self,
        article: dict,
        signal: BusinessSignal,
        evidence: EvidenceAssessment,
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

            published_at=(
                article["published_at"]
                or "Unknown"
            ),

            content=(
                article["content"]
            ),

            signal_type=(
                signal.signal_type.value
            ),

            signal_summary=(
                signal.summary
            ),

            business_relevance=(
                signal.business_relevance
            ),

            signal_confidence=(
                signal.confidence
            ),

            source_quality=(
                evidence
                .source_quality
                .value
            ),

            evidence_quality_score=(
                evidence
                .evidence_quality_score
            ),

            claim_supported=(
                evidence
                .claim_supported
            ),

            evidence_clear=(
                evidence
                .evidence_clear
            ),

            verification_confidence=(
                evidence
                .confidence
            ),

            verification_reason=(
                evidence
                .reason
            ),

            event_profiles=(
                self.event_profiles_text
            ),
        )

    # ========================================================
    # HASH
    # ========================================================

    @staticmethod
    def _generate_recommendation_hash(
        recommendation: Recommendation,
    ) -> str:

        value = (
            normalize_text(
                recommendation.company
            )
            + "|"
            + normalize_text(
                recommendation.signal_type
            )
            + "|"
            + normalize_text(
                recommendation.event_summary
            )
        )

        return hashlib.sha256(
            value.encode(
                "utf-8"
            )
        ).hexdigest()

    # ========================================================
    # REJECTED OPPORTUNITY
    # ========================================================

    @staticmethod
    def _build_rejected_recommendation(
        article: dict,
        signal: BusinessSignal,
        evidence: EvidenceAssessment,
    ) -> Recommendation:
        """
        Build a deterministic no-alert result when
        evidence is unsupported or the source quality
        is too weak for sponsorship outreach.
        """

        low_source = (
            evidence.source_quality
            == EvidenceQuality.LOW
        )

        if low_source:

            event_fit_reason = (
                "The source quality is LOW, so the "
                "business signal is not strong enough "
                "to evaluate a reliable sponsorship "
                "event fit."
            )

            reason = (
                "The information may be useful for "
                "monitoring, but a LOW-quality source "
                "is not sufficient to trigger a "
                "sponsorship recommendation."
            )

            next_step = (
                "Continue monitoring and look for "
                "confirmation from an official or "
                "higher-quality source."
            )

        else:

            event_fit_reason = (
                "The business signal does not "
                "have sufficiently verified "
                "evidence to evaluate a credible "
                "event sponsorship fit."
            )

            reason = (
                "The detected business signal "
                "is not sufficiently supported "
                "by the evidence."
            )

            next_step = (
                "Continue monitoring for "
                "stronger or independently "
                "verified evidence."
            )

        return Recommendation(
            company=(
                article["company"]
            ),

            signal_type=(
                signal.signal_type.value
            ),

            event_summary=(
                signal.summary
            ),

            recommended_event="NONE",

            event_fit_reason=(
                event_fit_reason
            ),

            business_trigger_score=0,

            event_fit_score=0,

            evidence_quality_score=(
                evidence
                .evidence_quality_score
            ),

            commercial_intent_score=0,

            recency_score=(
                calculate_recency_score(
                    article[
                        "published_at"
                    ]
                )
            ),

            total_score=(
                evidence
                .evidence_quality_score
            ),

            confidence=(
                min(
                    evidence.confidence,
                    signal.confidence,
                )
            ),

            should_recommend=False,

            reason=(
                reason
            ),

            next_step=(
                next_step
            ),

            sources=[
                article["url"]
            ],
        )

    # ========================================================
    # OUTPUT
    # ========================================================

    @staticmethod
    def _print_result(
        recommendation: Recommendation,
    ) -> None:

        print(
            "[RecommendationAgent] "
            "Recommended event: "
            f"{recommendation.recommended_event}"
        )

        print(
            "[RecommendationAgent] "
            "Event fit reason: "
            f"{recommendation.event_fit_reason}"
        )

        print(
            "[RecommendationAgent] "
            "Business trigger: "
            f"{recommendation.business_trigger_score}/25"
        )

        print(
            "[RecommendationAgent] "
            "Event fit: "
            f"{recommendation.event_fit_score}/25"
        )

        print(
            "[RecommendationAgent] "
            "Evidence quality: "
            f"{recommendation.evidence_quality_score}/20"
        )

        print(
            "[RecommendationAgent] "
            "Commercial intent: "
            f"{recommendation.commercial_intent_score}/15"
        )

        print(
            "[RecommendationAgent] "
            "Recency: "
            f"{recommendation.recency_score}/15"
        )

        print(
            "[RecommendationAgent] "
            "TOTAL: "
            f"{recommendation.total_score}/100"
        )

        print(
            "[RecommendationAgent] "
            "Confidence: "
            f"{recommendation.confidence:.2f}"
        )

        decision = (
            "RECOMMEND"
            if recommendation
            .should_recommend
            else "MONITOR / NO ALERT"
        )

        print(
            "[RecommendationAgent] "
            f"Decision: {decision}"
        )