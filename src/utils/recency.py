from datetime import (
    datetime,
    timezone,
)


def calculate_recency_score(
    published_at: str | None,
) -> int:
    """
    Deterministic article recency score.

    Unknown publication dates are intentionally
    treated conservatively.
    """

    if not published_at:
        return 5

    try:

        value = (
            published_at
            .strip()
            .replace(
                "Z",
                "+00:00",
            )
        )

        # Simple YYYY-MM-DD is supported
        # by datetime.fromisoformat().
        published = (
            datetime.fromisoformat(
                value
            )
        )

        if published.tzinfo is None:

            published = (
                published.replace(
                    tzinfo=timezone.utc
                )
            )

        now = datetime.now(
            timezone.utc
        )

        age_days = (
            now - published
        ).days

        if age_days < 0:
            # Future / malformed dates:
            # do not award more than normal recency.
            return 15

        if age_days <= 30:
            return 15

        if age_days <= 90:
            return 12

        if age_days <= 180:
            return 8

        if age_days <= 365:
            return 5

        return 2

    except Exception:

        return 5