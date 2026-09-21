import re


def clean_text(text: str) -> str:
    """
    Clean extracted webpage text.

    Removes:
    - excessive whitespace
    - tabs
    - repeated blank lines
    """

    if not text:
        return ""

    text = text.replace("\t", " ")

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def truncate_text(
    text: str,
    max_characters: int = 12000,
) -> str:
    """
    Limit the amount of article text sent
    to the local LLM.

    This prevents extremely long webpages
    from consuming unnecessary context.
    """

    if len(text) <= max_characters:
        return text

    return text[:max_characters]


def normalize_url(url: str) -> str:
    """
    Remove simple tracking parameters and
    normalize a URL for comparison.
    """

    if not url:
        return ""

    url = url.strip()

    # Remove common tracking fragments.
    url = re.sub(
        r"[?&]utm_[^&]+",
        "",
        url,
    )

    return url.rstrip("?&")