import hashlib
import re


def normalize_text(text: str) -> str:
    """
    Normalize text before hashing.
    """

    text = text.lower().strip()

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text


def generate_content_hash(
    company: str,
    title: str,
    content: str,
) -> str:
    """
    Generate a deterministic SHA-256 hash
    for an article.
    """

    normalized_company = normalize_text(company)
    normalized_title = normalize_text(title)
    normalized_content = normalize_text(content)

    combined = (
        f"{normalized_company}|"
        f"{normalized_title}|"
        f"{normalized_content}"
    )

    return hashlib.sha256(
        combined.encode("utf-8")
    ).hexdigest()