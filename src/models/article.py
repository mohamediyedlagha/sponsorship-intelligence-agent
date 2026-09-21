from datetime import datetime

from pydantic import BaseModel, Field


class Article(BaseModel):
    company: str

    title: str

    url: str

    content: str

    source: str | None = None

    published_at: datetime | None = None

    discovered_at: datetime = Field(
        default_factory=datetime.utcnow
    )

    content_hash: str | None = None