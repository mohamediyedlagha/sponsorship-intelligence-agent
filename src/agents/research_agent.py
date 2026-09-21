from src.memory.database import (
    Database,
)
from src.memory.deduplication import (
    DeduplicationService,
)
from src.services.search_service import (
    SearchService,
)
from src.services.scraper_service import (
    ScraperService,
)
from src.utils.hashing import (
    generate_content_hash,
)
from src.utils.text_cleaning import (
    normalize_url,
)


class ResearchAgent:

    def __init__(
        self,
        database: Database,
        search_service: SearchService,
        scraper_service: ScraperService,
        deduplication_service: (
            DeduplicationService | None
        ) = None,
    ) -> None:

        self.database = database

        self.search_service = (
            search_service
        )

        self.scraper_service = (
            scraper_service
        )

        self.deduplication_service = (
            deduplication_service
        )

    # ========================================================
    # QUERY
    # ========================================================

    def build_query(
        self,
        company: str,
        keywords: list[str],
    ) -> str:

        keyword_query = (
            " OR ".join(
                f'"{keyword}"'
                for keyword
                in keywords
            )
        )

        return (
            f'"{company}" '
            f"({keyword_query})"
        )

    # ========================================================
    # RESEARCH
    # ========================================================

    def research_company(
        self,
        company: str,
        keywords: list[str],
        preferred_domain: str | None = None,
    ) -> dict:

        query = self.build_query(
            company=company,
            keywords=keywords,
        )

        print(
            f"\n[ResearchAgent] "
            f"Searching: {company}"
        )

        print(
            f"[ResearchAgent] "
            f"Query: {query}"
        )

        search_results = (
            self.search_service.search(
                query=query
            )
        )

        search_results = (
            self._sort_search_results(
                search_results,
                preferred_domain,
            )
        )

        articles_found = len(
            search_results
        )

        new_article_ids = []

        skipped_articles = 0
        scraping_failures = 0
        exact_duplicates = 0
        semantic_duplicates = 0

        for result in search_results:

            url = normalize_url(
                result.url
            )

            content = (
                self.scraper_service
                .scrape(
                    url
                )
            )

            if not content:

                scraping_failures += 1

                content = (
                    result.snippet
                )

            if not content:

                skipped_articles += 1

                print(
                    f"  [SKIPPED] "
                    f"{result.title[:70]}"
                )

                continue

            content_hash = (
                generate_content_hash(
                    company=company,
                    title=result.title,
                    content=content,
                )
            )

            # =================================================
            # EXACT DUPLICATE
            # =================================================

            if self.database.article_exists(
                content_hash
            ):

                exact_duplicates += 1

                print(
                    f"  [KNOWN] "
                    f"{result.title[:70]}"
                )

                continue

            # =================================================
            # SEMANTIC ARTICLE DUPLICATE
            # =================================================

            if (
                self.deduplication_service
                is not None
            ):

                (
                    is_duplicate,
                    similarity,
                    matching_article,
                ) = (
                    self.deduplication_service
                    .is_semantic_duplicate(
                        company=company,
                        title=result.title,
                        content=content,
                    )
                )

                if is_duplicate:

                    semantic_duplicates += 1

                    print(
                        "  [SEMANTIC DUPLICATE "
                        f"{similarity:.2f}] "
                        f"{result.title[:55]}"
                    )

                    if matching_article:

                        print(
                            "      ↳ matches: "
                            f"{matching_article['title'][:55]}"
                        )

                    continue

            # =================================================
            # NEW ARTICLE
            # =================================================

            article_id = (
                self.database.save_article(
                    company=company,
                    title=result.title,
                    url=url,
                    source=(
                        self.get_domain(
                            url
                        )
                    ),
                    published_at=(
                        result.published_at
                    ),
                    content=content,
                    content_hash=(
                        content_hash
                    ),
                )
            )

            if article_id is None:

                exact_duplicates += 1

                print(
                    f"  [KNOWN] "
                    f"{result.title[:70]}"
                )

                continue

            new_article_ids.append(
                article_id
            )

            print(
                f"  [NEW] "
                f"{result.title[:70]}"
            )

        return {
            "company": company,
            "articles_found": (
                articles_found
            ),
            "new_articles": len(
                new_article_ids
            ),
            "new_article_ids": (
                new_article_ids
            ),
            "exact_duplicates": (
                exact_duplicates
            ),
            "semantic_duplicates": (
                semantic_duplicates
            ),
            "scraping_failures": (
                scraping_failures
            ),
            "skipped_articles": (
                skipped_articles
            ),
        }

    # ========================================================
    # RESULT PRIORITY
    # ========================================================

    def _sort_search_results(
        self,
        results,
        preferred_domain: str | None,
    ):

        generic_terms = (
            "wikipedia",
            "company profile",
            "statistics",
            "funding & investors",
            "team & investors",
            "company information",
        )

        def priority(
            result,
        ):

            title = (
                result.title.lower()
            )

            domain = (
                self.get_domain(
                    result.url
                )
            )

            official = (
                preferred_domain
                and self._domain_matches(
                    domain,
                    preferred_domain,
                )
            )

            generic = any(
                term in title
                for term
                in generic_terms
            )

            return (
                0 if official else 1,
                1 if generic else 0,
            )

        return sorted(
            results,
            key=priority,
        )

    # ========================================================
    # DOMAIN UTILITIES
    # ========================================================

    @staticmethod
    def _domain_matches(
        domain: str,
        preferred_domain: str,
    ) -> bool:

        preferred_domain = (
            preferred_domain
            .lower()
            .replace(
                "www.",
                "",
            )
        )

        domain = (
            domain
            .lower()
            .replace(
                "www.",
                "",
            )
        )

        return (
            domain
            == preferred_domain
            or domain.endswith(
                "."
                + preferred_domain
            )
        )

    @staticmethod
    def get_domain(
        url: str,
    ) -> str:

        try:

            domain = (
                url
                .split(
                    "//",
                    1,
                )[-1]
                .split(
                    "/",
                    1,
                )[0]
            )

            return domain.lower()

        except Exception:

            return "unknown"