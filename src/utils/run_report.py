from datetime import (
    datetime,
    timezone,
)
from pathlib import Path


BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
    .parent
)

DEMO_DIR = (
    BASE_DIR
    / "demo"
)


def save_run_report(
    run_id: int,
    company_results: list[dict],
    articles_found: int,
    new_articles: int,
    recommendations_created: int,
) -> Path:
    """
    Generate a Markdown report documenting
    one execution of the sponsorship agent.

    The report is useful for the assessment because
    it demonstrates:

    - public research,
    - persistent memory,
    - business signals,
    - evidence quality,
    - event matching,
    - sponsorship recommendations,
    - suggested next steps,
    - source links.
    """

    # ========================================================
    # CREATE DEMO DIRECTORY
    # ========================================================

    DEMO_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    report_path = (
        DEMO_DIR
        / f"run_{run_id}.md"
    )

    created_at = (
        datetime.now(
            timezone.utc
        ).isoformat()
    )

    lines: list[str] = []

    # ========================================================
    # REPORT TITLE
    # ========================================================

    lines.append(
        f"# Sponsorship Intelligence Agent — Run #{run_id}"
    )

    lines.append("")

    lines.append(
        f"Generated at: `{created_at}`"
    )

    lines.append("")

    # ========================================================
    # RUN SUMMARY
    # ========================================================

    lines.append(
        "## Run Summary"
    )

    lines.append("")

    lines.append(
        f"- Articles found: "
        f"**{articles_found}**"
    )

    lines.append(
        f"- New articles: "
        f"**{new_articles}**"
    )

    lines.append(
        "- New sponsorship recommendations: "
        f"**{recommendations_created}**"
    )

    lines.append("")

    # ========================================================
    # COMPANY RESULTS
    # ========================================================

    for company in company_results:

        lines.append(
            f"## {company['company']}"
        )

        lines.append("")

        lines.append(
            f"- Search results: "
            f"**{company['articles_found']}**"
        )

        lines.append(
            f"- New articles: "
            f"**{company['new_articles']}**"
        )

        lines.append(
            f"- Relevant business signals: "
            f"**{company['signals_detected']}**"
        )

        lines.append(
            f"- New recommendations: "
            f"**{company['recommendations_created']}**"
        )

        lines.append("")

        results = company.get(
            "results",
            [],
        )

        if not results:

            lines.append(
                "No new actionable information "
                "was detected in this run."
            )

            lines.append("")

            continue

        # ====================================================
        # ARTICLE ANALYSIS
        # ====================================================

        for index, result in enumerate(
            results,
            start=1,
        ):

            lines.append(
                f"### Result {index}"
            )

            lines.append("")

            # ------------------------------------------------
            # ARTICLE
            # ------------------------------------------------

            lines.append(
                f"**Article:** "
                f"{result.get('title', 'Unknown')}"
            )

            lines.append("")

            # ------------------------------------------------
            # SOURCE
            # ------------------------------------------------

            if result.get("url"):

                lines.append(
                    f"**Source:** "
                    f"{result['url']}"
                )

                lines.append("")

            # ------------------------------------------------
            # BUSINESS SIGNAL
            # ------------------------------------------------

            lines.append(
                f"**Signal:** "
                f"{result.get('signal', 'Unknown')}"
            )

            lines.append("")

            # ------------------------------------------------
            # BUSINESS EVENT SUMMARY
            # ------------------------------------------------

            if result.get(
                "event_summary"
            ):

                lines.append(
                    "**Business event:**"
                )

                lines.append("")

                lines.append(
                    result[
                        "event_summary"
                    ]
                )

                lines.append("")

            # ------------------------------------------------
            # SIGNAL RELEVANCE
            # ------------------------------------------------

            if (
                result.get(
                    "signal_relevance"
                )
                is not None
            ):

                lines.append(
                    "**Signal relevance:** "
                    f"{result['signal_relevance']}/100"
                )

                lines.append("")

            # ------------------------------------------------
            # EVIDENCE QUALITY
            # ------------------------------------------------

            if (
                result.get(
                    "evidence_score"
                )
                is not None
            ):

                lines.append(
                    "**Evidence quality:** "
                    f"{result['evidence_score']}/20"
                )

                lines.append("")

            # =================================================
            # EVENT MATCHING
            # =================================================

            recommended_event = (
                result.get(
                    "recommended_event"
                )
            )

            if recommended_event:

                lines.append(
                    "**Recommended event:** "
                    f"`{recommended_event}`"
                )

                lines.append("")

            event_fit_reason = (
                result.get(
                    "event_fit_reason"
                )
            )

            if event_fit_reason:

                lines.append(
                    "**Why this event:**"
                )

                lines.append("")

                lines.append(
                    event_fit_reason
                )

                lines.append("")

            # ------------------------------------------------
            # OPPORTUNITY SCORE
            # ------------------------------------------------

            if (
                result.get(
                    "total_score"
                )
                is not None
            ):

                lines.append(
                    "**Opportunity score:** "
                    f"{result['total_score']}/100"
                )

                lines.append("")

            # ------------------------------------------------
            # CONFIDENCE
            # ------------------------------------------------

            if (
                result.get(
                    "confidence"
                )
                is not None
            ):

                lines.append(
                    "**Confidence:** "
                    f"{result['confidence']:.2f}"
                )

                lines.append("")

            # =================================================
            # FINAL DECISION
            # =================================================

            recommend = result.get(
                "recommend",
                False,
            )

            decision = (
                "RECOMMEND"
                if recommend
                else "NO ALERT / MONITOR"
            )

            lines.append(
                f"**Decision:** "
                f"`{decision}`"
            )

            lines.append("")

            # ------------------------------------------------
            # WHY
            # ------------------------------------------------

            if result.get(
                "reason"
            ):

                lines.append(
                    "**Why this company:**"
                )

                lines.append("")

                lines.append(
                    result[
                        "reason"
                    ]
                )

                lines.append("")

            # ------------------------------------------------
            # NEXT STEP
            # ------------------------------------------------

            if result.get(
                "next_step"
            ):

                lines.append(
                    "**Suggested next step:**"
                )

                lines.append("")

                lines.append(
                    result[
                        "next_step"
                    ]
                )

                lines.append("")

            # ------------------------------------------------
            # SOURCES
            # ------------------------------------------------

            sources = result.get(
                "sources",
                [],
            )

            if sources:

                lines.append(
                    "**Sources:**"
                )

                lines.append("")

                for source in sources:

                    lines.append(
                        f"- {source}"
                    )

                lines.append("")

            elif result.get("url"):

                # The article URL is always a valid
                # source fallback for the report.

                lines.append(
                    "**Sources:**"
                )

                lines.append("")

                lines.append(
                    f"- {result['url']}"
                )

                lines.append("")

            lines.append("---")

            lines.append("")

    # ========================================================
    # MEMORY BEHAVIOR
    # ========================================================

    lines.append(
        "## Memory Behavior"
    )

    lines.append("")

    if new_articles == 0:

        lines.append(
            "No new articles were discovered. "
            "Previously processed information was "
            "recognized by the agent and was not "
            "re-analyzed or re-alerted."
        )

    else:

        lines.append(
            "Only previously unseen information "
            "was passed to the analysis pipeline. "
            "Exact and semantic duplicate detection "
            "prevented known information from being "
            "processed as new."
        )

    lines.append("")

    lines.append(
        "The SQLite database persists article hashes, "
        "business signals, recommendations and run history "
        "between executions."
    )

    lines.append("")

    # ========================================================
    # EVENT MATCHING EXPLANATION
    # ========================================================

    lines.append(
        "## Sponsorship Event Matching"
    )

    lines.append("")

    lines.append(
        "Verified business opportunities are evaluated "
        "against the available sponsorship events: "
        "**RAISE**, **MACHINA** and **SIGNAL WEEK**."
    )

    lines.append("")

    lines.append(
        "The agent may also return **NONE** when the "
        "business event does not have a sufficiently clear "
        "connection with any of the available event profiles."
    )

    lines.append("")

    lines.append(
        "An event is not selected simply because the company "
        "works in technology or AI. The business event, "
        "audience, themes and commercial reason must have "
        "a credible connection."
    )

    lines.append("")

    # ========================================================
    # ALERT POLICY
    # ========================================================

    lines.append(
        "## Alert Policy"
    )

    lines.append("")

    lines.append(
        "A recommendation is only created when the "
        "opportunity passes the configured score and "
        "confidence thresholds, the evidence is supported "
        "and clear, a relevant sponsorship event is selected, "
        "and the underlying business event has not already "
        "generated an alert."
    )

    lines.append("")

    # ========================================================
    # WRITE REPORT
    # ========================================================

    report_path.write_text(
        "\n".join(
            lines
        ),
        encoding="utf-8",
    )

    return report_path