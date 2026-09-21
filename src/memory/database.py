import sqlite3
from datetime import (
    datetime,
    timezone,
)
from pathlib import Path

from src.config import (
    DATABASE_PATH,
)


class Database:

    def __init__(
        self,
        database_path: str | Path = DATABASE_PATH,
    ) -> None:

        self.database_path = Path(
            database_path
        )

        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.initialize()

    # ========================================================
    # CONNECTION
    # ========================================================

    def connect(
        self,
    ) -> sqlite3.Connection:

        connection = sqlite3.connect(
            self.database_path
        )

        connection.execute(
            "PRAGMA foreign_keys = ON"
        )

        return connection

    # ========================================================
    # INITIALIZATION
    # ========================================================

    def initialize(
        self,
    ) -> None:

        with self.connect() as connection:

            cursor = (
                connection.cursor()
            )

            # =================================================
            # ARTICLES
            # =================================================

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company TEXT NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    source TEXT,
                    published_at TEXT,
                    content TEXT NOT NULL,
                    content_hash TEXT NOT NULL UNIQUE,
                    first_seen_at TEXT NOT NULL
                )
                """
            )

            # =================================================
            # SIGNALS
            # =================================================

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    article_id INTEGER NOT NULL,
                    company TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    business_relevance INTEGER NOT NULL,
                    confidence REAL NOT NULL,
                    created_at TEXT NOT NULL,

                    FOREIGN KEY(article_id)
                        REFERENCES articles(id)
                        ON DELETE CASCADE
                )
                """
            )

            # =================================================
            # RECOMMENDATIONS
            # =================================================

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS recommendations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    event_summary TEXT NOT NULL DEFAULT '',
                    recommended_event TEXT NOT NULL DEFAULT 'NONE',
                    event_fit_reason TEXT NOT NULL DEFAULT '',
                    total_score INTEGER NOT NULL,
                    confidence REAL NOT NULL,
                    reason TEXT NOT NULL,
                    next_step TEXT NOT NULL,
                    recommendation_hash TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL
                )
                """
            )

            # =================================================
            # RUNS
            # =================================================

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    articles_found INTEGER DEFAULT 0,
                    new_articles INTEGER DEFAULT 0,
                    recommendations_created INTEGER DEFAULT 0,
                    status TEXT NOT NULL
                )
                """
            )

            # =================================================
            # DATABASE MIGRATIONS
            # =================================================

            self._run_migrations(
                connection
            )

            connection.commit()

    # ========================================================
    # MIGRATIONS
    # ========================================================

    def _run_migrations(
        self,
        connection: sqlite3.Connection,
    ) -> None:
        """
        Safely upgrade an existing SQLite database.

        This allows older demo databases to continue working
        after new recommendation fields are introduced.
        """

        # ----------------------------------------------------
        # event_summary
        # ----------------------------------------------------

        if not self._column_exists(
            connection,
            "recommendations",
            "event_summary",
        ):

            connection.execute(
                """
                ALTER TABLE recommendations
                ADD COLUMN event_summary
                TEXT NOT NULL DEFAULT ''
                """
            )

        # ----------------------------------------------------
        # recommended_event
        # ----------------------------------------------------

        if not self._column_exists(
            connection,
            "recommendations",
            "recommended_event",
        ):

            connection.execute(
                """
                ALTER TABLE recommendations
                ADD COLUMN recommended_event
                TEXT NOT NULL DEFAULT 'NONE'
                """
            )

        # ----------------------------------------------------
        # event_fit_reason
        # ----------------------------------------------------

        if not self._column_exists(
            connection,
            "recommendations",
            "event_fit_reason",
        ):

            connection.execute(
                """
                ALTER TABLE recommendations
                ADD COLUMN event_fit_reason
                TEXT NOT NULL DEFAULT ''
                """
            )

    @staticmethod
    def _column_exists(
        connection: sqlite3.Connection,
        table: str,
        column: str,
    ) -> bool:

        cursor = connection.execute(
            f"PRAGMA table_info({table})"
        )

        columns = [
            row[1]
            for row in cursor.fetchall()
        ]

        return column in columns

    # ========================================================
    # ARTICLES
    # ========================================================

    def article_exists(
        self,
        content_hash: str,
    ) -> bool:

        with self.connect() as connection:

            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT id
                FROM articles
                WHERE content_hash = ?
                """,
                (
                    content_hash,
                ),
            )

            return (
                cursor.fetchone()
                is not None
            )

    def save_article(
        self,
        company: str,
        title: str,
        url: str,
        content: str,
        content_hash: str,
        source: str | None = None,
        published_at: str | None = None,
    ) -> int | None:

        if self.article_exists(
            content_hash
        ):
            return None

        first_seen_at = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        with self.connect() as connection:

            cursor = connection.cursor()

            cursor.execute(
                """
                INSERT INTO articles (
                    company,
                    title,
                    url,
                    source,
                    published_at,
                    content,
                    content_hash,
                    first_seen_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    company,
                    title,
                    url,
                    source,
                    published_at,
                    content,
                    content_hash,
                    first_seen_at,
                ),
            )

            connection.commit()

            return cursor.lastrowid

    def get_article_count(
        self,
    ) -> int:

        with self.connect() as connection:

            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM articles
                """
            )

            return cursor.fetchone()[0]

    def get_article_by_id(
        self,
        article_id: int,
    ) -> dict | None:

        with self.connect() as connection:

            connection.row_factory = (
                sqlite3.Row
            )

            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT *
                FROM articles
                WHERE id = ?
                """,
                (
                    article_id,
                ),
            )

            row = cursor.fetchone()

            if row is None:
                return None

            return dict(row)

    def get_articles_by_company(
        self,
        company: str,
    ) -> list[dict]:

        with self.connect() as connection:

            connection.row_factory = (
                sqlite3.Row
            )

            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT *
                FROM articles
                WHERE company = ?
                ORDER BY first_seen_at DESC
                """,
                (
                    company,
                ),
            )

            return [
                dict(row)
                for row
                in cursor.fetchall()
            ]

    # ========================================================
    # SIGNALS
    # ========================================================

    def save_signal(
        self,
        article_id: int,
        company: str,
        signal_type: str,
        summary: str,
        business_relevance: int,
        confidence: float,
    ) -> int:

        created_at = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        with self.connect() as connection:

            cursor = connection.cursor()

            cursor.execute(
                """
                INSERT INTO signals (
                    article_id,
                    company,
                    signal_type,
                    summary,
                    business_relevance,
                    confidence,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    article_id,
                    company,
                    signal_type,
                    summary,
                    business_relevance,
                    confidence,
                    created_at,
                ),
            )

            connection.commit()

            return cursor.lastrowid

    def get_signals_by_company(
        self,
        company: str,
    ) -> list[dict]:

        with self.connect() as connection:

            connection.row_factory = (
                sqlite3.Row
            )

            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT *
                FROM signals
                WHERE company = ?
                ORDER BY created_at DESC
                """,
                (
                    company,
                ),
            )

            return [
                dict(row)
                for row
                in cursor.fetchall()
            ]

    # ========================================================
    # RECOMMENDATIONS
    # ========================================================

    def recommendation_exists(
        self,
        recommendation_hash: str,
    ) -> bool:

        with self.connect() as connection:

            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT id
                FROM recommendations
                WHERE recommendation_hash = ?
                """,
                (
                    recommendation_hash,
                ),
            )

            return (
                cursor.fetchone()
                is not None
            )

    def save_recommendation(
        self,
        company: str,
        signal_type: str,
        event_summary: str,
        total_score: int,
        confidence: float,
        reason: str,
        next_step: str,
        recommendation_hash: str,
        recommended_event: str = "NONE",
        event_fit_reason: str = "",
    ) -> int | None:
        """
        Save a new sponsorship recommendation.

        recommended_event and event_fit_reason have default
        values to preserve compatibility with older tests
        and existing code.
        """

        if self.recommendation_exists(
            recommendation_hash
        ):
            return None

        created_at = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        with self.connect() as connection:

            cursor = connection.cursor()

            cursor.execute(
                """
                INSERT INTO recommendations (
                    company,
                    signal_type,
                    event_summary,
                    recommended_event,
                    event_fit_reason,
                    total_score,
                    confidence,
                    reason,
                    next_step,
                    recommendation_hash,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    company,
                    signal_type,
                    event_summary,
                    recommended_event,
                    event_fit_reason,
                    total_score,
                    confidence,
                    reason,
                    next_step,
                    recommendation_hash,
                    created_at,
                ),
            )

            connection.commit()

            return cursor.lastrowid

    def get_recommendations_by_company(
        self,
        company: str,
    ) -> list[dict]:

        with self.connect() as connection:

            connection.row_factory = (
                sqlite3.Row
            )

            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT *
                FROM recommendations
                WHERE company = ?
                ORDER BY created_at DESC
                """,
                (
                    company,
                ),
            )

            return [
                dict(row)
                for row
                in cursor.fetchall()
            ]

    # ========================================================
    # RUNS
    # ========================================================

    def start_run(
        self,
    ) -> int:

        started_at = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        with self.connect() as connection:

            cursor = connection.cursor()

            cursor.execute(
                """
                INSERT INTO runs (
                    started_at,
                    status
                )
                VALUES (?, ?)
                """,
                (
                    started_at,
                    "RUNNING",
                ),
            )

            connection.commit()

            return cursor.lastrowid

    def finish_run(
        self,
        run_id: int,
        articles_found: int,
        new_articles: int,
        recommendations_created: int,
    ) -> None:

        finished_at = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        with self.connect() as connection:

            connection.execute(
                """
                UPDATE runs
                SET
                    finished_at = ?,
                    articles_found = ?,
                    new_articles = ?,
                    recommendations_created = ?,
                    status = ?
                WHERE id = ?
                """,
                (
                    finished_at,
                    articles_found,
                    new_articles,
                    recommendations_created,
                    "COMPLETED",
                    run_id,
                ),
            )

            connection.commit()

    def fail_run(
        self,
        run_id: int,
    ) -> None:

        finished_at = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        with self.connect() as connection:

            connection.execute(
                """
                UPDATE runs
                SET
                    finished_at = ?,
                    status = ?
                WHERE id = ?
                """,
                (
                    finished_at,
                    "FAILED",
                    run_id,
                ),
            )

            connection.commit()

    def get_runs(
        self,
    ) -> list[dict]:

        with self.connect() as connection:

            connection.row_factory = (
                sqlite3.Row
            )

            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT *
                FROM runs
                ORDER BY started_at DESC
                """
            )

            return [
                dict(row)
                for row
                in cursor.fetchall()
            ]