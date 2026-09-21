import re
import time
from dataclasses import dataclass

from ddgs import DDGS


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    published_at: str | None = None


class SearchService:
    """
    Search public web information using DDGS.

    Strategy:
    1. Try the original advanced query.
    2. If it returns no results, retry with simpler
       company + keyword queries.
    3. Remove duplicate URLs.
    """

    def __init__(
        self,
        max_results: int = 10,
    ) -> None:
        self.max_results = max_results

    # ========================================================
    # PUBLIC SEARCH
    # ========================================================

    def search(
        self,
        query: str,
    ) -> list[SearchResult]:

        # ----------------------------------------------------
        # 1. Try original advanced query
        # ----------------------------------------------------

        print(
            "[SearchService] "
            "Trying primary search query..."
        )

        primary_results = self._run_search(
            query=query,
            max_results=self.max_results,
        )

        if primary_results:
            return primary_results[
                : self.max_results
            ]

        # ----------------------------------------------------
        # 2. Fallback to simpler queries
        # ----------------------------------------------------

        print(
            "[SearchService] "
            "Primary query returned no results. "
            "Using fallback queries..."
        )

        fallback_queries = (
            self._build_fallback_queries(
                query
            )
        )

        collected_results: list[
            SearchResult
        ] = []

        seen_urls: set[str] = set()

        for fallback_query in fallback_queries:

            if (
                len(collected_results)
                >= self.max_results
            ):
                break

            print(
                "[SearchService] "
                f"Fallback: "
                f"{fallback_query}"
            )

            remaining = (
                self.max_results
                - len(collected_results)
            )

            results = self._run_search(
                query=fallback_query,
                max_results=min(
                    5,
                    remaining,
                ),
            )

            for result in results:

                normalized_url = (
                    result.url
                    .strip()
                    .lower()
                )

                if (
                    normalized_url
                    in seen_urls
                ):
                    continue

                seen_urls.add(
                    normalized_url
                )

                collected_results.append(
                    result
                )

                if (
                    len(collected_results)
                    >= self.max_results
                ):
                    break

            # Small delay to reduce the risk
            # of DDGS rate limiting.
            time.sleep(0.6)

        return collected_results[
            : self.max_results
        ]

    # ========================================================
    # DDGS SEARCH
    # ========================================================

    def _run_search(
        self,
        query: str,
        max_results: int,
    ) -> list[SearchResult]:

        results: list[
            SearchResult
        ] = []

        try:

            with DDGS() as ddgs:

                raw_results = ddgs.text(
                    query,
                    max_results=max_results,
                )

                for item in raw_results:

                    title = (
                        item.get("title")
                        or ""
                    ).strip()

                    url = (
                        item.get("href")
                        or item.get("url")
                        or ""
                    ).strip()

                    snippet = (
                        item.get("body")
                        or item.get("snippet")
                        or ""
                    ).strip()

                    published_at = (
                        item.get("date")
                        or None
                    )

                    if not title or not url:
                        continue

                    results.append(
                        SearchResult(
                            title=title,
                            url=url,
                            snippet=snippet,
                            published_at=(
                                published_at
                            ),
                        )
                    )

        except Exception as exc:

            print(
                "[SearchService] "
                f"Search failed for "
                f"'{query}': {exc}"
            )

        return results

    # ========================================================
    # FALLBACK QUERY GENERATION
    # ========================================================

    @staticmethod
    def _build_fallback_queries(
        query: str,
    ) -> list[str]:
        """
        Convert a complex query such as:

        "Mistral AI" ("product launch" OR "funding" ...)

        into simpler queries such as:

        Mistral AI product launch
        Mistral AI funding
        Mistral AI partnership
        """

        quoted_terms = re.findall(
            r'"([^"]+)"',
            query,
        )

        if not quoted_terms:

            return [
                query
            ]

        company = quoted_terms[0]

        keywords = quoted_terms[1:]

        # Priority signals that are especially
        # useful for sponsorship monitoring.
        priority_order = (
            "funding",
            "product launch",
            "new product",
            "partnership",
            "expansion",
            "new market",
            "acquisition",
            "enterprise",
        )

        ordered_keywords: list[
            str
        ] = []

        for priority in priority_order:

            for keyword in keywords:

                if (
                    keyword.lower()
                    == priority.lower()
                    and keyword
                    not in ordered_keywords
                ):
                    ordered_keywords.append(
                        keyword
                    )

        # Keep any remaining keywords too.
        for keyword in keywords:

            if (
                keyword
                not in ordered_keywords
            ):
                ordered_keywords.append(
                    keyword
                )

        fallback_queries = [
            f"{company} {keyword}"
            for keyword
            in ordered_keywords
        ]

        # Last fallback:
        # search only the company name.
        fallback_queries.append(
            company
        )

        return fallback_queries