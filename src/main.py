import sys
from pathlib import Path

import yaml

from src.agents.recommendation_agent import (
    RecommendationAgent,
)
from src.agents.research_agent import (
    ResearchAgent,
)
from src.agents.signal_agent import (
    SignalAgent,
)
from src.agents.verification_agent import (
    VerificationAgent,
)
from src.config import (
    COMPANIES_PATH,
)
from src.memory.database import (
    Database,
)
from src.memory.deduplication import (
    DeduplicationService,
)
from src.memory.event_deduplication import (
    EventDeduplicationService,
)
from src.services.embedding_service import (
    EmbeddingService,
)
from src.services.ollama_service import (
    OllamaService,
)
from src.services.scraper_service import (
    ScraperService,
)
from src.services.search_service import (
    SearchService,
)
from src.utils.logger import (
    print_company_header,
    print_error,
    print_header,
    print_info,
    print_success,
    print_warning,
)
from src.utils.run_report import (
    save_run_report,
)


# ============================================================
# CONFIGURATION
# ============================================================


def load_companies(
    path: str | Path = COMPANIES_PATH,
) -> list[dict]:

    path = Path(
        path
    )

    if not path.exists():

        raise FileNotFoundError(
            "Companies configuration "
            f"not found: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:

        data = yaml.safe_load(
            file
        )

    if not data:
        return []

    companies = data.get(
        "companies",
        [],
    )

    return [
        company
        for company
        in companies
        if company.get(
            "enabled",
            True,
        )
    ]


# ============================================================
# AGENTS
# ============================================================


def build_agents():

    print_info(
        "Initializing local AI services..."
    )

    database = Database()

    llm = OllamaService()

    search_service = (
        SearchService(
            max_results=10
        )
    )

    scraper_service = (
        ScraperService(
            timeout=10,
            max_characters=12000,
        )
    )

    print_info(
        "Loading local embedding model..."
    )

    embedding_service = (
        EmbeddingService()
    )

    deduplication_service = (
        DeduplicationService(
            database=database,
            embedding_service=(
                embedding_service
            ),
        )
    )

    event_deduplication_service = (
        EventDeduplicationService(
            database=database,
            embedding_service=(
                embedding_service
            ),
        )
    )

    research_agent = (
        ResearchAgent(
            database=database,
            search_service=(
                search_service
            ),
            scraper_service=(
                scraper_service
            ),
            deduplication_service=(
                deduplication_service
            ),
        )
    )

    signal_agent = (
        SignalAgent(
            database=database,
            llm=llm,
        )
    )

    verification_agent = (
        VerificationAgent(
            database=database,
            llm=llm,
        )
    )

    recommendation_agent = (
        RecommendationAgent(
            database=database,
            llm=llm,
            event_deduplication_service=(
                event_deduplication_service
            ),
        )
    )

    return {
        "database": database,
        "research": research_agent,
        "signal": signal_agent,
        "verification": (
            verification_agent
        ),
        "recommendation": (
            recommendation_agent
        ),
    }


# ============================================================
# COMPANY PIPELINE
# ============================================================


def process_company(
    company_config: dict,
    agents: dict,
) -> dict:

    company_name = (
        company_config["name"]
    )

    keywords = (
        company_config.get(
            "keywords",
            [],
        )
    )

    website = (
        company_config.get(
            "website",
            "",
        )
    )

    preferred_domain = None

    if website:

        preferred_domain = (
            ResearchAgent
            .get_domain(
                website
            )
        )

    database = (
        agents["database"]
    )

    print_company_header(
        company_name
    )

    # ========================================================
    # RESEARCH
    # ========================================================

    research_result = (
        agents["research"]
        .research_company(
            company=company_name,
            keywords=keywords,
            preferred_domain=(
                preferred_domain
            ),
        )
    )

    new_article_ids = (
        research_result[
            "new_article_ids"
        ]
    )

    print_info(
        f"{research_result['articles_found']} "
        "search results found."
    )

    print_info(
        f"{research_result['new_articles']} "
        "new articles detected."
    )

    print_info(
        f"{research_result['exact_duplicates']} "
        "exact duplicates."
    )

    print_info(
        f"{research_result['semantic_duplicates']} "
        "semantic duplicates."
    )

    if not new_article_ids:

        print_success(
            "No new information. "
            "Nothing to analyze."
        )

        return {
            "company": company_name,
            "articles_found": (
                research_result[
                    "articles_found"
                ]
            ),
            "new_articles": 0,
            "signals_detected": 0,
            "recommendations_created": 0,
            "results": [],
        }

    signals_detected = 0
    recommendations_created = 0

    pipeline_results = []

    # ========================================================
    # NEW ARTICLES
    # ========================================================

    for article_id in new_article_ids:

        article = (
            database.get_article_by_id(
                article_id
            )
        )

        if article is None:
            continue

        print_info(
            f"Processing article "
            f"#{article_id}: "
            f"{article['title'][:80]}"
        )

        # ====================================================
        # SIGNAL
        # ====================================================

        try:

            signal = (
                agents["signal"]
                .analyze_article(
                    article_id
                )
            )

        except Exception as exc:

            print_error(
                "Signal analysis failed "
                f"for article #{article_id}: "
                f"{exc}"
            )

            continue

        if signal is None:
            continue

        # ====================================================
        # NOT RELEVANT
        # ====================================================

        if not signal.is_relevant:

            print_warning(
                "No meaningful business signal. "
                "Article kept in memory."
            )

            pipeline_results.append(
                {
                    "article_id": (
                        article_id
                    ),
                    "title": (
                        article["title"]
                    ),
                    "url": (
                        article["url"]
                    ),
                    "signal": (
                        signal
                        .signal_type
                        .value
                    ),
                    "signal_relevance": (
                        signal
                        .business_relevance
                    ),
                    "status": (
                        "NOT_RELEVANT"
                    ),
                    "event_summary": (
                        signal.summary
                    ),
                    "recommended_event": (
                        "NONE"
                    ),
                    "event_fit_reason": (
                        "The article did not pass "
                        "the business-signal "
                        "relevance gate."
                    ),
                    "evidence_score": None,
                    "total_score": None,
                    "confidence": (
                        signal.confidence
                    ),
                    "recommend": False,
                    "reason": (
                        "No sufficiently meaningful "
                        "business signal was detected."
                    ),
                    "next_step": (
                        "Continue monitoring."
                    ),
                    "sources": [
                        article["url"]
                    ],
                }
            )

            continue

        signals_detected += 1

        # ====================================================
        # EVIDENCE
        # ====================================================

        try:

            evidence = (
                agents["verification"]
                .verify(
                    article_id=(
                        article_id
                    ),
                    signal=signal,
                )
            )

        except Exception as exc:

            print_error(
                "Evidence verification "
                "failed for article "
                f"#{article_id}: {exc}"
            )

            continue

        if evidence is None:
            continue

        # ====================================================
        # COUNT RECOMMENDATIONS BEFORE
        # ====================================================

        recommendations_before = len(
            database
            .get_recommendations_by_company(
                company_name
            )
        )

        # ====================================================
        # RECOMMENDATION
        # ====================================================

        try:

            recommendation = (
                agents["recommendation"]
                .evaluate(
                    article_id=(
                        article_id
                    ),
                    signal=signal,
                    evidence=evidence,
                )
            )

        except Exception as exc:

            print_error(
                "Recommendation analysis "
                f"failed for article "
                f"#{article_id}: {exc}"
            )

            continue

        if recommendation is None:
            continue

        # ====================================================
        # COUNT RECOMMENDATIONS AFTER
        # ====================================================

        recommendations_after = len(
            database
            .get_recommendations_by_company(
                company_name
            )
        )

        if (
            recommendations_after
            > recommendations_before
        ):

            recommendations_created += 1

        # ====================================================
        # SAVE RESULT FOR MARKDOWN REPORT
        # ====================================================

        pipeline_results.append(
            {
                "article_id": (
                    article_id
                ),

                "title": (
                    article["title"]
                ),

                "url": (
                    article["url"]
                ),

                "signal": (
                    signal
                    .signal_type
                    .value
                ),

                "signal_relevance": (
                    signal
                    .business_relevance
                ),

                # --------------------------------------------
                # BUSINESS EVENT
                # --------------------------------------------

                "event_summary": (
                    recommendation
                    .event_summary
                ),

                # --------------------------------------------
                # EVENT MATCHING
                # --------------------------------------------

                "recommended_event": (
                    recommendation
                    .recommended_event
                ),

                "event_fit_reason": (
                    recommendation
                    .event_fit_reason
                ),

                # --------------------------------------------
                # EVIDENCE
                # --------------------------------------------

                "evidence_score": (
                    evidence
                    .evidence_quality_score
                ),

                # --------------------------------------------
                # OPPORTUNITY
                # --------------------------------------------

                "total_score": (
                    recommendation
                    .total_score
                ),

                "confidence": (
                    recommendation
                    .confidence
                ),

                "recommend": (
                    recommendation
                    .should_recommend
                ),

                "reason": (
                    recommendation
                    .reason
                ),

                "next_step": (
                    recommendation
                    .next_step
                ),

                # --------------------------------------------
                # SOURCES
                # --------------------------------------------

                "sources": (
                    recommendation
                    .sources
                ),
            }
        )

    # ========================================================
    # COMPANY SUMMARY
    # ========================================================

    return {
        "company": company_name,

        "articles_found": (
            research_result[
                "articles_found"
            ]
        ),

        "new_articles": len(
            new_article_ids
        ),

        "signals_detected": (
            signals_detected
        ),

        "recommendations_created": (
            recommendations_created
        ),

        "results": (
            pipeline_results
        ),
    }


# ============================================================
# MAIN
# ============================================================


def main() -> int:

    print_header(
        "SPONSORSHIP INTELLIGENCE AGENT"
    )

    # ========================================================
    # LOAD COMPANIES
    # ========================================================

    try:

        companies = (
            load_companies()
        )

    except Exception as exc:

        print_error(
            "Unable to load companies: "
            f"{exc}"
        )

        return 1

    if not companies:

        print_warning(
            "No enabled companies found."
        )

        return 0

    # ========================================================
    # BUILD AGENTS
    # ========================================================

    try:

        agents = build_agents()

    except Exception as exc:

        print_error(
            "Agent initialization failed: "
            f"{exc}"
        )

        return 1

    database = (
        agents["database"]
    )

    # ========================================================
    # START RUN
    # ========================================================

    run_id = (
        database.start_run()
    )

    print_info(
        f"Starting run #{run_id}"
    )

    company_results = []

    total_articles_found = 0
    total_new_articles = 0
    total_recommendations = 0

    try:

        # ====================================================
        # PROCESS COMPANIES
        # ====================================================

        for company in companies:

            try:

                result = (
                    process_company(
                        company_config=(
                            company
                        ),
                        agents=agents,
                    )
                )

                company_results.append(
                    result
                )

                total_articles_found += (
                    result[
                        "articles_found"
                    ]
                )

                total_new_articles += (
                    result[
                        "new_articles"
                    ]
                )

                total_recommendations += (
                    result[
                        "recommendations_created"
                    ]
                )

            except Exception as exc:

                print_error(
                    "Company processing "
                    "failed for "
                    f"{company.get('name', 'Unknown')}: "
                    f"{exc}"
                )

                continue

        # ====================================================
        # FINISH RUN
        # ====================================================

        database.finish_run(
            run_id=run_id,
            articles_found=(
                total_articles_found
            ),
            new_articles=(
                total_new_articles
            ),
            recommendations_created=(
                total_recommendations
            ),
        )

        # ====================================================
        # GENERATE REPORT
        # ====================================================

        report_path = (
            save_run_report(
                run_id=run_id,
                company_results=(
                    company_results
                ),
                articles_found=(
                    total_articles_found
                ),
                new_articles=(
                    total_new_articles
                ),
                recommendations_created=(
                    total_recommendations
                ),
            )
        )

        # ====================================================
        # FINAL OUTPUT
        # ====================================================

        print_header(
            f"RUN #{run_id} COMPLETE"
        )

        print_success(
            "Articles found: "
            f"{total_articles_found}"
        )

        print_success(
            "New articles: "
            f"{total_new_articles}"
        )

        print_success(
            "New recommendations: "
            f"{total_recommendations}"
        )

        print_success(
            "Report saved to: "
            f"{report_path}"
        )

        return 0

    # ========================================================
    # INTERRUPTED
    # ========================================================

    except KeyboardInterrupt:

        database.fail_run(
            run_id
        )

        print_warning(
            "Execution interrupted."
        )

        return 130

    # ========================================================
    # FAILED
    # ========================================================

    except Exception as exc:

        database.fail_run(
            run_id
        )

        print_error(
            f"Run failed: {exc}"
        )

        return 1


if __name__ == "__main__":

    sys.exit(
        main()
    )