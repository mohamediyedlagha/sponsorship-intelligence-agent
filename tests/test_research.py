from src.agents.research_agent import (
    ResearchAgent,
)
from src.memory.database import Database
from src.services.search_service import (
    SearchResult,
)


class FakeSearchService:

    def search(
        self,
        query: str,
    ) -> list[SearchResult]:

        return [
            SearchResult(
                title=(
                    "Mistral AI launches "
                    "new enterprise product"
                ),
                url=(
                    "https://example.com/"
                    "mistral-product"
                ),
                snippet=(
                    "Mistral AI announced "
                    "a new enterprise AI product."
                ),
            )
        ]


class FakeScraperService:

    def scrape(
        self,
        url: str,
    ) -> str:

        return (
            "Mistral AI announced "
            "a new enterprise AI product "
            "for business customers."
        )


def test_research_agent_memory(
    tmp_path,
):

    database_path = (
        tmp_path
        / "research_test.db"
    )

    db = Database(
        database_path=database_path
    )

    agent = ResearchAgent(
        database=db,
        search_service=FakeSearchService(),
        scraper_service=FakeScraperService(),
    )

    # First run
    first_run = agent.research_company(
        company="Mistral AI",
        keywords=[
            "product launch",
            "partnership",
        ],
    )

    assert (
        first_run["articles_found"]
        == 1
    )

    assert (
        first_run["new_articles"]
        == 1
    )

    # Second run
    second_run = agent.research_company(
        company="Mistral AI",
        keywords=[
            "product launch",
            "partnership",
        ],
    )

    assert (
        second_run["articles_found"]
        == 1
    )

    assert (
        second_run["new_articles"]
        == 0
    )