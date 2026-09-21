import requests
from bs4 import BeautifulSoup

from src.utils.text_cleaning import (
    clean_text,
    truncate_text,
)


class ScraperService:
    """
    Lightweight webpage scraper.

    Used to extract readable article text
    from public web pages.
    """

    def __init__(
        self,
        timeout: int = 10,
        max_characters: int = 12000,
    ) -> None:

        self.timeout = timeout
        self.max_characters = max_characters

        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/120 Safari/537.36"
            )
        }

    def scrape(
        self,
        url: str,
    ) -> str | None:
        """
        Download and extract meaningful
        text from a webpage.

        Returns None if extraction fails.
        """

        try:

            response = requests.get(
                url,
                headers=self.headers,
                timeout=self.timeout,
            )

            response.raise_for_status()

            content_type = response.headers.get(
                "Content-Type",
                "",
            )

            if "text/html" not in content_type:
                return None

            soup = BeautifulSoup(
                response.text,
                "html.parser",
            )

            # Remove page elements that usually
            # contain little useful article content.
            for tag in soup(
                [
                    "script",
                    "style",
                    "noscript",
                    "nav",
                    "footer",
                    "header",
                    "form",
                    "svg",
                ]
            ):
                tag.decompose()

            article = soup.find("article")

            if article:
                raw_text = article.get_text(
                    separator=" ",
                )
            else:
                raw_text = soup.get_text(
                    separator=" ",
                )

            text = clean_text(
                raw_text
            )

            text = truncate_text(
                text,
                max_characters=self.max_characters,
            )

            if len(text) < 150:
                return None

            return text

        except requests.RequestException as exc:

            print(
                f"[ScraperService] "
                f"Failed to scrape {url}: {exc}"
            )

            return None

        except Exception as exc:

            print(
                f"[ScraperService] "
                f"Unexpected error for {url}: {exc}"
            )

            return None