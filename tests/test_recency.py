from datetime import (
    datetime,
    timedelta,
    timezone,
)

from src.utils.recency import (
    calculate_recency_score,
)


def test_unknown_date():

    assert (
        calculate_recency_score(
            None
        )
        == 5
    )


def test_recent_article():

    date = (
        datetime.now(
            timezone.utc
        )
        - timedelta(
            days=10
        )
    ).isoformat()

    assert (
        calculate_recency_score(
            date
        )
        == 15
    )


def test_medium_age_article():

    date = (
        datetime.now(
            timezone.utc
        )
        - timedelta(
            days=120
        )
    ).isoformat()

    assert (
        calculate_recency_score(
            date
        )
        == 8
    )